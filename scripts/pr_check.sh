#!/usr/bin/env bash
# usage: bash scripts/pr_check.sh <git-diff-range> <pandas-version>
# Checks changed .py files. Never runs them. Always exits 0; the result is in GITHUB_OUTPUT.
set -u
RANGE="$1"
VER="$2"
PY="${PY:-python}"
OUT=pr_report.txt
: > "$OUT"
status=0
files=0
while IFS= read -r -d '' f; do
  files=$((files + 1))
  res=$("$PY" -m docpilot check "$f" --pandas "$VER" 2>&1)
  code=$?
  if [ "$code" -eq 1 ]; then
    status=1
  fi
  printf '%s\n' "$res" | grep -v '^$' | grep -v 'breaking call(s) for pandas' >> "$OUT"
done < <(git diff --name-only -z --diff-filter=ACMR "$RANGE" -- '*.py' ':(exclude)scripts/*')
count=$(grep -c ': removed \|: deprecated ' "$OUT")
{
  echo "status=$status"
  echo "files=$files"
  echo "count=$count"
} >> "${GITHUB_OUTPUT:-/dev/null}"
echo "files=$files breaking=$count status=$status"
cat "$OUT"
