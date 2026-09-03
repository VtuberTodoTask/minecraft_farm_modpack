#!/usr/bin/env python3
"""手元の mod jar から mod ID とバージョンを読み取り、data/mods.yaml を埋める。

CLAUDE.md 3.1 は mod ID を記憶や推測で書くことを禁じ、jar の中身で確認する
ことを求めている。19件を手で転記すると必ず打ち間違えるので、機械的に写す。

使い方:
    python3 scripts/sync_mod_ids.py <jarのあるディレクトリ>            # 確認だけ（既定）
    python3 scripts/sync_mod_ids.py <jarのあるディレクトリ> --write    # data/mods.yaml を更新

例:
    python3 scripts/sync_mod_ids.py ~/mc-test/mods
    python3 scripts/sync_mod_ids.py ~/mc-test/mods --write

既定では何も書き換えず、何をどう埋めるかだけを表示する。
内容を見て納得してから --write を付けること。

照合は jar の displayName と data/mods.yaml の name で行う。
自動で結びつかなかったものは「未照合」として一覧に出す。
推測で結びつけることはしない。
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODS_YAML = REPO / "data" / "mods.yaml"

# Forge の mods.toml では version に ${file.jarVersion} が入っていることがある。
# その場合の実体は MANIFEST.MF の Implementation-Version にある。
JAR_VERSION_PLACEHOLDER = "${file.jarVersion}"


def normalize(name: str) -> str:
    """照合用にゆるく正規化する。大小・記号・空白の違いを吸収する。"""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def manifest_version(zf: zipfile.ZipFile) -> str | None:
    try:
        raw = zf.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
    except KeyError:
        return None
    # MANIFEST.MF は72バイトで折り返され、継続行は先頭が空白になる。
    unfolded = raw.replace("\r\n", "\n").replace("\r", "\n").replace("\n ", "")
    for line in unfolded.split("\n"):
        if line.lower().startswith("implementation-version:"):
            return line.split(":", 1)[1].strip()
    return None


def read_jar(path: Path) -> list[dict]:
    """1つの jar から [[mods]] エントリを読む。Forge 以外は空を返す。"""
    out: list[dict] = []
    try:
        with zipfile.ZipFile(path) as zf:
            try:
                raw = zf.read("META-INF/mods.toml")
            except KeyError:
                return []
            try:
                doc = tomllib.loads(raw.decode("utf-8", "replace"))
            except tomllib.TOMLDecodeError as e:
                print(f"  ! {path.name}: mods.toml を解釈できない: {e}", file=sys.stderr)
                return []
            fallback = manifest_version(zf)
    except (zipfile.BadZipFile, OSError) as e:
        print(f"  ! {path.name}: 読めない: {e}", file=sys.stderr)
        return []

    for entry in doc.get("mods") or []:
        mod_id = entry.get("modId")
        if not isinstance(mod_id, str) or not mod_id:
            continue
        version = entry.get("version")
        if not isinstance(version, str) or version == JAR_VERSION_PLACEHOLDER:
            version = fallback
        display = entry.get("displayName") or mod_id
        out.append({
            "mod_id": mod_id,
            "version": version,
            "display_name": display if isinstance(display, str) else mod_id,
            "jar": path.name,
        })
    return out


def mods_section(text: str) -> tuple[int, int]:
    """mods.yaml の `mods:` ブロックの範囲を返す。

    candidates:（検討中で未採用）は対象外。ここを混ぜると、採用していない mod を
    「jar が見つからない」と報告してしまう。
    """
    m = re.search(r"^mods:$", text, re.M)
    if not m:
        return -1, -1
    start = m.end()
    nxt = re.search(r"^[a-zA-Z_][a-zA-Z0-9_]*:", text[start:], re.M)
    end = len(text) if not nxt else start + nxt.start()
    return start, end


def yaml_entry_names(text: str) -> list[str]:
    """mods.yaml の mods: 配下にある name を、書かれている順に拾う。"""
    start, end = mods_section(text)
    if start == -1:
        return []
    return re.findall(r'^  - name: "([^"]+)"', text[start:end], re.M)


def fill(text: str, name: str, mod_id: str, version: str | None) -> tuple[str, bool]:
    """`- name: "<name>"` のブロック内の mod_id / version を書き換える。

    次の `- name:` が現れるまでをそのエントリの範囲とみなす。
    """
    start = text.find(f'  - name: "{name}"')
    if start == -1:
        return text, False
    nxt = text.find('\n  - name: "', start + 1)
    end = len(text) if nxt == -1 else nxt
    block = text[start:end]

    new = re.sub(r"^(    mod_id:).*$", f'\\1 "{mod_id}"', block, count=1, flags=re.M)
    if version is None:
        new = re.sub(r"^(    version:).*$", r"\1 null", new, count=1, flags=re.M)
    else:
        new = re.sub(r"^(    version:).*$", f'\\1 "{version}"', new, count=1, flags=re.M)

    if new == block:
        return text, False
    return text[:start] + new + text[end:], True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mods_dir", type=Path, help="mod の jar が入ったディレクトリ")
    ap.add_argument("--write", action="store_true", help="data/mods.yaml を実際に書き換える")
    args = ap.parse_args()

    mods_dir: Path = args.mods_dir.expanduser().resolve()
    if not mods_dir.is_dir():
        print(f"ディレクトリが無い: {mods_dir}", file=sys.stderr)
        return 2

    jars = sorted(mods_dir.glob("*.jar"))
    if not jars:
        print(f"{mods_dir} に .jar が無い。", file=sys.stderr)
        return 2

    found: list[dict] = []
    for jar in jars:
        found.extend(read_jar(jar))

    print(f"jar {len(jars)} 個から mod {len(found)} 件を読んだ。")
    if not found:
        print("Forge の META-INF/mods.toml を持つ jar が1つも無い。", file=sys.stderr)
        return 2
    print()

    text = MODS_YAML.read_text(encoding="utf-8")
    names = yaml_entry_names(text)
    by_norm = {normalize(n): n for n in names}

    matched: list[tuple[str, dict]] = []
    unmatched: list[dict] = []
    for m in found:
        key = normalize(m["display_name"])
        target = by_norm.get(key) or by_norm.get(normalize(m["mod_id"]))
        if target:
            matched.append((target, m))
        else:
            unmatched.append(m)

    # 同じ mods.yaml エントリに複数の jar が当たったら、選べないので止める。
    seen: dict[str, dict] = {}
    conflicts: list[str] = []
    for target, m in matched:
        if target in seen and seen[target]["mod_id"] != m["mod_id"]:
            conflicts.append(f'{target}: {seen[target]["jar"]} と {m["jar"]}')
        seen[target] = m

    print(f"照合できたもの（{len(seen)} 件）:")
    for target, m in sorted(seen.items()):
        ver = m["version"] or "(バージョン不明)"
        print(f'  {target}')
        print(f'      mod_id: {m["mod_id"]}   version: {ver}   <- {m["jar"]}')
    print()

    if unmatched:
        print(f"未照合の jar（{len(unmatched)} 件）— data/mods.yaml に対応する name が無い:")
        for m in sorted(unmatched, key=lambda x: x["display_name"]):
            print(f'  {m["display_name"]}  (mod_id: {m["mod_id"]})  <- {m["jar"]}')
        print("  ライブラリ mod なら放置してよい。採用 mod なら data/mods.yaml に行を足すこと。")
        print()

    missing = [n for n in names if n not in seen]
    if missing:
        print(f"jar が見つからなかったもの（{len(missing)} 件）:")
        for n in missing:
            print(f"  {n}")
        print()

    if conflicts:
        print("同じ mod に複数の jar が当たっている。どちらを採るか決められないので中止する:",
              file=sys.stderr)
        for c in conflicts:
            print(f"  {c}", file=sys.stderr)
        return 2

    if not args.write:
        print("確認のみ。書き換えるには --write を付けること。")
        return 0

    updated = 0
    for target, m in seen.items():
        text, ok = fill(text, target, m["mod_id"], m["version"])
        if ok:
            updated += 1

    MODS_YAML.write_text(text, encoding="utf-8")
    print(f"data/mods.yaml を更新した（{updated} 件）。")
    print("git diff で内容を確認すること。")
    if missing:
        print(f"{len(missing)} 件はまだ null のまま。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
