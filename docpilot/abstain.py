import json
from pathlib import Path

CFG = Path(__file__).resolve().parent.parent / "data" / "abstain_config.json"
THRESHOLD = json.load(open(CFG))["threshold"] if CFG.exists() else 0.394
MESSAGE = "Cannot confirm for your version."


def scored_search(s, query, version, k=5, pool=30):
    """Hybrid search + rerank. Returns (top reranker score, top-k chunks). s must be a Searcher with a reranker."""
    dense = s._dense(query, version, pool)
    sparse = s._bm25(query, version, pool)
    rrf = {}
    for ranking in (dense, sparse):
        for r, idx in enumerate(ranking):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (60 + r + 1)
    fused = sorted(rrf, key=rrf.get, reverse=True)[:pool]
    sc = s.reranker.predict([(query, s.chunks[i]["text"]) for i in fused])
    order = sorted(zip(sc, fused), key=lambda x: -x[0])
    return float(order[0][0]), [s.chunks[i] for _, i in order[:k]]


def should_abstain(score):
    return score < THRESHOLD
