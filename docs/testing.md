# 実機テスト手順

CLAUDE.md 3.3 のとおり、`UNTESTED` を外せるのは人間が実際に起動して
確認したときだけ。ここではその手順を書く。

## 何をテストするのか

現時点で実装が終わっているのは**鉱石除去と要塞除去だけ**で、
これは**バニラのdatapackとして完結している**。つまり mod を1つも入れずに
検証できる。modpack 全体のテストより先にこれを済ませるほうが、
問題が出たときの切り分けが楽になる。

| | いつできるか |
|---|---|
| テストA: 鉱石除去・要塞除去（mod無し） | **いま** |
| テストB: modpack 全体 | `data/mods.yaml` の mod ID とバージョンが決まってから |

---

# テストA: 鉱石除去（mod無し）

## 考え方 — 必ずA/Bで比較する

「鉱石が見つからなかった」だけでは、**除去が効いたのか、走査が失敗していたのか
区別がつかない**。そこで同じシードで2つのワールドを作る。

1. **対照区**: datapack 無し → 鉱石が**ある**ことを確認する
2. **実験区**: datapack 有り → 鉱石が**ない**ことを確認する

同じシードで、対照区に鉱石があり実験区に無ければ、それは除去が効いた証拠になる。
この比較を省くと結論が出ないので、面倒でも両方やってほしい。

## 準備

必要なもの:

- Minecraft **1.20.1 のサーバjar**（minecraft.net の server ダウンロード、
  または公式ランチャー経由で入手する）
- Java 17 以上
- Python 3.11 以上と PyYAML（走査スクリプト用）

このリポジトリを clone して、生成物が最新か確認しておく。

```sh
python3 scripts/gen_ore_removal.py --check
```

`OK: 20 ファイルが ...` と出れば `pack/` は `data/` と一致している。

## 手順

### 1. 対照区（datapack 無し）を作る

```sh
mkdir -p ~/mc-test/control && cd ~/mc-test/control
cp /path/to/minecraft_server.1.20.1.jar server.jar
echo "eula=true" > eula.txt

cat > server.properties <<'EOF'
level-seed=1234567890
level-name=world
online-mode=false
EOF

java -Xmx4G -jar server.jar nogui
```

起動時に "Preparing spawn area" が走り、スポーン周辺のチャンクが生成される。
`Done (...)` が出たらコンソールに `stop` と打って止める。

シードは何でもよいが、**実験区と必ず同じ値にする**こと。

### 2. 実験区（datapack 有り）を作る

**ここが一番間違えやすい。** worldgen を変える datapack は、
**ワールドが最初に作られる時点で置かれていないと効かない**。
後から入れても既存チャンクは変わらない。

なので**サーバを起動する前に**ディレクトリを掘って datapack を置く。

```sh
mkdir -p ~/mc-test/trial && cd ~/mc-test/trial
cp /path/to/minecraft_server.1.20.1.jar server.jar
echo "eula=true" > eula.txt

cat > server.properties <<'EOF'
level-seed=1234567890
level-name=world
online-mode=false
EOF

# ワールド生成より先に datapack を置く
mkdir -p world/datapacks
python3 /path/to/minecraft_farm_modpack/scripts/build_test_datapack.py \
    ~/mc-test/trial/world/datapacks/farm_no_ores

java -Xmx4G -jar server.jar nogui
```

`build_test_datapack.py` は `pack/kubejs/data/` の中身に `pack.mcmeta` を
付けて、バニラが読める形にコピーするだけのもの。

起動したら `Done` を待ち、**止める前に**コンソールで確認する。

```
/datapack list
```

`farm_no_ores` が有効側に出ていること。出ていなければ置き場所が違う。

```
/locate structure minecraft:stronghold
```

**見つからないのが正解**（要塞除去が効いている）。座標が返ってきたら効いていない。

確認できたら `stop` で止める。

### 3. 生成量を増やす（任意）

スポーン周辺だけでは標本が小さいと感じたら、止める前に force load する。

```
/forceload add -128 -128 127 127
```

16×16 = 256 チャンク。既定の上限が 256 なのでこれ以上は一度に指定できない。
読み込みが落ち着いてから `stop` する。

### 4. 走査する

```sh
cd /path/to/minecraft_farm_modpack

# 対照区 — 鉱石が「ある」ことを確認する
python3 scripts/scan_world_ores.py ~/mc-test/control/world/region

# 実験区 — 鉱石が「ない」ことを確認する
python3 scripts/scan_world_ores.py ~/mc-test/trial/world/region
```

## 結果の読み方

期待する結果:

| | 対照区 | 実験区 |
|---|---|---|
| 対照ブロック（石・岩盤など） | 見つかる | 見つかる |
| 除去対象の鉱石 | **見つかる** | **0件** |
| 終了コード | 1 | 0 |

対照区で鉱石が0件なら、**そのテストは成立していない**。
走査するディレクトリを間違えているか、チャンクが生成されていない。
この状態で実験区が0件でも、それは除去が効いた証拠にならない。

走査スクリプトは、必ずあるはずのブロック（石・岩盤・深層岩）を対照として
一緒に数えている。これが0件のときは結果を出さずにエラーで止まる。
パーサが壊れて「0件＝成功」に見えるのが一番まずい失敗の仕方なので、
そこだけは落ちるようにしてある。

## ネザー（任意）

クォーツ・ネザー金鉱石・古代の残骸はネザーにしか無い。
確認するならネザーのチャンクを生成してから、次を走査する。

```sh
python3 scripts/scan_world_ores.py ~/mc-test/trial/world/DIM-1/region
```

サーバのコンソールからネザーのチャンクを生成する簡単な方法は無いので、
一度クライアントで繋いでポータルを通るのが早い。

## うまくいかないとき

| 症状 | 見るところ |
|---|---|
| 鉱石が残っている | 既存ワールドで試していないか。datapack はワールド生成前に置いたか |
| `/datapack list` に出ない | 置き場所が `world/datapacks/<名前>/pack.mcmeta` になっているか |
| サーバが datapack を弾く | `pack.mcmeta` の `pack_format` が 15 か（1.20.1 用） |
| 走査が「失敗している」と言う | `world/region` を指しているか。`world` ではない |
| 要塞が見つかってしまう | `structure_set/strongholds.json` が datapack に入っているか |

---

# テストB: modpack 全体

`data/mods.yaml` の mod ID とバージョンが未確定なので、**まだ実施できない**。

決まってから確認することになるのは、少なくとも次の点。

- KubeJS が `kubejs/data/` を datapack として読むか
  （テストAで検証しているのは JSON の中身であって、この読み込み経路ではない）
- mod が追加する鉱石が湧いていないか。バニラの worldgen 除去では止まらないので、
  各 mod の config 側で切る必要がある（CLAUDE.md 5.1）
- Mystical Agriculture の Prosperity / Inferium 鉱石は**残っているか**。
  これは除去の例外で、消すと鉄ツルハシ以降の進行が詰む（憲法 2.2）
- End Remastered の End Castle が生成されていないか（CLAUDE.md 5.2）

---

# 結果の残し方

テストが通ったら、`UNTESTED` を外して結果を記録する。
外してよいのは**実際に起動して確認した範囲だけ**で、
テストAを通しただけで modpack 全体を「動作確認済み」とは書かない。

結果（走査スクリプトの出力そのまま）を貼ってもらえれば、
`UNTESTED` の削除と `docs/decisions.md` への追記はこちらで対応できる。
