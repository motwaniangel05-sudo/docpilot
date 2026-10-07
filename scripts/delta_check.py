import json
import sys

import numpy as np

sys.path.insert(0, ".")
from docpilot.delta import DeltaSearcher
from docpilot.detect import detect_target
from docpilot.search import Searcher

bench = json.load(open("data/benchmark_multi.json"))
chunks = json.load(open("data/chunks.json"))
exists = {}
for c in chunks:
    exists.setdefault((c["library"], c["version"]), set()).add(c["symbol"])
A, B = Searcher(use_reranker=False), DeltaSearcher(use_reranker=False)
same, st = 0, {"naive": [], "delta": []}
hit = {"naive": [], "delta": []}
for it in bench:
    lib, ver, _ = detect_target(it["q"])
    ra = A.search(it["q"], version=ver, k=5, rerank=False, library=lib)
    rb = B.search(it["q"], version=ver, k=5, rerank=False, library=lib)
    same += [(r["symbol"], r["version"]) for r in ra] == [(r["symbol"], r["version"]) for r in rb]
    for name, res in (("naive", ra), ("delta", rb)):
        if it["trap"]:
            st[name].append(res[0]["symbol"] not in exists[(it["lib"], it["user_version"])])
        if it["target"]:
            hit[name].append(any(r["symbol"] == it["target"] and r["version"] == it["user_version"] for r in res))
print(f"identical top-5 lists: {same}/{len(bench)}")
for n in ("naive", "delta"):
    print(f"{n}: stale@1={np.mean(st[n]):.4f} recall@5={np.mean(hit[n]):.4f}")
