import argparse
import sys
from pathlib import Path

from docpilot.checker import SUPPORTED, check_code
from docpilot.upgrade import MAX_FILE_BYTES, SKIP_DIRS


def collect(path):
    p = Path(path)
    if p.is_file():
        return [p]
    out = []
    for f in sorted(p.rglob("*.py")):
        parts = f.relative_to(p).parts[:-1]
        if any(x in SKIP_DIRS or x.startswith(".venv") for x in parts):
            continue
        out.append(f)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="docpilot", description="Static pandas upgrade checker (never runs your code).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a .py file or a folder")
    c.add_argument("path")
    c.add_argument("--pandas", required=True, choices=SUPPORTED, help="target pandas version")
    args = ap.parse_args(argv)

    p = Path(args.path)
    if not p.exists():
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 2
    files = collect(args.path)
    if not files:
        print("error: no .py files found", file=sys.stderr)
        return 2

    breaking, low, errors = 0, 0, 0
    for f in files:
        if f.stat().st_size > MAX_FILE_BYTES:
            print(f"{f}: skipped (over 2 MB)", file=sys.stderr)
            continue
        out = check_code(f.read_text(encoding="utf-8", errors="replace"), args.pandas)
        if out["error"]:
            errors += 1
            print(f"{f}: could not parse ({out['error']})", file=sys.stderr)
            continue
        for x in out["findings"]:
            if x["confidence"] == "high":
                breaking += 1
                print(f"{f}:{x['line']}: {x['status']} {x['symbol']} (since {x['since']}) -> {x['replacement']}")
            else:
                low += 1
                print(f"{f}:{x['line']}: check by hand: {x['symbol']} (low confidence)")
    print(f"\n{breaking} breaking call(s) for pandas {args.pandas} in {len(files)} file(s); "
          f"{low} low-confidence (not counted); {errors} file(s) not parsed.")
    return 1 if breaking else 0


if __name__ == "__main__":
    sys.exit(main())
