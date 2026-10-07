import pickle
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

import numpy as np

from docpilot.search import QUERY_PREFIX, ROOT, Searcher, tok

DELTA_DIR = ROOT / "index"


class DeltaSearcher(Searcher):
    """Same API as Searcher, but each chunk stores the list of versions it applies to."""

    def __init__(self, use_reranker=True, device="cpu"):
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
        self.client = QdrantClient(path=str(DELTA_DIR / "qdrant"))
        data = pickle.load(open(DELTA_DIR / "bm25.pkl", "rb"))
        self.chunks = data["chunks"]
        self.bm25 = BM25Okapi(data["tokens"])
        self.reranker = CrossEncoder("BAAI/bge-reranker-base", device=device) if use_reranker else None

    def _dense(self, query, version, k, library="pandas"):
        q = self.model.encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()
        must = []
        if library:
            must.append(FieldCondition(key="library", match=MatchValue(value=library)))
        if version:
            must.append(FieldCondition(key="applies", match=MatchValue(value=version)))
        flt = Filter(must=must) if must else None
        return [p.id for p in self.client.query_points("docs", query=q, query_filter=flt, limit=k).points]

    def _bm25(self, query, version, k, library="pandas"):
        order = np.argsort(-self.bm25.get_scores(tok(query)))
        out = []
        for i in order:
            c = self.chunks[i]
            if library and c["library"] != library:
                continue
            if version and version not in c["applies"]:
                continue
            out.append(int(i))
            if len(out) == k:
                break
        return out

    def search(self, query, version=None, k=5, rerank=True, pool=30, library="pandas"):
        res = super().search(query, version=version, k=k, rerank=rerank, pool=pool, library=library)
        return [dict(c, version=version if version else c["applies"][-1]) for c in res]
