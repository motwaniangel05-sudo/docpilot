import json, re, collections
from pathlib import Path
from docpilot.sandbox import run_snippet

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "ai_systems.json").read_text())
FENCE = re.compile(r"```(?:python|py)?\n(.*?)```", re.S)
KNOWN = {"ok", "warning", "error", "timeout"}


def norm(r):
    if isinstance(r, dict):
        s = r.get("status") or r.get("got") or r.get("result")
        m = r.get("message") or r.get("msg") or r.get("detail") or r.get("error") or ""
    elif isinstance(r, (tuple, list)):
        s = r[0]
        m = r[1] if len(r) > 1 else ""
    else:
        s = getattr(r, "status", None)
        m = getattr(r, "message", "")
    if s not in KNOWN:
        return "unknown", repr(r)[:200]
    return s, str(m)[:200]


def category(status, msg):
    if status == "error" and "NameError" in msg:
        return "incomplete_snippet"
    if status == "error":
        return "real_error"
    return status


out = {}
for sysname in ("plain", "full"):
    rows = []
    for i, d in data.items():
        for k, b in enumerate(FENCE.findall(d[sysname]["answer"])):
            s, m = norm(run_snippet(b, "2.2"))
            c = category(s, m)
            rows.append({"id": i, "block": k, "status": s, "category": c, "message": m})
            print(f"{sysname:5} {i} {c:18} {m[:60]}")
    counts = collections.Counter(r["category"] for r in rows)
    out[sysname] = {"blocks": len(rows), "counts": dict(counts), "results": rows}
    print("===", sysname, len(rows), "blocks", dict(counts), "===")

json.dump(out, open(ROOT / "data" / "ai_answer_exec.json", "w"), indent=1)
print("saved data/ai_answer_exec.json")
