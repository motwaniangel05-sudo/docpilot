import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from docpilot.upgrade import scan_files, SKIP_DIRS, MAX_FILE_BYTES

for name in ("xarray", "statsmodels", "scikit-learn"):
    base = Path("/tmp/repos") / name
    files = {}
    for p in sorted(base.rglob("*.py")):
        rel = p.relative_to(base).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")[:-1]) or p.stat().st_size > MAX_FILE_BYTES:
            continue
        files[rel] = p.read_bytes()
    rep = scan_files(files, "1.5", "2.2")
    print("=====", name, rep["breaking_total"])
    for r in rep["breaking"]:
        line = files[r["file"]].decode("utf-8", "replace").split("\n")[r["line"] - 1].strip()[:95]
        print(f"{r['file'].split('/')[-1]}:{r['line']} [{r['symbol']} {r['confidence']}] {line}")
