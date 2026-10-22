import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from docpilot.upgrade import scan_files, SKIP_DIRS, MAX_FILE_BYTES

out = {}
for name in ("xarray", "statsmodels", "scikit-learn"):
    base = Path("/tmp/repos") / name
    commit = subprocess.run(["git", "-C", str(base), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    files = {}
    for p in sorted(base.rglob("*.py")):
        rel = p.relative_to(base).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")[:-1]) or p.stat().st_size > MAX_FILE_BYTES:
            continue
        files[rel] = p.read_bytes()
    rep = scan_files(files, "1.5", "2.2")
    out[name] = {"commit": commit, "files_scanned": rep["files_scanned"],
                 "syntax_errors": len(rep["syntax_errors"]),
                 "breaking_high": rep["breaking_total"], "removed": rep["breaking_removed"],
                 "deprecated": rep["breaking_deprecated"],
                 "low_confidence": len(rep["low_confidence"]),
                 "findings": rep["breaking"]}
    o = out[name]
    print("=====", name, commit, {k: o[k] for k in ("files_scanned", "syntax_errors", "breaking_high", "removed", "deprecated", "low_confidence")})
    for r in rep["breaking"]:
        line = files[r["file"]].decode("utf-8", "replace").split("\n")[r["line"] - 1].strip()[:70]
        print(f"  {r['file'].split('/')[-1]}:{r['line']} {r['symbol']} | {line}")
json.dump(out, open(ROOT / "data" / "repo_scan_final.json", "w"), indent=1)
print("saved data/repo_scan_final.json")
