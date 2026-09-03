#!/usr/bin/env python3
"""data/ore_removal.yaml から worldgen 無効化データパックを生成する。

CLAUDE.md 5.1 / 5.2 に対応。data/ が唯一の正であり、このスクリプトの出力を
手で編集してはいけない（CLAUDE.md 3.4 / 4章）。

使い方:
    python3 scripts/gen_ore_removal.py           # 生成
    python3 scripts/gen_ore_removal.py --check   # 生成物が data/ と一致するか検証（CI 用）

UNTESTED: 生成される JSON の形は バニラ 1.20.1 のデータ定義に照らして作って
あるが、実際にゲームを起動して新規ワールドで確認はしていない。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "ore_removal.yaml"
DATAPACK = REPO / "pack" / "kubejs" / "data"
MANIFEST = DATAPACK / ".generated" / "ore_removal.manifest.json"

# リソースパスとして妥当な名前だけを許す。
# data/ に打ち間違いが入ったまま静かに無意味なファイルを吐くのを防ぐ。
NAME_RE = re.compile(r"^[a-z0-9_.-]+$")

# 無効化の実体。この feature 型は 1.20.1 の worldgen/feature レジストリに
# 存在することを確認済み。
NO_OP = {"type": "minecraft:no_op", "config": {}}


class DataError(Exception):
    """data/ 側の記述が不正。"""


def load_source() -> dict:
    with SOURCE.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise DataError(f"{SOURCE.name} のトップレベルがマッピングではない")
    return doc


def _names(entries: list, key: str, where: str) -> list[str]:
    out = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or key not in entry:
            raise DataError(f"{where}[{i}] に {key} がない: {entry!r}")
        name = entry[key]
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise DataError(f"{where}[{i}] の {key} が不正: {name!r}")
        out.append(name)
    return out


def plan(doc: dict) -> dict[str, dict]:
    """出力パス（DATAPACK からの相対）-> JSON 内容 の対応を組み立てる。"""
    cf = doc.get("configured_features") or {}
    remove = _names(cf.get("remove") or [], "feature", "configured_features.remove")
    keep = _names(cf.get("keep") or [], "feature", "configured_features.keep")

    dupes = sorted(set(remove) & set(keep))
    if dupes:
        raise DataError(f"remove と keep の両方に現れる feature がある: {dupes}")
    for group, names in (("remove", remove), ("keep", keep)):
        seen = {n for n in names if names.count(n) > 1}
        if seen:
            raise DataError(f"{group} に重複した feature がある: {sorted(seen)}")

    files: dict[str, dict] = {}
    for name in remove:
        files[f"minecraft/worldgen/configured_feature/{name}.json"] = NO_OP

    sets = (doc.get("structure_sets") or {}).get("empty_structures") or []
    for i, entry in enumerate(sets):
        if not isinstance(entry, dict):
            raise DataError(f"structure_sets.empty_structures[{i}] がマッピングではない")
        name = entry.get("set")
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise DataError(f"structure_sets.empty_structures[{i}] の set が不正: {name!r}")
        placement = entry.get("placement")
        if not isinstance(placement, dict) or "type" not in placement:
            # placement を落とすと構造物探索側が壊れうる（CLAUDE.md 5.2）。
            raise DataError(f"structure set {name!r} に placement がない。バニラの定義をそのまま写すこと")
        files[f"minecraft/worldgen/structure_set/{name}.json"] = {
            "placement": placement,
            "structures": [],
        }

    return files


def render(content: dict) -> str:
    return json.dumps(content, indent=2, ensure_ascii=False) + "\n"


def read_manifest() -> list[str]:
    if not MANIFEST.exists():
        return []
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    except (ValueError, KeyError):
        return []


def write(files: dict[str, dict], check: bool) -> int:
    """check=False なら書き込み、True なら差分があるかだけ報告する。"""
    problems: list[str] = []
    wrote = 0

    for rel, content in sorted(files.items()):
        path = DATAPACK / rel
        want = render(content)
        have = path.read_text(encoding="utf-8") if path.exists() else None
        if have == want:
            continue
        if check:
            problems.append(f"古い/欠けている: pack/kubejs/data/{rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(want, encoding="utf-8")
        wrote += 1

    # data/ から消えたエントリの生成物を残さない。
    # 前回の manifest に載っていて今回作らなかったものだけを消す（手書きの
    # ファイルを巻き込まないため、削除対象は必ず manifest 経由で決める）。
    stale = [rel for rel in read_manifest() if rel not in files]
    for rel in stale:
        path = DATAPACK / rel
        if not path.exists():
            continue
        if check:
            problems.append(f"消し残り: pack/kubejs/data/{rel}")
            continue
        path.unlink()
        for parent in path.parents:
            if parent == DATAPACK:
                break
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()

    manifest_body = json.dumps(
        {
            "generated_by": "scripts/gen_ore_removal.py",
            "source": "data/ore_removal.yaml",
            "note": "手で編集しないこと。data/ を直して再生成する。",
            "files": sorted(files),
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    if MANIFEST.exists() and MANIFEST.read_text(encoding="utf-8") == manifest_body:
        pass
    elif check:
        problems.append("manifest が古い")
    else:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(manifest_body, encoding="utf-8")

    if check:
        if problems:
            print("pack/ が data/ と一致していない:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            print("scripts/gen_ore_removal.py を実行して結果をコミットすること。", file=sys.stderr)
            return 1
        print(f"OK: {len(files)} ファイルが data/ore_removal.yaml と一致している。")
        return 0

    print(f"生成: {len(files)} ファイル（更新 {wrote} / 削除 {len(stale)}）-> pack/kubejs/data/")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="書き込まずに差分の有無だけを検証する")
    args = ap.parse_args()
    try:
        files = plan(load_source())
    except DataError as e:
        print(f"data/ore_removal.yaml が不正: {e}", file=sys.stderr)
        return 2
    return write(files, args.check)


if __name__ == "__main__":
    sys.exit(main())
