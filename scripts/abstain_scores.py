import json
import sys

import numpy as np
from qdrant_client.models import FieldCondition, Filter, MatchValue

sys.path.insert(0, ".")
from docpilot.search import QUERY_PREFIX, Searcher

OOS = [
    "how do I bake sourdough bread at home",
    "what is the capital of Australia",
    "train a convolutional neural network on MNIST",
    "how to center a div in CSS",
    "best way to learn the guitar quickly",
    "deploy a Docker container to AWS Lambda",
    "write a SQL query that joins three tables",
    "how do I change a flat tire on a bicycle",
    "explain the plot of Hamlet",
    "set up a React project with Vite",
    "convert Celsius to Fahrenheit by hand",
    "how do I make a git branch from a tag",
    "what is the speed of light in a vacuum",
    "plot a 3D surface with matplotlib",
    "fine-tune BERT for sentiment analysis",
    "how to get a Schengen visa as a student",
    "reverse a linked list in C++",
    "how do I cook basmati rice",
    "install CUDA drivers on Ubuntu",
    "write a regular expression for email validation",
]

bench = json.load(open("data/benchmark.json"))
items = []
for b in bench:
    items.append(dict(q=b["q"], user_version=b["user_version"], target=b["target"],
                      group="trap" if b["trap"] else "recall"))
for i, t in enumerate(OOS):
    v = "1.5" if i % 2 == 0 else "2.2"
    items.append(dict(q=f"In pandas {v}, {t}", user_version=v, target=None, group="oos"))

s = Searcher(use_reranker=True, device="cpu")
out = []
for n, it in enumerate(items, 1):
    v = it["user_version"]
    qv = s.model.encode(QUERY_PREFIX + it["q"], normalize_embeddings=True).tolist()
    flt = Filter(must=[FieldCondition(key="version", match=MatchValue(value=v))])
    pts = s.client.query_points("docs", query=qv, query_filter=flt, limit=30).points
    dense_ids = [p.id for p in pts]
    dense_top = float(pts[0].score)
    sparse_ids = s._bm25(it["q"], v, 30)
    rrf = {}
    for ranking in (dense_ids, sparse_ids):
        for r, idx in enumerate(ranking):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (60 + r + 1)
    fused = sorted(rrf, key=rrf.get, reverse=True)[:30]
    sc = s.reranker.predict([(it["q"], s.chunks[i]["text"]) for i in fused])
    order = sorted(zip(sc, fused), key=lambda x: -x[0])
    top5 = [s.chunks[i] for _, i in order[:5]]
    hit = None
    if it["target"]:
        hit = any(c["symbol"] == it["target"] and c["version"] == v for c in top5)
    out.append(dict(it, dense_top=dense_top, rr_top=float(order[0][0]),
                    top1=f'{top5[0]["symbol"]} v{top5[0]["version"]}', hit=hit))
    if n % 10 == 0:
        print(f"{n}/{len(items)}", flush=True)

json.dump(out, open("data/abstain_scores.json", "w"), indent=2)
for g in ("recall", "trap", "oos"):
    r = [x for x in out if x["group"] == g]
    print(g, len(r),
          "dense_top mean %.3f" % np.mean([x["dense_top"] for x in r]),
          "rr_top mean %.2f" % np.mean([x["rr_top"] for x in r]))
