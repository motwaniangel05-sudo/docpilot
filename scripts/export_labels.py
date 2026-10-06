import csv
import json
import random
import re

random.seed(7)
FULL = {"1.5": "1.5.3", "2.2": "2.2.3"}

chunks = json.load(open("data/chunks.json"))
bench = json.load(open("data/benchmark.json"))

meta = {}
for c in chunks:
    meta.setdefault(c["symbol"], (c["valid_from"], c["valid_until"]))


def url(sym, ver):
    return f"https://pandas.pydata.org/pandas-docs/version/{FULL[ver]}/reference/api/pandas.{sym}.html"


def summary(c):
    doc = c["docstring"].strip()
    first = re.split(r"\n\s*\n", doc)[0].replace("\n", " ").strip()
    first = re.split(r"(?<=\.)\s", first)[0].replace("`", "").rstrip(".")
    return first


def target_word(sym):
    if sym.startswith("DataFrame."):
        return "DataFrame"
    if sym.startswith("Series."):
        return "Series"
    return "top-level function"


by_summary = {}
for c in chunks:
    by_summary.setdefault(summary(c), set()).add(c["symbol"])


def exists(sym, ver):
    vf, vu = meta[sym]
    return float(vf) <= float(ver) <= float(vu)


rows = []

for i, b in enumerate(random.sample(bench, 50), 1):
    uv = b["user_version"]
    if b["target"]:
        cands = [b["target"]]
    else:
        tail = b["q"].split(": ", 1)[1]
        word = re.search(r"with a (.+?): ", b["q"]).group(1)
        cands = sorted(s for s in by_summary.get(tail, []) if target_word(s) == word)[:2]
    rows.append(dict(
        id=f"Q{i}", task="question", item=b["q"], user_version=uv,
        candidate=" | ".join(cands),
        url=" | ".join(url(s, uv) for s in cands),
        benchmark_says="n" if b["trap"] else "y",
        human="", note="",
    ))

syms = sorted(meta)
neg, pos = [], []
for s in syms:
    for v in ("1.5", "2.2"):
        (pos if exists(s, v) else neg).append((s, v))
pairs = random.sample(neg, min(10, len(neg)))
pairs += random.sample(pos, 30 - len(pairs))
random.shuffle(pairs)
for i, (s, v) in enumerate(pairs, 1):
    rows.append(dict(
        id=f"V{i}", task="validity", item=s, user_version=v, candidate=s,
        url=url(s, v), benchmark_says="y" if exists(s, v) else "n",
        human="", note="",
    ))

with open("data/labels.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"wrote data/labels.csv: {sum(r['task']=='question' for r in rows)} question rows, "
      f"{sum(r['task']=='validity' for r in rows)} validity rows")
