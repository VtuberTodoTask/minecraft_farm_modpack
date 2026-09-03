# mod を入れる手順

CLAUDE.md 3.1（IDを推測しない）と 4章（jar はコミットしない）を守りながら
mod を追加するための手順。

---

## 0. 先に決めること

mod を落とす前に3つ決める必要がある。ここが決まらないと、
バージョンを選べないか、後で入れ替えることになる。

### (1) Forge のバージョン

`data/mods.yaml` の `loader_version` と `pack/pack.toml` の `[versions]` が
どちらも未記入。packwiz は `[versions]` に loader が無いと動かないので、
**これが最初のブロッカー**になる。

1.20.1 対応の各 mod が揃うバージョンを1つ選んで固定する。
決めたら両方に同じ値を書く（食い違うと後で必ず事故る）。

### (2) Caged Mobs と Drygmy のどちらを使うか（CLAUDE.md 7章）

モブドロップの牧場化をどちらで実現するか。役割が重なるので両方入れる必要は薄い。

| | Caged Mobs | Ars Nouveau の Drygmy |
|---|---|---|
| 仕組み | 檻に入れて放置でドロップ | 使い魔が囲いの中のモブから集める |
| 前提 | 単体で完結 | Ars Nouveau と Source が要る |
| 憲法との相性 | 工業寄り。放置で完結する | 魔法寄り。Source 経由で畑に依存する |
| mod 数 | 1つ増える | 増えない（Ars Nouveau は既に採用） |

**推奨は Drygmy 一本**。理由は、Drygmy が Source を要求し、Source は
Agronomic Sourcelink で畑から供給される（憲法 2.5）ため、
**モブドロップの生産量が畑の規模に縛られる**から。
憲法 2.1 の「規模を拡大するほど農業の規模も要求される」がそのまま効く。
mod が1つ減るのも利点。

Caged Mobs を選ぶ理由があるとすれば、Ars Nouveau に入る前の序盤から
モブドロップを扱わせたい場合。畜産を early game に置きたいなら
そちらが素直になる。**ここは進行設計の判断なので決めてほしい。**

### (3) Farmer's Delight のアドオンをどれにするか

CLAUDE.md 6章は「Farmer's Delight（＋アドオン群）」としか書いていない。
アドオンは料理の種類 = 買取品目の数に直結するので、
`data/prices.yaml` を書き始める前に確定させたい。

---

## 1. jar を集める

packwiz で管理する（CLAUDE.md 4章）。`pack/` で作業する。

```sh
cd pack
packwiz modrinth add <slug>      # Modrinth から
packwiz curseforge add <slug>    # CurseForge から
```

生成されるのは `pack/mods/<name>.pw.toml` というメタデータだけで、
**jar 本体はリポジトリに入らない**。これが意図した状態。

正確なコマンドとフラグは `packwiz --help` で確認すること
（ここでは検証できていないため、形だけ示している）。

`pack/pack.toml` の `[versions]` に loader が無いと弾かれるはずなので、
先に 0-(1) を済ませておく。

実際の jar は `packwiz install` などで手元に展開する。
`.gitignore` で `*.jar` を弾いてあるので、どこに置いても
リポジトリに紛れ込むことはない。

## 2. mod ID を data/mods.yaml に写す

**手で転記しない。** 19件を目で写すと必ず打ち間違える。
jar から機械的に読む。

```sh
# まず確認だけ（何も書き換えない）
python3 scripts/sync_mod_ids.py ~/mc-test/mods

# 内容を見て納得したら書き込む
python3 scripts/sync_mod_ids.py ~/mc-test/mods --write
git diff data/mods.yaml
```

このスクリプトは各 jar の `META-INF/mods.toml` から `modId` と `version` を
読み、`displayName` を頼りに `data/mods.yaml` の `name` と突き合わせて埋める。

抑えてある点:

- `version` が `${file.jarVersion}` のときは `MANIFEST.MF` の
  `Implementation-Version` から拾い直す（Forge ではよくある）
- 1つの jar に複数の mod が入っている場合も全部拾う
- 同じ mod に複数の jar が当たったら、選べないので**中止する**。
  勝手にどちらかを採ることはしない
- 名前が結びつかなかった jar は「未照合」として一覧に出す。
  推測で結びつけない（ライブラリ mod はここに出るが、放置してよい）
- `candidates:`（検討中で未採用）は対象外

書き換えは対象の行だけを差し替えるので、コメントや並び順は保たれる。

## 3. 入れたあとに確認すること

mod を入れると、バニラだけのときには無かった問題が出る。

### 鉱石除去が mod 鉱石に効いていない

バニラの worldgen 除去は **mod が追加した鉱石を止めない**（CLAUDE.md 5.1）。
各 mod の config 側で切る必要がある。
`docs/testing.md` の手順で走査したうえで、残っているものを個別に潰す。

なお `scripts/scan_world_ores.py` が数えるのは
`data/ore_removal.yaml` に載っているブロックだけなので、
mod 鉱石を見張りたければそのブロックIDを `data/` 側に足すことになる。

### Mystical Agriculture の鉱石は「残っている」のが正解

Prosperity / Inferium 鉱石は除去の例外（憲法 2.2）。
**消すと鉄ツルハシ以降の進行が詰む。**
消えていないことを確認する。

### KubeJS が kubejs/data/ を読んでいるか

いまの鉱石除去は `pack/kubejs/data/` に置いてある（CLAUDE.md 5.1）。
バニラだけのテストで確認できるのは JSON の中身であって、
**KubeJS がこの場所を datapack として読む経路は未検証**。
KubeJS を入れた初回に、鉱石が実際に消えているかで確認する。

### End Remastered の End Castle

`strongholds` を空にしただけでは mod 側の生成は止まらない（CLAUDE.md 5.2）。
End Remastered の config で切る。設定キー名は jar で確認すること。

## 4. 決まったことを記録する

0章の3つを決めたら、理由を `docs/decisions.md` に追記する（CLAUDE.md 8章）。
特に Caged Mobs / Drygmy の選択は進行設計に効くので、
なぜそちらにしたかを残しておかないと後で判断できなくなる。

決着したら CLAUDE.md 7章のチェックボックスも消すこと。
