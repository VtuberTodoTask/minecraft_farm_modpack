#!/usr/bin/env python3
"""生成済みワールドの region ファイルを走査し、鉱石が残っていないか数える。

目視だと「たまたま見なかっただけ」と「本当に無い」の区別がつかないので、
機械的に数える。

使い方:
    python3 scripts/scan_world_ores.py <ワールドのregionディレクトリ>

例:
    python3 scripts/scan_world_ores.py ~/mc-test/world/region
    python3 scripts/scan_world_ores.py ~/mc-test/world/DIM-1/region   # ネザー

数えているもの:
    region ファイル内のチャンクを展開し、ブロック名の文字列が何回現れるかを
    数えている。ブロックの個数ではなく、そのブロックを含むセクション（16^3の
    区画）のおおよその数。ここで見たいのは有無であって量ではないので、これで足りる。

【重要】このスクリプト自体が壊れていると「0件＝鉱石が消えている」に見えてしまう。
それを防ぐため、必ず存在するはずのブロック（石・岩盤など）を対照として一緒に
数えている。対照が0件なら走査が失敗していると判断して、結果を信用せずエラーで止まる。

UNTESTED: 合成したregionファイルでパーサの動作は確認したが、実際に
Minecraft が出力したワールドでは動かしていない。
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
import gzip
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ORE_YAML = REPO / "data" / "ore_removal.yaml"

SECTOR = 4096

# 走査が成立していることを示す対照。地上ワールドにも地下にも必ずある。
# 1つも見つからなければパーサか対象ディレクトリがおかしい。
CONTROL_BLOCKS = ["minecraft:stone", "minecraft:bedrock", "minecraft:deepslate"]


def chunk_blobs(path: Path) -> tuple[list[bytes], int, int]:
    """region ファイルから各チャンクの展開済みバイト列を取り出す。

    戻り値: (展開できたチャンク, 読み飛ばしたチャンク数, 空きスロット数)
    """
    raw = path.read_bytes()
    if len(raw) < SECTOR * 2:
        return [], 0, 0

    blobs: list[bytes] = []
    skipped = 0
    empty = 0

    for i in range(1024):
        off = i * 4
        entry = raw[off:off + 4]
        if len(entry) < 4:
            break
        sector_offset = int.from_bytes(entry[0:3], "big")
        sector_count = entry[3]
        if sector_offset == 0 or sector_count == 0:
            empty += 1
            continue

        start = sector_offset * SECTOR
        if start + 5 > len(raw):
            skipped += 1
            continue

        length = struct.unpack(">I", raw[start:start + 4])[0]
        if length < 1:
            skipped += 1
            continue
        compression = raw[start + 4]
        payload = raw[start + 5:start + 4 + length]

        # 最上位ビットが立っていると、チャンク本体は別ファイル（.mcc）にある。
        # 黙って無視すると取りこぼすので、読み飛ばした数として報告する。
        if compression & 0x80:
            skipped += 1
            continue

        try:
            if compression == 1:
                blobs.append(gzip.decompress(payload))
            elif compression == 2:
                blobs.append(zlib.decompress(payload))
            elif compression == 3:
                blobs.append(payload)
            else:
                skipped += 1
        except (zlib.error, OSError, EOFError):
            skipped += 1

    return blobs, skipped, empty


def load_expected_absent() -> list[str]:
    with ORE_YAML.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    blocks: list[str] = []
    for entry in (doc.get("configured_features") or {}).get("remove") or []:
        for b in entry.get("blocks") or []:
            if b not in blocks:
                blocks.append(b)
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("region_dir", type=Path, help="ワールドの region ディレクトリ")
    args = ap.parse_args()

    region_dir: Path = args.region_dir.expanduser().resolve()
    if not region_dir.is_dir():
        print(f"ディレクトリが無い: {region_dir}", file=sys.stderr)
        return 2

    files = sorted(region_dir.glob("*.mca"))
    if not files:
        print(f"{region_dir} に .mca が無い。ワールドが生成されているか確認すること。", file=sys.stderr)
        return 2

    absent = load_expected_absent()
    targets = absent + CONTROL_BLOCKS
    counts = {b: 0 for b in targets}
    needles = {b: b.encode() for b in targets}

    chunks = skipped_total = 0
    for path in files:
        blobs, skipped, _ = chunk_blobs(path)
        skipped_total += skipped
        chunks += len(blobs)
        for blob in blobs:
            for b, needle in needles.items():
                c = blob.count(needle)
                if c:
                    counts[b] += c

    print(f"走査: region {len(files)} ファイル / チャンク {chunks} 個", end="")
    if skipped_total:
        print(f" / 読み飛ばし {skipped_total} 個", end="")
    print()
    print()

    control_total = sum(counts[b] for b in CONTROL_BLOCKS)
    print("対照（必ず見つかるはずのブロック）:")
    for b in CONTROL_BLOCKS:
        print(f"  {counts[b]:>8}  {b}")
    print()

    if control_total == 0:
        print("走査が失敗している。対照ブロックが1つも見つからなかった。", file=sys.stderr)
        print("結果は信用できない。region ディレクトリの指定か、", file=sys.stderr)
        print("このスクリプトのパーサを疑うこと。", file=sys.stderr)
        return 2

    found = {b: c for b, c in counts.items() if b in absent and c > 0}
    print("除去対象の鉱石:")
    for b in absent:
        mark = "  NG" if counts[b] else "  ok"
        print(f"  {counts[b]:>8}  {b}{mark}")
    print()

    if found:
        print(f"残っている鉱石が {len(found)} 種類ある:")
        for b, c in sorted(found.items(), key=lambda kv: -kv[1]):
            print(f"  {b}: {c}")
        print()
        print("考えられる原因:")
        print("  - 既存のワールドで試している（鉱石除去は新規ワールドにしか効かない）")
        print("  - datapack が有効になっていない（/datapack list で確認）")
        print("  - mod が追加した鉱石（バニラの worldgen 除去では止まらない）")
        return 1

    print("除去対象の鉱石は1つも見つからなかった。")
    print("（対照ブロックは見つかっているので、走査自体は成立している）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
