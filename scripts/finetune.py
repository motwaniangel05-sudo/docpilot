import json
import random
import re

import torch
from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader

random.seed(0)
PREFIX = "Represent this sentence for searching relevant passages: "
DISPLAY = {"pandas": "pandas", "numpy": "numpy", "sklearn": "scikit-learn"}

chunks = json.load(open("data/chunks.json"))
bench = json.load(open("data/benchmark_multi.json"))
nat = json.load(open("data/natural_scores.json"))


def summary(c):
    doc = c["docstring"].strip()
    first = re.split(r"\n\s*\n", doc)[0].replace("\n", " ").strip()
    return re.split(r"(?<=\.)\s", first)[0].replace("`", "").rstrip(".")


held_summaries = {b["q"].split(": ", 1)[1] for b in bench}
held_symbols = {b["target"] for b in bench if b["target"]} | {n["target"] for n in nat}

by_sym = {}
for c in chunks:
    by_sym.setdefault((c["library"], c["symbol"]), []).append(c)

TEMPLATES = [
    lambda lib, v, s: f"how do I {s[0].lower() + s[1:]}",
    lambda lib, v, s: f"{s} using {DISPLAY[lib]} {v}",
    lambda lib, v, s: f"which function lets me {s[0].lower() + s[1:]}",
]

ex, skipped = [], 0
for (lib, sym), cs in sorted(by_sym.items()):
    if sym in held_symbols or any(summary(c) in held_summaries for c in cs):
        skipped += 1
        continue
    cs = [c for c in cs if len(summary(c)) >= 20]
    if not cs:
        continue
    c = random.choice(cs)
    q = random.choice(TEMPLATES)(lib, c["version"], summary(c))
    ex.append(InputExample(texts=[PREFIX + q, c["text"][:2000]]))

print(f"training pairs: {len(ex)} (symbols held out of training: {skipped})")
print("example:", ex[0].texts[0])

device = "cpu"
model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
model.max_seq_length = 128
dl = DataLoader(ex, shuffle=True, batch_size=32)
loss = losses.MultipleNegativesRankingLoss(model)
model.fit(train_objectives=[(dl, loss)], epochs=2, warmup_steps=10,
          optimizer_params={"lr": 2e-5}, show_progress_bar=True)
model.max_seq_length = 512
model.save("models/bge-small-docpilot")
json.dump({"pairs": len(ex), "held_out_symbols": skipped, "epochs": 2, "lr": 2e-5, "batch": 32},
          open("data/finetune_info.json", "w"), indent=2)
print("saved models/bge-small-docpilot")
