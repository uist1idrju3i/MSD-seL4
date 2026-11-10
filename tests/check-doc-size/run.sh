#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
checker="$repo_root/.github/scripts/check-doc-size.py"
test_root="$(mktemp -d)"

cleanup() {
	rm -rf "$test_root"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

fail() {
	printf 'not ok - %s\n' "$*" >&2
	exit 1
}

setup_repo() {
	dir="$1"
	mkdir -p "$dir/.github/scripts"
	cp "$checker" "$dir/.github/scripts/check-doc-size.py"
	git -C "$dir" init -q
	git -C "$dir" config user.email t@t && git -C "$dir" config user.name t
}

# Case 1: small file passes.
d="$test_root/small"; setup_repo "$d"
printf '# 小さい文書\n' > "$d/a.md"; git -C "$d" add a.md
( cd "$d" && python3 .github/scripts/check-doc-size.py ) || fail "small file should pass"

# Case 2: >20,000 bytes warns but does not fail.
d="$test_root/warn"; setup_repo "$d"
python3 -c "open('$d/a.md','w').write('x'*20001)"
git -C "$d" add a.md
out="$(cd "$d" && python3 .github/scripts/check-doc-size.py)" || fail "20,001 bytes should warn only"
echo "$out" | grep -q '::warning' || fail "expected warning for 20,001 bytes"

# Case 3: exactly 20,000 passes silently.
d="$test_root/edge"; setup_repo "$d"
python3 -c "open('$d/a.md','w').write('x'*20000)"
git -C "$d" add a.md
out="$(cd "$d" && python3 .github/scripts/check-doc-size.py)" || fail "20,000 bytes should pass"
echo "$out" | grep -q '::warning' && fail "no warning expected at exactly 20,000"

# Case 4: >40,000 fails without exception.
d="$test_root/big"; setup_repo "$d"
python3 -c "open('$d/a.md','w').write('x'*40001)"
git -C "$d" add a.md
( cd "$d" && python3 .github/scripts/check-doc-size.py ) && fail "40,001 bytes should fail"

# Case 5: exception within max_bytes passes; over max fails.
d="$test_root/exc"; setup_repo "$d"
python3 -c "open('$d/a.md','w').write('x'*41000)"
printf 'a.md\trecord\t42000\tsingle tracking table\n' > "$d/.github/doc-size-exceptions.tsv"
git -C "$d" add a.md .github/doc-size-exceptions.tsv
( cd "$d" && python3 .github/scripts/check-doc-size.py ) || fail "exception should pass"
python3 -c "open('$d/a.md','w').write('x'*43000)"
( cd "$d" && python3 .github/scripts/check-doc-size.py ) && fail "over exception max should fail"

# Case 6: unused / missing / duplicate exceptions fail.
d="$test_root/exc-unused"; setup_repo "$d"
printf '# ok\n' > "$d/a.md"; git -C "$d" add a.md
printf 'ghost.md\trecord\t42000\tx\n' > "$d/.github/doc-size-exceptions.tsv"
( cd "$d" && python3 .github/scripts/check-doc-size.py ) && fail "missing exception path should fail"
printf 'a.md\trecord\t42000\tx\n' > "$d/.github/doc-size-exceptions.tsv"
( cd "$d" && python3 .github/scripts/check-doc-size.py ) && fail "unused exception should fail"

# Case 7: Japanese text is measured in UTF-8 bytes, not characters.
d="$test_root/jp"; setup_repo "$d"
python3 -c "open('$d/a.md','w').write('あ'*7000)"  # 21,000 bytes
git -C "$d" add a.md
out="$(cd "$d" && python3 .github/scripts/check-doc-size.py)" || fail "jp warn should not fail"
echo "$out" | grep -q '::warning' || fail "expected warning for 21,000 UTF-8 bytes"

# Case 8: invalid UTF-8 fails.
d="$test_root/utf8"; setup_repo "$d"
python3 -c "open('$d/a.md','wb').write(b'ok\xff\xfe')"; git -C "$d" add a.md
( cd "$d" && python3 .github/scripts/check-doc-size.py ) && fail "invalid UTF-8 should fail"

# Case 9: vendor/ prefix is skipped.
d="$test_root/vendor"; setup_repo "$d"
mkdir -p "$d/vendor/sub"
python3 -c "open('$d/vendor/sub/a.md','w').write('x'*50000)"
git -C "$d" add vendor/sub/a.md
( cd "$d" && python3 .github/scripts/check-doc-size.py ) || fail "vendor should be skipped"

# Case 10: symlinked file is not double-counted.
d="$test_root/link"; setup_repo "$d"
python3 -c "open('$d/real.md','w').write('x'*41000)"
printf 'real.md\trecord\t42000\tx\n' > "$d/.github/doc-size-exceptions.tsv"
ln -s real.md "$d/link.md"
git -C "$d" add real.md link.md .github/doc-size-exceptions.tsv
( cd "$d" && python3 .github/scripts/check-doc-size.py ) || fail "symlink should be skipped"

printf 'ok - check-doc-size\n'
