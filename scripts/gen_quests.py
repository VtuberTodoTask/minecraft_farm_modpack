#!/usr/bin/env python3
"""data/prices.yaml から FTB Quests の SNBT を生成する。

CLAUDE.md 5.4 に対応。商品数が100を超えるため手作業では作らない。

使い方:
    python3 scripts/gen_quests.py
    python3 scripts/gen_quests.py --lint    # 検査だけ行い、何も書かない

現状:
    検査（lint）までは動く。SNBT の出力は未実装。理由は下の
    「なぜ SNBT 出力が未実装か」を参照。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "prices.yaml"
CHAPTERS = REPO / "pack" / "config" / "ftbquests" / "quests" / "chapters"

# 憲法 2.3 の機械的な担保。
# 買取（sell）に混ざってはいけないカテゴリ。ここに引っかかるものを1つでも
# 買取に入れると、自動生産と組み合わさって無限金策が成立する。
FORBIDDEN_IN_SELL = {"ore", "ingot", "mob_drop", "nugget", "gem", "dust", "raw_ore"}

# 買取に入れてよいと判断するためのIDの手がかり。
# カテゴリの書き間違いを拾うための二重チェックで、これ単体を根拠にはしない。
SUSPICIOUS_ID_PARTS = (
    "_ore", "ore_", "_ingot", "ingot_", "_nugget", "raw_",
    "gunpowder", "ender_pearl", "blaze_rod", "bone", "string", "leather",
)

# SUSPICIOUS_ID_PARTS の誤検知を個別に許可する。
# 例: 骨粉入りの料理や "bone" を含む名前の作物など。
# 追加するときは必ず理由をコメントで残すこと。憲法 2.3 の抜け穴になりうる。
ALLOWED_SELL_IDS: dict[str, str] = {
    # "modid:some_dish": "料理。'bone' を名前に含むだけでモブドロップではない",
}


class DataError(Exception):
    """data/ 側の記述が不正。"""


def load() -> dict:
    with SOURCE.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise DataError(f"{SOURCE.name} のトップレベルがマッピングではない")
    return doc


def _entries(doc: dict, key: str) -> list[dict]:
    v = doc.get(key) or []
    if not isinstance(v, list):
        raise DataError(f"{key}: がリストではない")
    return v


def validate(doc: dict) -> tuple[list[dict], list[dict]]:
    cats = doc.get("categories") or {}
    sellable = set(cats.get("sellable") or [])
    purchasable = set(cats.get("purchasable") or [])
    if not sellable or not purchasable:
        raise DataError("categories.sellable / categories.purchasable が空")

    overlap = sellable & purchasable
    if overlap:
        # 同じカテゴリが売買両方にあると、買って売るだけの裁定取引が生まれる。
        raise DataError(f"sellable と purchasable に同じカテゴリがある: {sorted(overlap)}")

    banned = sellable & FORBIDDEN_IN_SELL
    if banned:
        raise DataError(
            f"買取可能カテゴリに {sorted(banned)} が含まれている。"
            "鉱石・インゴット・モブドロップは買取対象にできない（憲法 2.3）"
        )

    sell = _check_side(_entries(doc, "sell"), "sell", sellable)
    buy = _check_side(_entries(doc, "buy"), "buy", purchasable)

    # 憲法 2.3 の本体。カテゴリ名だけでなく個別エントリも見る。
    for e in sell:
        if e["category"] in FORBIDDEN_IN_SELL:
            raise DataError(
                f"買取に {e['id']!r}（category: {e['category']}）が入っている。"
                "鉱石・インゴット・モブドロップは買取対象にできない（憲法 2.3）"
            )
        hits = [p for p in SUSPICIOUS_ID_PARTS if p in e["id"]]
        if hits and e["id"] not in ALLOWED_SELL_IDS:
            raise DataError(
                f"買取の {e['id']!r} は鉱物かモブドロップに見える（一致: {hits}）。"
                "農産物と料理だけを買取対象にする（憲法 2.3）。"
                "誤検知なら scripts/gen_quests.py の ALLOWED_SELL_IDS に理由つきで追加すること"
            )

    both = {e["id"] for e in sell} & {e["id"] for e in buy}
    if both:
        raise DataError(f"売りと買いの両方にあるアイテムがある（無限金策になる）: {sorted(both)}")

    return sell, buy


def _check_side(entries: list, side: str, allowed: set[str]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        where = f"{side}[{i}]"
        if not isinstance(e, dict):
            raise DataError(f"{where} がマッピングではない")

        item_id = e.get("id")
        if not isinstance(item_id, str) or ":" not in item_id:
            raise DataError(f"{where} の id が不正（名前空間つきのIDが必要）: {item_id!r}")
        if item_id in seen:
            raise DataError(f"{side} に同じアイテムが2回ある: {item_id!r}")
        seen.add(item_id)

        cat = e.get("category")
        if cat not in allowed:
            raise DataError(f"{where} の category が不正: {cat!r}（許可: {sorted(allowed)}）")

        for field in ("count", "price"):
            v = e.get(field)
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise DataError(f"{where} の {field} が正の整数でない: {v!r}")

        out.append({"id": item_id, "category": cat, "count": e["count"], "price": e["price"]})
    return out


def check_baseline(doc: dict) -> list[str]:
    """価格を出力してよい状態かを見る。空リストなら出力可。"""
    blockers = []
    base = doc.get("baseline") or {}
    if base.get("target_income_per_hour") is None:
        blockers.append(
            "baseline.target_income_per_hour が未設定（CLAUDE.md 7章「料理納品の時給想定」）"
        )
    if base.get("currency_item") is None:
        blockers.append("baseline.currency_item が未設定（TODO(id): Numismatics のコイン）")
    return blockers


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lint", action="store_true", help="検査だけ行い、何も書かない")
    args = ap.parse_args()

    try:
        doc = load()
        sell, buy = validate(doc)
    except DataError as e:
        print(f"data/prices.yaml が不正: {e}", file=sys.stderr)
        return 2

    print(f"検査OK: 買取 {len(sell)} 件 / 販売 {len(buy)} 件")

    blockers = check_baseline(doc)
    if args.lint:
        for b in blockers:
            print(f"  未設定: {b}")
        return 0

    if blockers or not (sell or buy):
        print("\nSNBT は生成しない。先に決める必要があるものが残っている:")
        for b in blockers:
            print(f"  - {b}")
        if not (sell or buy):
            print("  - data/prices.yaml の sell / buy が空")
        return 0

    # ------------------------------------------------------------------
    # なぜ SNBT 出力が未実装か
    #
    # 1. 出力すべき中身がまだ無い。価格は時給想定から決まるが、それが
    #    CLAUDE.md 7章の未決定事項として残っている。
    #
    # 2. 販売方式そのものが未確定。CLAUDE.md 5.4 と 7章のとおり、FTB Quests の
    #    リピートクエストには報酬が複製される不具合が知られており、人間による
    #    再現テストの結果しだいで「リピートクエストで売る」以外の方式に
    #    変わりうる。方式が変われば SNBT の構造ごと変わるため、先に書くと捨てる。
    #
    # 3. SNBT のスキーマを実物で確認できていない。FTB Quests の jar も
    #    既存の quests/ も無く、CLAUDE.md 3.1 により記憶で書くことは禁止。
    #
    # 実装するときの手順:
    #   - 人間が 1 と 2 を決める
    #   - 実際に FTB Quests でクエストを1つ手作りし、生成された SNBT を読む
    #   - その形を写して、ここに書き出し処理を足す
    #   - クエスト名は「鉄インゴット ×8 — 80」の形式にする（CLAUDE.md 5.4）
    # ------------------------------------------------------------------
    print(f"\nTODO: SNBT の生成は未実装。出力先は {CHAPTERS.relative_to(REPO)}/ の予定。")
    print("実装の前提と手順は scripts/gen_quests.py のコメントに書いてある。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
