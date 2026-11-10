#!/usr/bin/env python3
"""Check UTF-8 byte size of tracked Markdown documents.

- > 20,000 bytes: non-blocking warning asking to consider splitting by
  meaning unit (purpose and reader).
- > 40,000 bytes: fail unless the file has a reasoned exception in
  .github/doc-size-exceptions.tsv (path, kind, max_bytes, reason).
- Exceptions must be used, existing, unique, and within their max_bytes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WARN_BYTES = 20_000
FAIL_BYTES = 40_000
EXCEPTIONS_PATH = Path(".github/doc-size-exceptions.tsv")
VALID_KINDS = {"upstream", "legal", "generated", "record"}

SKIP_PREFIXES = ("vendor/",)


def tracked_markdown() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"],
        check=True,
        capture_output=True,
    ).stdout
    names = [n.decode("utf-8", "surrogateescape") for n in out.split(b"\0") if n]
    return [n for n in names if not n.startswith(SKIP_PREFIXES)]


def load_exceptions(path: Path) -> dict[str, tuple[str, int, str]]:
    ex: dict[str, tuple[str, int, str]] = {}
    if not path.exists():
        return ex
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        cols = raw.split("\t")
        if len(cols) != 4:
            print(f"::error file={path}::{lineno}行目は path<TAB>kind<TAB>max_bytes<TAB>reason の4列にしてください。")
            sys.exit(1)
        name, kind, maxb, reason = cols
        if name in ex:
            print(f"::error file={path}::{lineno}行目: 例外 {name} が重複しています。")
            sys.exit(1)
        if kind not in VALID_KINDS:
            print(f"::error file={path}::{lineno}行目: kind {kind} は {sorted(VALID_KINDS)} のいずれかにしてください。")
            sys.exit(1)
        try:
            max_bytes = int(maxb)
        except ValueError:
            print(f"::error file={path}::{lineno}行目: max_bytes {maxb} は整数にしてください。")
            sys.exit(1)
        if not reason.strip():
            print(f"::error file={path}::{lineno}行目: 例外には理由が必要です。")
            sys.exit(1)
        ex[name] = (kind, max_bytes, reason)
    return ex


def main() -> int:
    files = tracked_markdown()
    exceptions = load_exceptions(EXCEPTIONS_PATH)
    used: set[str] = set()
    status = 0

    for name in files:
        p = Path(name)
        if p.is_symlink():
            continue
        try:
            data = p.read_bytes()
            data.decode("utf-8", "strict")
        except (OSError, UnicodeDecodeError) as e:
            print(f"::error file={name}::読み取りまたは UTF-8 デコードに失敗しました: {e}")
            status = 1
            continue
        size = len(data)
        if size <= WARN_BYTES:
            continue
        if name in exceptions:
            used.add(name)
            _, max_bytes, _ = exceptions[name]
            if size <= max_bytes:
                print(f"例外適用: {name} ({size} bytes, 上限 {max_bytes})")
                continue
            print(f"::error file={name}::{size} bytes が例外の上限 {max_bytes} bytes を超えています。")
            status = 1
            continue
        if size <= FAIL_BYTES:
            print(f"::warning file={name}::{size} bytes は {WARN_BYTES} 超です。意味単位（目的と読者）での分割を検討してください。")
        else:
            print(f"::error file={name}::{size} bytes は {FAIL_BYTES} 超です。意味単位で分割するか、.github/doc-size-exceptions.tsv に理由付きの例外を登録してください。")
            status = 1

    for name in exceptions:
        if name not in used:
            kind = "file=" + name
            if not Path(name).exists():
                print(f"::error {kind}::例外リストのパスが存在しません: {name}")
            elif name not in files:
                print(f"::error {kind}::例外リストのパスは追跡対象の Markdown ではありません: {name}")
            else:
                size = len(Path(name).read_bytes())
                print(f"::error {kind}::未使用の例外です（現在 {size} bytes で {WARN_BYTES} 以下、または例外が不要）: {name}")
            status = 1

    if status == 0:
        print(f"ok: {len(files)} files checked")
    return status


if __name__ == "__main__":
    sys.exit(main())
