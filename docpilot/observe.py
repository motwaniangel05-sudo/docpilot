import json
import logging
import time
from collections import OrderedDict
from pathlib import Path

from docpilot.search import Searcher

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "queries.jsonl"

# Cost per query is $0.00: all models (bge-small, bge-reranker-base) run locally on CPU,
# there are no paid API calls, and the app is hosted on the free Streamlit Community Cloud tier.
COST_PER_QUERY_USD = 0.0

_logger = logging.getLogger("docpilot")
if not _logger.handlers:
    LOG_PATH.parent.mkdir(exist_ok=True)
    _h = logging.FileHandler(LOG_PATH)
    _h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)


class ObservedSearcher:
    def __init__(self, use_reranker=True, device="cpu", cache_size=256):
        self.inner = Searcher(use_reranker=use_reranker, device=device)
        self.cache = OrderedDict()
        self.cache_size = cache_size

    def search(self, query, version=None, k=5, rerank=True):
        key = (" ".join(query.lower().split()), version, k, rerank)
        t0 = time.perf_counter()
        hit = key in self.cache
        if hit:
            self.cache.move_to_end(key)
            res = self.cache[key]
        else:
            res = self.inner.search(query, version=version, k=k, rerank=rerank)
            self.cache[key] = res
            if len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)
        ms = (time.perf_counter() - t0) * 1000
        _logger.info(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "query": query,
            "version": version,
            "k": k,
            "rerank": rerank,
            "cache_hit": hit,
            "latency_ms": round(ms, 2),
            "top1": f"{res[0]['symbol']} v{res[0]['version']}" if res else None,
            "n_results": len(res),
            "cost_usd": COST_PER_QUERY_USD,
        }))
        return res
