# minecraft_farm_modpack

Minecraft 1.20.1 / Forge 向けの modpack。
農業・畜産で生計を立て、そのままエンダードラゴン討伐まで繋げる。

設計の根幹は [`CLAUDE.md`](CLAUDE.md) にある。**作業前に必ず読むこと。**

## いまの状態

パック本体はまだ動かない。決まっていることと決まっていないことの区別は以下。

| 領域 | 状態 |
|---|---|
| 鉱石除去 | 実装済み（未起動検証）。バニラ鉱石19件と要塞生成を無効化 |
| 設計ドキュメント | 一通りあり |
| mod ID / バージョン | **未確定**。jar が無く確認できないため空にしてある |
| 価格表 | **空**。基準時給が未決定（CLAUDE.md 7章） |
| 目12種の料理チェーン | **空**。未決定（CLAUDE.md 7章） |
| FTB Quests の SNBT 生成 | 未実装。販売方式が未確定なため |

空欄は「作業漏れ」ではなく「人間の判断待ち」。
埋めてよいかどうかは CLAUDE.md 7章を見る。

## 構成

```
data/      設計データ。ここが唯一の正
scripts/   data/ から pack/ を生成する
pack/      パック本体。生成物を手で編集しない
docs/      設計と決定の記録
```

流れは一方向。`data/` を直す → `scripts/` を走らせる → `pack/` に反映される。
`pack/` を直接編集したコミットは作らない（CLAUDE.md 8章）。

## 使い方

必要なもの: Python 3.11 以上、PyYAML。

```sh
pip install pyyaml
```

生成:

```sh
python3 scripts/gen_ore_removal.py    # 鉱石除去データパック
python3 scripts/gen_recipes.py        # 目のレシピ（data/eyes.yaml が空のあいだは何も出ない）
python3 scripts/gen_quests.py         # 価格表の検査（SNBT 生成は未実装）
```

実機テスト用:

```sh
python3 scripts/build_test_datapack.py <出力先>   # バニラで読める datapack に詰め直す
python3 scripts/scan_world_ores.py <world/region> # 生成済みワールドの鉱石を数える
```

手順は [`docs/testing.md`](docs/testing.md)。鉱石除去は mod 無しで検証できる。

検証（`pack/` が `data/` と一致しているか）:

```sh
python3 scripts/gen_ore_removal.py --check
python3 scripts/gen_recipes.py --check
python3 scripts/gen_quests.py --lint
```

`--check` は書き込まずに差分の有無だけを見る。
`pack/` が手で編集されていたらここで落ちる。

## 検証について

**このリポジトリではゲームを起動して確認できない。**

そのため、生成物には `UNTESTED` を付けてある。
「動作確認済み」と書けるのは人間が実際に起動して確認した場合だけ
（CLAUDE.md 3.3）。

鉱石除去は**既存チャンクには効かない**。テストは必ず新規ワールドで行う。

実機で確認する手順は [`docs/testing.md`](docs/testing.md) にある。

## mod の jar について

jar はコミットしない。packwiz のメタデータ（`.pw.toml`）で管理する。
`.gitignore` で `*.jar` を弾いてある。
