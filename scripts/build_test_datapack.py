#!/usr/bin/env python3
"""pack/kubejs/data/ の中身を、バニラで読める datapack に詰め直す。

mod を1つも入れずに鉱石除去だけを検証するためのもの。
KubeJS 経由（`kubejs/data/`）で動かす場合はこのスクリプトは不要。

使い方:
    python3 scripts/build_test_datapack.py <出力先ディレクトリ>

例:
    python3 scripts/build_test_datapack.py ~/mc-test/world/datapacks/farm_no_ores

pack_format は 15。Minecraft 1.20.1 のバニラ自身の pack.mcmeta と
version.json（data_pack_version）で確認済みで、推測ではない。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "pack" / "kubejs" / "data"

# 1.20.1 の datapack フォーマット。確認済み（CLAUDE.md 3.1）。
PACK_FORMAT = 15


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dest", type=Path, help="datapack を作る場所")
    ap.add_argument("--force", action="store_true", help="既存の出力先を消してから作り直す")
    args = ap.parse_args()

    if not SOURCE.is_dir():
        print(f"{SOURCE} が無い。先に gen_ore_removal.py を実行すること。", file=sys.stderr)
        return 2

    dest: Path = args.dest.expanduser().resolve()
    if dest.exists():
        if not args.force:
            print(f"{dest} は既にある。作り直すなら --force を付けること。", file=sys.stderr)
            return 2
        shutil.rmtree(dest)

    (dest / "data").mkdir(parents=True)

    copied = 0
    for src in sorted(SOURCE.rglob("*.json")):
        rel = src.relative_to(SOURCE)
        # 生成の記録用ファイルは datapack に含めない。
        if rel.parts and rel.parts[0] == ".generated":
            continue
        out = dest / "data" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        copied += 1

    if copied == 0:
        print(f"{SOURCE} に JSON が無い。gen_ore_removal.py を実行したか確認すること。", file=sys.stderr)
        shutil.rmtree(dest)
        return 2

    mcmeta = {
        "pack": {
            "pack_format": PACK_FORMAT,
            "description": "minecraft_farm_modpack / ore removal (test)",
        }
    }
    (dest / "pack.mcmeta").write_text(
        json.dumps(mcmeta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"datapack を作った: {dest}")
    print(f"  JSON {copied} 件 + pack.mcmeta (pack_format={PACK_FORMAT})")
    print()
    print("次にやること:")
    print("  1. この場所がテスト用ワールドの world/datapacks/<名前>/ になっていることを確認する")
    print("  2. サーバを起動し、コンソールで /datapack list を実行して有効になっているか見る")
    return 0


if __name__ == "__main__":
    sys.exit(main())
