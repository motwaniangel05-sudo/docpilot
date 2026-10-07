import resource
import sys

sys.path.insert(0, ".")
from docpilot.abstain import scored_search
from docpilot.search import Searcher

rr = sys.argv[1] == "rr"
s = Searcher(use_reranker=rr, device="cpu")
if rr:
    scored_search(s, "numpy 2.1 product of array elements", "2.1", library="numpy")
else:
    s.search("numpy 2.1 product of array elements", version="2.1", rerank=False, library="numpy")
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6  # bytes on macOS -> MB
print(f"{'with reranker (abstention on)' if rr else 'no reranker'}: peak memory {peak:.0f} MB")
