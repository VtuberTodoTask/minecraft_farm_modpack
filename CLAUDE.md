Minecraft 1.20.1 Forge 向けmodpackの制作プロジェクト。

このファイルはプロジェクト全体の指示書であり、作業開始時に必ず読むこと。

---

## 1. プロジェクト概要

**コンセプト**: 農業・畜産で生計を立てるmodpack。ルーンファクトリー、牧場物語、スターデューバレーの生活感を土台にしつつ、Minecraftの最終目標であるエンダードラゴン討伐までを一本の線で繋ぐ。

**プラットフォーム**: Minecraft 1.20.1 / Minecraft Forge

**中核となる体験**:

1. 作物を育て、料理に加工し、納品して稼ぐ

2. 稼いだ金で鉱石や資材を買う（鉱石は自然生成しない）

3. 規模が大きくなったら、工業と魔法で作業を省力化する

4. 最終的に自力でエンドポータルを建て、ドラゴンを倒す

---

## 2. デザイン憲法

以下は設計の根幹であり、**変更する場合は必ず人間に確認を取ること**。

矛盾する実装を求められた場合は、実装する前に矛盾を指摘する。

### 2.1 農業が主役、工業と魔法は道具

- 工業（Create）と魔法（Ars Nouveau）は**作業の簡素化**として存在する。それ自体を目的地にしない

- 自動化装置のレシピには農産物・加工食品を要求する。規模を拡大するほど農業の規模も要求される構造を維持する

- 収量を倍加させる系のレシピ（粉砕による鉱石倍化など）は入れないか、大きく抑える

### 2.2 鉱石は自然生成しない

- バニラ鉱石は全バリアントを worldgen から除去する

- ただし Mystical Agriculture の Prosperity / Inferium 鉱石は例外扱い。**Prosperity鉱石の採掘には鉄ツルハシ以上が必要**なので、鉱石を全部消すと進行不能になる

- 最初の鉄は必ずショップ経由で供給する。これが経済の起点

### 2.3 買取対象は農産物と料理だけ

- **鉱石・インゴット・モブドロップを買取対象にしてはいけない**

- これらは自動生産できるため、買取を許すと無限金策が成立し経済が崩壊する

- 鉱物は常に「使うために買うもの」であり続ける

### 2.4 季節が進行のリズムを作る

- Serene Seasons を前提とする

- 冬に農業ができないことが、工業・魔法・畜産に時間を割く理由になる

- 温室（グリーンハウスガラス）は中盤の主要目標。高価格に設定する

- Mystical Agriculture の作物にも季節制限をかける。鉱石農場だけが季節を無視する状態を作らない

### 2.5 最終目標への到達手順

エンダードラゴン討伐までの経路は以下で固定する。

| 要素 | 手段 |

|---|---|

| エンド要塞 | **生成しない**（worldgen で除去） |

| エンドポータルフレーム ×12 | Create の**連続組み立て（Sequenced Assembly）**で製作 |

| エンダーアイ ×12種 | End Remastered の目を Ars Nouveau の **Enchanting Apparatus** で生成 |

| 目の材料 | 農業由来の料理。12種すべて別系統の食材チェーンを要求する |

| 魔力（Source） | Agronomic Sourcelink で畑から供給 |

| 戦闘装備 | Mystical Agriculture のエッセンス装備。農業で強くなる |

工業・魔法・農業のどれか一つでは門が開かない状態を維持する。

---

## 3. 作業上の禁止事項

**このプロジェクトではゲームを起動して検証できない。** 推測がそのままバグになるため、以下を厳守する。

### 3.1 IDを推測しない

- アイテムID、ブロックID、レシピタイプ、タグ、mod ID を記憶や推測で書かない

- 確認手段:

  - mod jar の中身: `unzip -l mods/<name>.jar` および `unzip -p mods/<name>.jar <path>`

  - `/kubejs dump_registry item` の出力（`kubejs/exported/` に生成される）

  - ProbeJS の型定義出力

- 確認できないIDは `// TODO(id): <説明>` を残し、**その旨を報告する**。それらしいIDを埋めない

### 3.2 mod jar を直接書き換えない

- レシピ変更はすべて KubeJS またはデータパックで行う

- jar の中身は読み取り専用として扱う

### 3.3 検証していないことを「動く」と書かない

- コミットメッセージやドキュメントに「動作確認済み」と書けるのは、人間が実際に起動して確認した場合のみ

- 未検証の実装には `// UNTESTED` を付ける

### 3.4 数値バランスを勝手に変えない

- 価格表、ソース消費量、失敗率などは `data/` 配下の設計データが唯一の正

- スクリプトが生成する成果物を直接編集しない。必ず元データを直す

---

## 4. リポジトリ構成

```

.

├── CLAUDE.md              # このファイル

├── README.md

├── docs/

│   ├── design.md          # ゲームデザイン詳細

│   ├── economy.md         # 経済設計と価格の考え方

│   ├── progression.md     # 進行フローとアンロック順

│   └── decisions.md       # 決定ログ（なぜそうしたか）

├── data/                  # 設計データ = ソース・オブ・トゥルース

│   ├── mods.yaml          # 採用mod一覧と役割

│   ├── prices.yaml        # 商品と価格

│   ├── eyes.yaml          # 12種の目と要求料理

│   └── ore_removal.yaml   # 除去対象の worldgen feature 一覧

├── scripts/               # data/ から成果物を生成

│   ├── gen_quests.py      # FTB Quests の SNBT 生成

│   ├── gen_ore_removal.py # 鉱石除去データパック生成

│   └── gen_recipes.py     # KubeJS レシピ生成

├── pack/                  # パック本体（packwiz 管理）

│   ├── pack.toml

│   ├── index.toml

│   ├── mods/              # .pw.toml メタデータのみ。jar は含めない

│   ├── config/

│   ├── defaultconfigs/

│   └── kubejs/

│       ├── startup_scripts/

│       ├── server_scripts/

│       ├── client_scripts/

│       └── data/          # データパック（鉱石除去など）

└── .gitignore

```

### 方針

- **mod の jar は絶対にコミットしない**。packwiz のメタデータ（`.pw.toml`）で管理する

- `data/` を編集 → `scripts/` を実行 → `pack/` に反映、という一方向の流れを守る

- `pack/` 配下の生成物は手で編集しない

---

## 5. 技術ごとの作業指針

### 5.1 鉱石除去（データパック）

`pack/kubejs/data/minecraft/worldgen/configured_feature/<name>.json` に以下を置くことで、その feature を無効化する。

```json

{ "type": "minecraft:no_op", "config": {} }

```

注意点:

- **バリアントを網羅すること**。`ore_iron` / `ore_iron_small` / `ore_copper` / `ore_copper_large` / `ore_gold` / `ore_gold_extra` / `ore_diamond` 系4種 / `ore_redstone` / `ore_redstone_lower` / `ore_lapis` / `ore_lapis_buried` / `ore_coal_upper` / `ore_coal_lower` / `ore_emerald` / `ore_quartz_nether` / `ore_ancient_debris` 系 など

- 対象一覧は `data/ore_removal.yaml` で管理し、スクリプトで生成する

- **既存チャンクには効かない**。テストは必ず新規ワールドで

- mod 追加の鉱石は各 mod の config を優先して確認する

### 5.2 エンド要塞の除去

`pack/kubejs/data/minecraft/worldgen/structure_set/strongholds.json` を上書きし、`structures` を空配列にする。`placement` の `concentric_rings` ブロックは残す。

End Remastered が要塞をカスタムダンジョンに差し替え、End Castle を生成するため、**mod 側の config でも生成を切る必要がある**。

副作用として、エンダーアイを投げても何も見つからない状態になる。クエストブックで明示する。

### 5.3 KubeJS

- レシピ追加は `pack/kubejs/server_scripts/`

- 連続組み立て（Create Sequenced Assembly）、Enchanting Apparatus（KubeJS Ars Nouveau アドオン経由）を使う

- Enchanting Apparatus のシグネチャ:

```js

event.recipes.ars_nouveau.enchanting_apparatus(

  [/* 台座アイテム 最大8 */],

  'reagent_item',   // 中央の触媒

  'output_item',

  sourceCost

)

```

### 5.4 FTB Quests

- クエストデータは `pack/config/ftbquests/quests/chapters/` に SNBT 形式で保存される

- 商品数が100を超えるため、**手作業では作らない**。`data/prices.yaml` から `scripts/gen_quests.py` で生成する

- クエスト名には価格を含める形式にする（例: `鉄インゴット ×8 — 80`）

- **リピートクエストには既知の不具合がある**（再入場で報酬を再取得できる、チームで報酬が複製される）。販売機能の実装前に人間が再現テストを行う。詳細は `docs/decisions.md` を参照

---

## 6. 採用mod（現時点）

確定した役割のみ記載する。バージョンと正確な mod ID は `data/mods.yaml` で管理する。

| 領域 | mod | 役割 |

|---|---|---|

| 季節 | Serene Seasons | 進行のリズム、温室、シーズンセンサー |

| 農業 | Mystical Agriculture | 資源の自給、エッセンス装備 |

| 作物 | Croptopia | 作物の種類 |

| 料理 | Farmer's Delight（＋アドオン群） | 加工と付加価値 |

| 工業 | Create | 省力化、連続組み立て |

| 工業 | Create: Crafts & Additions | 回転力→RF変換 |

| 魔法 | Ars Nouveau | Enchanting Apparatus、使い魔、Agronomic Sourcelink |

| 畜産 | Caged Mobs | モブドロップの牧場化 |

| 通貨 | Numismatics | コインアイテム |

| 進行 | FTB Quests | チュートリアル、進捗管理、販売 |

| 依頼 | Bountiful | 日替わり依頼の掲示板 |

| エンド | End Remastered | 12種のエンダーアイ |

| 釣り | Aquaculture 2 | 独立した収入源 |

| 内装 | Handcrafted / Supplementaries | 拠点の成長実感 |

| 開発 | KubeJS / ProbeJS / JEI / Jade | レシピ改変と確認 |

---

## 7. 未決定事項

実装前に人間の判断が必要な項目。勝手に決めない。

- [ ] 料理納品の時給想定（これが決まらないと価格表全体が決まらない）

- [ ] Caged Mobs と Ars Nouveau の Drygmy を両方入れるか、片方に絞るか

- [ ] End Remastered の目を自然入手できるルートを残すか、儀式のみにするか

- [ ] 鉱石以外の鉄入手経路（村チェスト、鉄ゴーレム、ゾンビドロップ、ピグリン交易）をどこまで塞ぐか

- [ ] FTB Quests のリピートクエスト不具合の再現有無と、その結果に応じた販売実装の方式

- [ ] 12種の目に割り当てる料理チェーン

---

## 8. コミット規約

- 1コミット1目的。生成スクリプトの変更と生成物の反映は分けない（同時にコミットする）

- コミットメッセージは日本語で可。何を変えたかを先頭行に書く

- 設計判断を伴う変更は `docs/decisions.md` に理由を追記する

- `pack/` 配下だけを手で書き換えたコミットは作らない。必ず `data/` と `scripts/` を経由する

---

## 9. 作業開始時の手順

1. このファイルと `docs/decisions.md` を読む

2. 未決定事項に触れる作業かどうかを確認する

3. 触れる場合は、実装せずに選択肢と推奨案を提示する

4. 触れない場合は着手してよい。ただし ID の確認手順（3.1）を必ず踏む
