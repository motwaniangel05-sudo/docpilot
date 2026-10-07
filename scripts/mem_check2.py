import resource
import sys

import torch

sys.path.insert(0, ".")
from sentence_transformers import CrossEncoder

from docpilot.abstain import scored_search
from docpilot.search import Searcher

mode = sys.argv[1]
s = Searcher(use_reranker=False, device="cpu")
kw = {"automodel_args": {"torch_dtype": torch.bfloat16}} if mode == "bf16" else {}
s.reranker = CrossEncoder("BAAI/bge-reranker-base", device="cpu", **kw)
tests = [
    ("how do I append a row in pandas 1.5", "1.5", "pandas"),
    ("numpy 2.1 product of array elements", "2.1", "numpy"),
    ("scikit-learn 1.3 random forest classifier", "1.3", "sklearn"),
    ("how do I bake sourdough bread in pandas 2.2", "2.2", "pandas"),
]
for q, v, lib in tests:
    sc, res = scored_search(s, q, v, library=lib)
    print(f"{mode} score={float(sc):.3f} top1={res[0]['symbol']} | {q}")
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
print(f"{mode}: peak memory {peak:.0f} MB")
