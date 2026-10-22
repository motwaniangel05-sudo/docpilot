import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from docpilot.upgrade import scan_files, SKIP_DIRS, MAX_FILE_BYTES

REPOS = ["xarray", "statsmodels", "scikit-learn"]
out = {}
for name in REPOS:
    base = Path("/tmp/repos") / name
    if not base.exists():
        print(name, "NOT CLONED")
        continue
    commit = subprocess.run(["git", "-C", str(base), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    files, skipped = {}, 0
    for p in sorted(base.rglob("*.py")):
        rel = p.relative_to(base).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")[:-1]) or p.stat().st_size > MAX_FILE_BYTES:
            skipped += 1
            continue
        files[rel] = p.read_bytes()
    rep = scan_files(files, "1.5", "2.2")
    uses_pd = sum(1 for b in files.values() if b"pandas" in b or b"import pd" in b)
    out[name] = {"commit": commit, "files_scanned": rep["files_scanned"], "files_mentioning_pandas": uses_pd,
                 "skipped": skipped, "breaking_total": rep["breaking_total"],
                 "removed": rep["breaking_removed"], "deprecated": rep["breaking_deprecated"],
                 "syntax_errors": len(rep["syntax_errors"]),
                 "top_symbols": rep["top_symbols"], "sample": rep["breaking"][:12]}
    o = out[name]
    print("=====", name, o["commit"])
    print({k: o[k] for k in ("files_scanned", "files_mentioning_pandas", "skipped", "breaking_total",
                              "removed", "deprecated", "syntax_errors")})
    print("top:", o["top_symbols"])
    for r in o["sample"]:
        print("  ", r["file"], r["line"], r["symbol"], r["status"], r["confidence"])
json.dump(out, open(ROOT / "data" / "repo_scan_after_fix.json", "w"), indent=1)
print("saved data/repo_scan_after_fix.json")
