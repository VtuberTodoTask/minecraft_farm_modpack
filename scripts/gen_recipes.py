#!/usr/bin/env python3
"""data/eyes.yaml から KubeJS のレシピスクリプトを生成する。

CLAUDE.md 5.3 に対応。エンダーアイ12種を Ars Nouveau の Enchanting Apparatus で
作るレシピを吐く。data/ が唯一の正であり、出力を手で編集してはいけない。

使い方:
    python3 scripts/gen_recipes.py
    python3 scripts/gen_recipes.py --check

data/eyes.yaml の eyes: が空のあいだは何も出力しない。これは異常ではなく、
CLAUDE.md 7章の未決定事項（12種の目に割り当てる料理チェーン）が未決定であり、
End Remastered のアイテムIDも未確認だから。埋まった時点でこのスクリプトが
そのまま使える。

UNTESTED: 出力する JS は CLAUDE.md 5.3 に載っているシグネチャに従って
組み立てているが、ゲームを起動しての確認はしていない（CLAUDE.md 3.3）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "eyes.yaml"
OUTPUT = REPO / "pack" / "kubejs" / "server_scripts" / "end_remastered_eyes.js"

# CLAUDE.md 5.3: 台座アイテムは最大8。
MAX_PEDESTALS = 8

HEADER = """// 生成物。手で編集しないこと。
// data/eyes.yaml を直して scripts/gen_recipes.py を実行する（CLAUDE.md 3.4）。
//
// End Remastered のエンダーアイ12種を Ars Nouveau の Enchanting Apparatus で作る。
// 憲法 2.5: 目の材料は農業由来の料理。12種すべて別系統の食材チェーンを要求する。
//
// UNTESTED: ゲームを起動しての確認はしていない。
"""


class DataError(Exception):
    """data/ 側の記述が不正。"""


def load() -> dict:
    with SOURCE.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise DataError(f"{SOURCE.name} のトップレベルがマッピングではない")
    return doc


def _item(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{where} のアイテムIDが空か文字列でない: {value!r}")
    if ":" not in value:
        # 名前空間なしのIDは minecraft: と解釈されて事故になりやすい。
        raise DataError(f"{where} のアイテムID {value!r} に名前空間がない（例: 'modid:item'）")
    return value


def validate(doc: dict) -> list[dict]:
    eyes = doc.get("eyes") or []
    if not isinstance(eyes, list):
        raise DataError("eyes: がリストではない")

    default_cost = (doc.get("ritual") or {}).get("default_source_cost")

    seen_keys: set[str] = set()
    seen_items: set[str] = set()
    seen_chains: set[str] = set()
    out: list[dict] = []

    for i, e in enumerate(eyes):
        where = f"eyes[{i}]"
        if not isinstance(e, dict):
            raise DataError(f"{where} がマッピングではない")

        key = e.get("key")
        if not isinstance(key, str) or not key.strip():
            raise DataError(f"{where} に key がない")
        if key in seen_keys:
            raise DataError(f"key が重複している: {key!r}")
        seen_keys.add(key)

        item = _item(e.get("item"), f"{where}.item")
        if item in seen_items:
            raise DataError(f"同じ目を2回作ろうとしている: {item!r}")
        seen_items.add(item)

        chain = e.get("chain")
        if not isinstance(chain, str) or not chain.strip():
            raise DataError(f"{where} に chain がない")
        if chain in seen_chains:
            # 憲法 2.5。ここを緩めると「同じ畑で12個作れる」状態になる。
            raise DataError(
                f"食材チェーン {chain!r} が複数の目で使い回されている。"
                "12種すべて別系統にすること（憲法 2.5）"
            )
        seen_chains.add(chain)

        pedestals = e.get("pedestals") or []
        if not isinstance(pedestals, list) or not pedestals:
            raise DataError(f"{where} に pedestals がない")
        if len(pedestals) > MAX_PEDESTALS:
            raise DataError(
                f"{where} の pedestals が {len(pedestals)} 個ある。"
                f"Enchanting Apparatus の台座は最大 {MAX_PEDESTALS}（CLAUDE.md 5.3）"
            )
        pedestals = [_item(p, f"{where}.pedestals[{j}]") for j, p in enumerate(pedestals)]

        reagent = _item(e.get("reagent"), f"{where}.reagent")

        cost = e.get("source_cost", default_cost)
        if not isinstance(cost, int) or isinstance(cost, bool) or cost < 0:
            raise DataError(
                f"{where} の source_cost が整数でない: {cost!r}。"
                "eyes.yaml の ritual.default_source_cost か個別の source_cost を埋めること"
            )

        out.append(
            {"key": key, "item": item, "chain": chain,
             "pedestals": pedestals, "reagent": reagent, "source_cost": cost}
        )

    if out and len(out) != 12:
        # 12種そろわないとポータルが開かない。中途半端な状態で気づかず進むのを防ぐ。
        raise DataError(f"目が {len(out)} 種しかない。End Remastered は12種（憲法 2.5）")

    return out


def render(eyes: list[dict]) -> str:
    lines = [HEADER, "ServerEvents.recipes(event => {"]
    for e in eyes:
        peds = ",\n".join(f"      {json.dumps(p)}" for p in e["pedestals"])
        lines += [
            f"  // {e['key']} — 食材チェーン: {e['chain']}",
            "  event.recipes.ars_nouveau.enchanting_apparatus(",
            "    [",
            peds,
            "    ],",
            f"    {json.dumps(e['reagent'])},",
            f"    {json.dumps(e['item'])},",
            f"    {e['source_cost']}",
            "  )",
            "",
        ]
    lines.append("})")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="書き込まずに差分の有無だけを検証する")
    args = ap.parse_args()

    try:
        eyes = validate(load())
    except DataError as e:
        print(f"data/eyes.yaml が不正: {e}", file=sys.stderr)
        return 2

    if not eyes:
        msg = ("data/eyes.yaml の eyes: が空のため、レシピは生成しない。\n"
               "  未決定事項（CLAUDE.md 7章）:\n"
               "    - 12種の目に割り当てる料理チェーン\n"
               "    - End Remastered の目のアイテムID（TODO(id)）")
        if args.check:
            if OUTPUT.exists():
                print(f"eyes: が空なのに {OUTPUT.relative_to(REPO)} が残っている", file=sys.stderr)
                return 1
            print("OK: eyes: が空。生成物も無い。")
            return 0
        if OUTPUT.exists():
            OUTPUT.unlink()
        print(msg)
        return 0

    want = render(eyes)
    if args.check:
        have = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
        if have != want:
            print(f"{OUTPUT.relative_to(REPO)} が data/eyes.yaml と一致していない。"
                  "scripts/gen_recipes.py を実行すること。", file=sys.stderr)
            return 1
        print(f"OK: 目 {len(eyes)} 種が data/eyes.yaml と一致している。")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(want, encoding="utf-8")
    print(f"生成: 目 {len(eyes)} 種 -> {OUTPUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
