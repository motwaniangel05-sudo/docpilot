import json
import random
import re
import sys
import time

import numpy as np

sys.path.insert(0, ".")
from docpilot.changes import Changes
from docpilot.search import Searcher
from docpilot.version import detect_version

random.seed(42)
TARGET_TOTAL = 90

chunks = json.load(open("data/chunks.json"))
by = {(c["symbol"], c["version"]): c for c in chunks}
syms = sorted({c["symbol"] for c in chunks})
exists = {v: {c["symbol"] for c in chunks if c["version"] == v} for v in ("1.5", "2.2")}
ch = Changes(chunks)


def summary(c):
    doc = c["docstring"].strip()
    first = re.split(r"\n\s*\n", doc)[0].replace("\n", " ").strip()
    first = re.split(r"(?<=\.)\s", first)[0].replace("`", "").rstrip(".")
    return first


def ok(sym, ver):
    c = by.get((sym, ver))
    return c is not None and len(summary(c)) >= 20


def target_word(sym):
    if sym.startswith("DataFrame."):
        return "DataFrame"
    if sym.startswith("Series."):
        return "Series"
    return "top-level function"


def question(sym, user_ver, src_ver):
    return f"In pandas {user_ver}, with a {target_word(sym)}: {summary(by[(sym, src_ver)])}"


removed = [s for s in syms if s in exists["1.5"] and s not in exists["2.2"] and ok(s, "1.5")]
added = [s for s in syms if s in exists["2.2"] and s not in exists["1.5"] and ok(s, "2.2")]
both = [s for s in syms if s in exists["1.5"] and s in exists["2.2"] and ok(s, "1.5") and ok(s, "2.2")]
changed_real = [s for s in both if "parameters" in (ch.note(s, "2.2") or "")]
changed_other = [s for s in both if s not in changed_real and by[(s, "1.5")]["signature"] != by[(s, "2.2")]["signature"]]
for lst in (removed, added, changed_real, changed_other):
    random.shuffle(lst)
removed, added = removed[:20], added[:10]
need = TARGET_TOTAL - 2 * len(removed) - 2 * len(added)
changed = (changed_real + changed_other)[:need]

Q = []
for s in removed:
    Q.append(dict(q=question(s, "2.2", "1.5"), user_version="2.2", target=None, trap=True, kind="removed"))
    Q.append(dict(q=question(s, "1.5", "1.5"), user_version="1.5", target=s, trap=False, kind="removed"))
for s in added:
    Q.append(dict(q=question(s, "1.5", "2.2"), user_version="1.5", target=None, trap=True, kind="added"))
    Q.append(dict(q=question(s, "2.2", "2.2"), user_version="2.2", target=s, trap=False, kind="added"))
for i, s in enumerate(changed):
    v = "1.5" if i % 2 == 0 else "2.2"
    Q.append(dict(q=question(s, v, v), user_version=v, target=s, trap=False, kind="changed"))

n_trap = sum(q["trap"] for q in Q)
n_recall = sum(q["target"] is not None for q in Q)
print(f"questions: {len(Q)} (trap: {n_trap}, recall: {n_recall}) removed={len(removed)} added={len(added)} changed={len(changed)}")
json.dump(Q, open("data/benchmark.json", "w"), indent=2)

searcher = Searcher(use_reranker=True, device="cpu")
configs = [
    ("No filter, no reranker", False, False),
    ("Version filter, no reranker", True, False),
    ("No filter + reranker", False, True),
    ("Version filter + reranker (full system)", True, True),
]


def pct(x):
    return f"{100 * x:.1f}%"


table, details = [], {}
detect_ok = sum(detect_version(q["q"])[0] == q["user_version"] for q in Q) / len(Q)

for name, use_filter, rerank in configs:
    for item in Q[:3]:
        searcher.search(item["q"], version=None, rerank=rerank)
    lat, rows = [], []
    for item in Q:
        t0 = time.perf_counter()
        ver, _ = detect_version(item["q"])
        res = searcher.search(item["q"], version=ver if use_filter else None, k=5, rerank=rerank)
        lat.append((time.perf_counter() - t0) * 1000)
        uv = item["user_version"]
        rows.append(dict(
            q=item["q"], kind=item["kind"], user_version=uv, target=item["target"], trap=item["trap"],
            top5=[f'{r["symbol"]} v{r["version"]}' for r in res],
            stale=[r["symbol"] not in exists[uv] for r in res],
            wrong_version_top1=res[0]["version"] != uv,
            hit=(any(r["symbol"] == item["target"] and r["version"] == uv for r in res) if item["target"] else None),
        ))
    trap = [r for r in rows if r["trap"]]
    rec = [r for r in rows if r["hit"] is not None]
    table.append(
        f"| {name} | {pct(np.mean([r['stale'][0] for r in trap]))} | {pct(np.mean([any(r['stale']) for r in trap]))} | "
        f"{pct(np.mean([r['wrong_version_top1'] for r in rows]))} | {pct(np.mean([r['hit'] for r in rec]))} | "
        f"{np.percentile(lat, 50):.0f} | {np.percentile(lat, 95):.0f} |"
    )
    details[name] = rows
    print("done:", name)

md = f"""# Evaluation results

Benchmark: {len(Q)} auto-generated questions from symbol differences between pandas 1.5.3 and 2.2.3
(removed={len(removed)}, added={len(added)}, changed signatures={len(changed)}).
Trap questions (stale-answer test): {n_trap}. Recall questions: {n_recall}. Version detection accuracy: {pct(detect_ok)}.

| Config | Stale@1 (trap) | Stale@5 (trap) | Wrong-version@1 | Recall@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
""" + "\n".join(table) + """

Definitions:
- Stale@1 / Stale@5: share of trap questions where the top-1 / any of the top-5 results is a symbol that does not exist in the user's pandas version (for example DataFrame.append for a pandas 2.2 user).
- Wrong-version@1: share of all questions whose top-1 chunk belongs to the other pandas version.
- Recall@5: share of recall questions where the correct symbol, in the user's version, is in the top 5.
- Latency: search only, per query, on a MacBook (M1) CPU, after 3 warm-up queries.
- Caveat: questions are built from docstring summaries, so they leak some wording of the target symbol.
"""
open("results.md", "w").write(md)
json.dump(details, open("data/eval_details.json", "w"), indent=2)
print(md)
