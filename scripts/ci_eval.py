import json
import sys
import time

import numpy as np

sys.path.insert(0, ".")
from docpilot.detect import detect_target
from docpilot.delta import DeltaSearcher

EPS = 1e-9
chunks = json.load(open("data/chunks.json"))
bench = json.load(open("data/benchmark_multi.json"))
exists = {}
for c in chunks:
    exists.setdefault((c["library"], c["version"]), set()).add(c["symbol"])

USE_RR = "--full" in sys.argv
searcher = DeltaSearcher(use_reranker=USE_RR, device="cpu")
for item in bench[:3]:
    lib, ver, _ = detect_target(item["q"])
    searcher.search(item["q"], version=None, rerank=USE_RR, library=lib)

lat, stale1, hits = [], [], []
for item in bench:
    t0 = time.perf_counter()
    lib, ver, _ = detect_target(item["q"])
    res = searcher.search(item["q"], version=ver, k=5, rerank=USE_RR, library=lib)
    lat.append((time.perf_counter() - t0) * 1000)
    uv = item["user_version"]
    if item["trap"]:
        stale1.append(res[0]["symbol"] not in exists[(item["lib"], uv)])
    if item["target"]:
        hits.append(any(r["symbol"] == item["target"] and r["version"] == uv for r in res))

m = {
    "stale_at1": round(float(np.mean(stale1)), 4),
    "recall_at5": round(float(np.mean(hits)), 4),
    "p50_ms": round(float(np.percentile(lat, 50))),
    "p95_ms": round(float(np.percentile(lat, 95))),
    "n_questions": len(bench),
}
json.dump(m, open("data/ci_metrics.json", "w"), indent=2)
print("METRICS:", m)

if "--update-baseline" in sys.argv:
    json.dump({"stale_at1": m["stale_at1"], "recall_at5": m["recall_at5"]}, open("baseline.json", "w"), indent=2)
    print("baseline.json written")
    sys.exit(0)

base = json.load(open("baseline.json"))
fails = []
if m["stale_at1"] > base["stale_at1"] + EPS:
    fails.append(f"stale_at1 worse: {m['stale_at1']} > baseline {base['stale_at1']}")
if m["recall_at5"] < base["recall_at5"] - EPS:
    fails.append(f"recall_at5 worse: {m['recall_at5']} < baseline {base['recall_at5']}")
if fails:
    print("REGRESSION:\n" + "\n".join(fails))
    sys.exit(1)
print("OK: no regression vs baseline.json")
