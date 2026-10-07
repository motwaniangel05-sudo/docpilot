import pickle
import re
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "index"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def tok(t):
    return re.findall(r"[a-z0-9_]+", t.lower())


class Searcher:
    def __init__(self, use_reranker=True, device="cpu"):
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
        self.client = QdrantClient(path=str(INDEX_DIR / "qdrant"))
        data = pickle.load(open(INDEX_DIR / "bm25.pkl", "rb"))
        self.chunks = data["chunks"]
        self.bm25 = BM25Okapi(data["tokens"])
        self.reranker = CrossEncoder("BAAI/bge-reranker-base", device=device) if use_reranker else None

    def _dense(self, query, version, k, library="pandas"):
        q = self.model.encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()
        must = []
        if library:
            must.append(FieldCondition(key="library", match=MatchValue(value=library)))
        if version:
            must.append(FieldCondition(key="version", match=MatchValue(value=version)))
        flt = Filter(must=must) if must else None
        pts = self.client.query_points("docs", query=q, query_filter=flt, limit=k).points
        return [p.id for p in pts]

    def _bm25(self, query, version, k, library="pandas"):
        scores = self.bm25.get_scores(tok(query))
        order = np.argsort(-scores)
        out = []
        for i in order:
            c = self.chunks[i]
            if library and c["library"] != library:
                continue
            if version and c["version"] != version:
                continue
            out.append(int(i))
            if len(out) == k:
                break
        return out

    def search(self, query, version=None, k=5, rerank=True, pool=30, library="pandas"):
        dense = self._dense(query, version, pool, library)
        sparse = self._bm25(query, version, pool, library)
        rrf = {}
        for ranking in (dense, sparse):
            for rank, idx in enumerate(ranking):
                rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (60 + rank + 1)
        fused = sorted(rrf, key=rrf.get, reverse=True)[:pool]
        if rerank and self.reranker is not None:
            pairs = [(query, self.chunks[i]["text"]) for i in fused]
            scores = self.reranker.predict(pairs)
            fused = [i for _, i in sorted(zip(scores, fused), key=lambda x: -x[0])]
        return [self.chunks[i] for i in fused[:k]]
