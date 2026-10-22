import json, re, collections
from pathlib import Path
from docpilot.sandbox import run_snippet

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "ai_systems.json").read_text())
before = json.loads((ROOT / "data" / "ai_answer_exec.json").read_text())
FENCE = re.compile(r"```(?:python|py)?\n(.*?)```", re.S)
KNOWN = {"ok", "warning", "error", "timeout"}

EXTRA = '''
_idx = pd.date_range("2024-01-01", periods=3, freq="D")
df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0], "c": ["x", "y", "z"],
                   "col": ["a", "b", "a"], "A": ["g1", "g2", "g1"],
                   "ts": ["2024-01-01 10:00:00", "2024-01-02 11:00:00", "2024-01-03 12:00:00"],
                   "x": [1.0, None, 3.0]}, index=_idx)
s = pd.Series([1.0, 2.0, 3.0], index=_idx)
'''


def norm(r):
    if isinstance(r, dict):
        st = r.get("status") or r.get("got") or r.get("result")
        m = r.get("message") or r.get("msg") or r.get("detail") or r.get("error") or ""
    elif isinstance(r, (tuple, list)):
        st = r[0]
        m = r[1] if len(r) > 1 else ""
    else:
        st = getattr(r, "status", None)
        m = getattr(r, "message", "")
    if st not in KNOWN:
        return "unknown", repr(r)[:200]
    return st, str(m)[:200]


def category(st, m):
    if st == "error" and "NameError" in m:
        return "incomplete_snippet"
    if st == "error":
        return "real_error"
    return st


out = {}
for sysname in ("plain", "full"):
    rows = []
    old = {(r["id"], r["block"]): r["category"] for r in before[sysname]["results"]}
    for i, d in data.items():
        for k, b in enumerate(FENCE.findall(d[sysname]["answer"])):
            st, m = norm(run_snippet(EXTRA + b, "2.2"))
            c = category(st, m)
            rows.append({"id": i, "block": k, "category": c, "was": old.get((i, k)), "message": m})
            if c != old.get((i, k)):
                print(f"{sysname:5} {i} b{k}: {old.get((i, k))} -> {c}  {m[:55]}")
    counts = collections.Counter(r["category"] for r in rows)
    out[sysname] = {"blocks": len(rows), "counts": dict(counts), "results": rows}
    print("===", sysname, len(rows), "blocks", dict(counts), "===")

json.dump(out, open(ROOT / "data" / "ai_answer_exec_fixed.json", "w"), indent=1)
print("saved data/ai_answer_exec_fixed.json")
