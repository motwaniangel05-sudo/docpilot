import sys

sys.path.insert(0, ".")
from docpilot.detect import detect_target
from docpilot.search import Searcher

s = Searcher(use_reranker=False, device="cpu")
for q in [
    "how do I append a row in pandas 1.5",
    "pandas 2.0 how do I append a row",
    "numpy 2.1 product of array elements",
    "numpy 1.26 product of array elements",
    "scikit-learn 1.3 random forest classifier",
    "sklearn==1.5.2 split data into train and test",
    "pandas==1.5.3 sklearn grid search",
]:
    lib, v, msg = detect_target(q)
    res = s.search(q, version=v, k=3, rerank=False, library=lib)
    print(f"[{lib} {v}] {q}\n    -> " + " | ".join(f"{r['symbol']} ({r['library']} {r['version']})" for r in res))
