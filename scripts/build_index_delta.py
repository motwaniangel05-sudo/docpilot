import json
import pickle
import re
import shutil
import subprocess
from collections import OrderedDict
from pathlib import Path

import torch
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

OUT = Path("index_delta")
MAX_CHARS = 2000
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

chunks = json.load(open("data/chunks.json"))
groups = OrderedDict()
for c in chunks:
    groups.setdefault((c["library"], c["symbol"], c["text"]), []).append(c)

delta = []
for (lib, sym, text), cs in groups.items():
    d = {k: cs[0][k] for k in ("library", "symbol", "kind", "signature", "docstring", "valid_from", "valid_until")}
    d["text"] = text[:MAX_CHARS]
    d["applies"] = [c["version"] for c in cs]
    delta.append(d)

device = "mps" if torch.backends.mps.is_available() else "cpu"
model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
vectors = model.encode([d["text"] for d in delta], batch_size=32, normalize_embeddings=True, show_progress_bar=True)

client = QdrantClient(path=str(OUT / "qdrant"))
client.create_collection("docs", vectors_config=VectorParams(size=vectors.shape[1], distance=Distance.COSINE))
client.upsert("docs", points=[PointStruct(id=i, vector=vectors[i].tolist(), payload=d) for i, d in enumerate(delta)])
client.close()

tok = lambda t: re.findall(r"[a-z0-9_]+", t.lower())
with open(OUT / "bm25.pkl", "wb") as f:
    pickle.dump({"chunks": delta, "tokens": [tok(d["text"]) for d in delta]}, f)
print(f"delta index: {len(delta)} chunks (naive {len(chunks)})")


def mb(p):
    return int(subprocess.check_output(["du", "-sk", p]).split()[0]) / 1024


naive, dl = mb("index"), mb("index_delta")
print(f"naive index: {naive:.1f} MB (qdrant {mb('index/qdrant'):.1f}, bm25 {mb('index/bm25.pkl'):.1f})")
print(f"delta index: {dl:.1f} MB (qdrant {mb('index_delta/qdrant'):.1f}, bm25 {mb('index_delta/bm25.pkl'):.1f})")
print(f"size reduction: {100 * (1 - dl / naive):.1f}%")
json.dump({"naive_mb": round(naive, 1), "delta_mb": round(dl, 1), "naive_chunks": len(chunks),
           "delta_chunks": len(delta), "reduction_pct": round(100 * (1 - dl / naive), 1)},
          open("data/delta_size.json", "w"), indent=2)
