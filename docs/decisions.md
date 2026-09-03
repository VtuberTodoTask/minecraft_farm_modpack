# 決定ログ

なぜそうしたかを残す。CLAUDE.md 8章に基づき、設計判断を伴う変更はここに追記する。

新しい項目は下に追加する。日付は YYYY-MM-DD。

---

## 2026-09-03 — 鉱石除去は placed_feature ではなく configured_feature を潰す

**決定**: `data/ore_removal.yaml` の管理対象を configured_feature 名に統一し、
`minecraft:no_op` での上書きも configured_feature 側だけに行う。

**理由**:

placed_feature は configured_feature を参照する薄いラッパーで、1つの
configured_feature を複数の placed_feature が共有していることが多い。
configured 側を `no_op` にすれば、それを参照するすべての placed が何も
生成しなくなる。したがって configured 側を潰すほうが、

- 漏れが出にくい（placed を1つ書き忘れると鉱石が残る）
- ファイル数が少ない（19ファイルで全鉱石を止められる）

バニラ 1.20.1 での実際の対応関係は `data/ore_removal.yaml` の
`placed_by` に証跡として残してある。例:

| configured（潰す） | それを使う placed |
|---|---|
| `ore_redstone` | `ore_redstone`, `ore_redstone_lower` |
| `ore_iron` | `ore_iron_middle`, `ore_iron_upper` |
| `ore_coal` | `ore_coal_upper` |
| `ore_coal_buried` | `ore_coal_lower` |
| `ore_gold_buried` | `ore_gold`, `ore_gold_lower` |
| `ore_gold` | `ore_gold_extra` |
| `ore_quartz` | `ore_quartz_nether`, `ore_quartz_deltas` |

---

## 2026-09-03 — CLAUDE.md 5.1 の feature 名リストに誤りがあったため訂正した

**決定**: CLAUDE.md 5.1 の注意書きにあった feature 名の例示を、バニラ 1.20.1 の
実際の configured_feature 名に差し替えた。

**理由**:

元の記述は次のように configured_feature 名と placed_feature 名が混ざっていた。

- `ore_copper` … placed のみ。configured は `ore_copper_small`
- `ore_gold_extra` … placed のみ。configured は `ore_gold`
- `ore_redstone_lower` … placed のみ。configured は `ore_redstone` に含まれる
- `ore_coal_upper` / `ore_coal_lower` … placed のみ。configured は `ore_coal` / `ore_coal_buried`
- `ore_quartz_nether` … placed のみ。configured は `ore_quartz`
- `ore_diamond` 系4種 … configured は3種（`ore_diamond_small` / `_large` / `_buried`）。
  4種なのは placed 側（`ore_diamond` / `_large` / `_buried`）でもなく、
  バージョンによる記憶違いと思われる

これらを `configured_feature/` に置いても、その名前の configured_feature は
存在しないため**何も無効化されない**。銅・金・レッドストーン・石炭・クォーツが
そのまま湧き、憲法 2.2（鉱石は自然生成しない）が崩れる。経済設計の前提が
丸ごと壊れるため、放置できないと判断した。

**根拠**: misode/mcmeta の `1.20.1-data` / `1.20.1-summary` ブランチ
（バニラ 1.20.1 のデータ本体とレジストリ一覧）を取得し、
`worldgen/configured_feature` の全エントリと各 placed_feature の `feature`
フィールドを機械的に突き合わせた。手入力・記憶からの補完はしていない。
`minecraft:no_op` が 1.20.1 の `worldgen/feature` レジストリに実在することも
同じ手順で確認した。

**補足**: これは設計判断の変更ではなく事実の訂正であるため、憲法（CLAUDE.md 2章）の
「変更する場合は必ず人間に確認」には当たらないと判断して先に直した。
判断が違っていればこのコミットを戻せば元に戻る。

---

## 2026-09-03 — 地形ブロック系の `ore_*` は残す

**決定**: `ore_andesite` / `ore_diorite` / `ore_granite` / `ore_tuff` /
`ore_gravel` / `ore_gravel_nether` / `ore_dirt` / `ore_clay` /
`ore_blackstone` / `ore_magma` / `ore_soul_sand` / `ore_infested` は除去しない。

**理由**: 名前は `ore_` で始まるが中身は鉱物ではなく地形ブロック。
特に安山岩は Create の主要素材、砂利は燧石（火打石）の入手経路であり、
消すと農業と無関係なところで詰む。

`data/ore_removal.yaml` にはこれらを `keep:` として明示的に列挙してある。
書かずに省くと、後から監査したときに「漏れなのか判断なのか」が分からなくなるため。

---

## 2026-09-03 — 石炭とネザー鉱石も除去対象に含めた

**決定**: 石炭・ネザー金鉱石・ネザークォーツ・古代の残骸も worldgen から除去する。

**理由**: 憲法 2.2 は「バニラ鉱石は全バリアントを worldgen から除去する」であり、
例外として挙がっているのは Mystical Agriculture の Prosperity / Inferium だけ。
石炭は木炭で代替できるので序盤の詰みは起きない。クォーツは Create の需要が
大きいぶん、ショップに寄せたほうが「鉱物は使うために買うもの」（憲法 2.3）が効く。

**確認したい点**: ネザー金鉱石を消すこととピグリン交易を残すかどうかは別問題。
CLAUDE.md 7章の「鉱石以外の鉄入手経路をどこまで塞ぐか」に含まれる論点なので、
そちらが決まったら整合を取り直す必要がある。

---

## 未記入（人間の判断待ち）

CLAUDE.md 7章の未決定事項が片付いたら、決定内容と理由をここに追記する。
特に以下は決まり次第、必ず理由まで残すこと。

- 料理納品の時給想定（価格表全体の基準になる）
- FTB Quests のリピートクエスト不具合の再現結果と、販売実装の方式
- 12種の目に割り当てる料理チェーン
