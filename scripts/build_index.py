import json
import pickle
import re
import shutil
from pathlib import Path

import torch
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path("index")
QDRANT_DIR = INDEX_DIR / "qdrant"
BM25_PATH = INDEX_DIR / "bm25.pkl"
MAX_CHARS = 2000

if INDEX_DIR.exists():
    shutil.rmtree(INDEX_DIR)
INDEX_DIR.mkdir()

chunks = json.load(open("data/chunks.json"))
for c in chunks:
    c["text"] = c["text"][:MAX_CHARS]

device = "mps" if torch.backends.mps.is_available() else "cpu"
print("device:", device)
model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
vectors = model.encode(
    [c["text"] for c in chunks],
    batch_size=32,
    normalize_embeddings=True,
    show_progress_bar=True,
)

client = QdrantClient(path=str(QDRANT_DIR))
client.create_collection(
    "docs", vectors_config=VectorParams(size=vectors.shape[1], distance=Distance.COSINE)
)
client.upsert(
    "docs",
    points=[PointStruct(id=i, vector=vectors[i].tolist(), payload=c) for i, c in enumerate(chunks)],
)
client.close()


def tok(t):
    return re.findall(r"[a-z0-9_]+", t.lower())


tokens = [tok(c["text"]) for c in chunks]
with open(BM25_PATH, "wb") as f:
    pickle.dump({"chunks": chunks, "tokens": tokens}, f)

print(f"indexed {len(chunks)} chunks")
