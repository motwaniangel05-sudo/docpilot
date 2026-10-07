import json
import re
import sys

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

sys.path.insert(0, ".")
from docpilot.detect import detect_target

PREFIX = "Represent this sentence for searching relevant passages: "
chunks = json.load(open("data/chunks.json"))
bench = json.load(open("data/benchmark_multi.json"))
nat = json.load(open("data/natural_scores.json"))
tok = lambda t: re.findall(r"[a-z0-9_]+", t.lower())
bm25 = BM25Okapi([tok(c["text"][:2000]) for c in chunks])
lib_arr = np.array([c["library"] for c in chunks])
ver_arr = np.array([c["version"] for c in chunks])
exists = {}
for c in chunks:
    exists.setdefault((c["library"], c["version"]), set()).add(c["symbol"])
texts = [c["text"][:2000] for c in chunks]

questions = [dict(q=b["q"], lib=b["lib"], uv=b["user_version"], target=b["target"], trap=b["trap"], grp="bench") for b in bench]
questions += [dict(q=n["q"], lib=detect_target(n["q"])[0], uv=n["version"], target=n["target"], trap=False, grp="natural") for n in nat]


def run(model_path, mode):
    m = SentenceTransformer(model_path, device="mps")
    m.max_seq_length = 512
    E = m.encode(texts, batch_size=32, normalize_embeddings=True)
    Q = m.encode([PREFIX + x["q"] for x in questions], batch_size=32, normalize_embeddings=True)
    rows = []
    for qi, x in enumerate(questions):
        lib, ver, _ = detect_target(x["q"])
        mask = (lib_arr == lib) & (ver_arr == ver)
        dense = np.where(mask, E @ Q[qi], -9)
        d_ids = [int(i) for i in np.argsort(-dense)[:30] if mask[i]]
        if mode == "dense":
            ranked = d_ids
        else:
            sc = np.where(mask, bm25.get_scores(tok(x["q"])), -9)
            s_ids = [int(i) for i in np.argsort(-sc)[:30] if mask[i]]
            rrf = {}
            for ranking in (d_ids, s_ids):
                for r, i in enumerate(ranking):
                    rrf[i] = rrf.get(i, 0) + 1 / (61 + r)
            ranked = sorted(rrf, key=rrf.get, reverse=True)
        syms = [chunks[i]["symbol"] for i in ranked]
        rank = next((k + 1 for k, s in enumerate(syms) if s == x["target"]), None) if x["target"] else None
        rows.append(dict(grp=x["grp"], trap=x["trap"], rank=rank, target=x["target"],
                         stale1=(syms[0] not in exists[(x["lib"], x["uv"])]) if x["trap"] else None))
    return rows


def stats(rows):
    b = [r for r in rows if r["grp"] == "bench" and r["target"]]
    n = [r for r in rows if r["grp"] == "natural"]
    t = [r for r in rows if r["trap"]]
    f = lambda rs, k: np.mean([(r["rank"] or 999) <= k for r in rs])
    return dict(r1=f(b, 1), r5=f(b, 5), stale1=np.mean([r["stale1"] for r in t]), nat5=f(n, 5), nat1=f(n, 1))


out, lines = {}, []
for name, path in (("base bge-small", "BAAI/bge-small-en-v1.5"), ("fine-tuned bge-small", "models/bge-small-docpilot")):
    for mode in ("dense", "hybrid"):
        s = stats(run(path, mode))
        out[f"{name} | {mode}"] = {k: round(float(v), 4) for k, v in s.items()}
        lines.append(f"| {name} | {mode} | {100*s['r1']:.1f}% | {100*s['r5']:.1f}% | {100*s['stale1']:.1f}% | {100*s['nat1']:.1f}% | {100*s['nat5']:.1f}% |")
        print(lines[-1], flush=True)
json.dump(out, open("data/ablation_finetune.json", "w"), indent=2)
section = (
    "\n## Embedding fine-tuning ablation\n\n"
    "bge-small fine-tuned with MultipleNegativesRankingLoss on 1132 synthetic (question, chunk) pairs built from docstring summaries "
    "(2 epochs, lr 2e-5, batch 32). Symbols and summaries used in the 150-question benchmark or the 24 natural questions were excluded from training. "
    "Version filter on, no reranker. Benchmark = 121 recall questions (Recall@1, Recall@5) and 29 trap questions (Stale@1); Natural = 24 hand-written questions.\n\n"
    "| Embedder | Retrieval | Recall@1 | Recall@5 | Stale@1 | Natural R@1 | Natural R@5 |\n|---|---|---|---|---|---|---|\n"
    + "\n".join(lines) + "\n\n"
    "Caveats: training questions are synthetic templates over docstring first lines (the same source as the benchmark, so the benchmark is easier than real queries); "
    "NumPy ufunc docstrings start with a signature, which adds noisy pairs; the natural set is small.\n"
)
md = open("results.md").read()
md = re.sub(r"\n## Embedding fine-tuning ablation.*?(?=\n## |\Z)", "", md, flags=re.S).rstrip() + "\n" + section
open("results.md", "w").write(md)
