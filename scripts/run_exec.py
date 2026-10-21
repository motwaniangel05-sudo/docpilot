import json, collections
from docpilot.sandbox import run_snippet

blocks = [b for b in json.load(open("data/exec_blocks.json")) if b["lib"] == "pandas"]
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

results = []
for b in blocks:
    s, m = norm(run_snippet(b["code"], b["version"]))
    results.append({"idx": b["idx"], "version": b["version"], "symbol": b["symbol"],
                    "status": s, "message": m})
    print(f"{s:8} pandas {b['version']}  {b['symbol'][:30]:30} {m[:60]}")

counts = collections.Counter(r["status"] for r in results)
n = len(results)
print()
print("total run:", n, "|", dict(counts))
if n:
    print("ran without error (ok+warning): %.1f%%" % (100 * (counts["ok"] + counts["warning"]) / n))
    print("clean ok: %.1f%%" % (100 * counts["ok"] / n))
json.dump({"n": n, "counts": dict(counts), "results": results},
          open("data/exec_results.json", "w"), indent=1)
print("saved data/exec_results.json")
