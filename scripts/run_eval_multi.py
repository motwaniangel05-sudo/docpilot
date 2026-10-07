import json
import random
import re
import sys
import time

import numpy as np

sys.path.insert(0, ".")
from docpilot.detect import detect_target
from docpilot.search import Searcher

random.seed(42)
PER_LIB = 50
TRAP_PAIRS = 12
DISPLAY = {"pandas": "pandas", "numpy": "numpy", "sklearn": "scikit-learn"}

chunks = json.load(open("data/chunks.json"))
by = {(c["library"], c["symbol"], c["version"]): c for c in chunks}
present, exists, libver = {}, {}, {}
for c in chunks:
    present.setdefault((c["library"], c["symbol"]), set()).add(c["version"])
    exists.setdefault((c["library"], c["version"]), set()).add(c["symbol"])
    libver.setdefault(c["library"], set()).add(c["version"])


def vkey(v):
    return tuple(int(x) for x in v.split("."))


def summary(c):
    doc = c["docstring"].strip()
    first = re.split(r"\n\s*\n", doc)[0].replace("\n", " ").strip()
    first = re.split(r"(?<=\.)\s", first)[0].replace("`", "").rstrip(".")
    return first


def ok(lib, sym, ver):
    c = by.get((lib, sym, ver))
    return c is not None and len(summary(c)) >= 20


def word(lib, sym, ver):
    if lib == "pandas":
        if sym.startswith("DataFrame."):
            return "DataFrame"
        if sym.startswith("Series."):
            return "Series"
        return "top-level function"
    return "class" if by[(lib, sym, ver)]["kind"] == "class" else "function"


def question(lib, sym, user_ver, src_ver):
    return f"In {DISPLAY[lib]} {user_ver}, with a {word(lib, sym, src_ver)}: {summary(by[(lib, sym, src_ver)])}"


Q = []
for lib in ("pandas", "numpy", "sklearn"):
    vers = sorted(libver[lib], key=vkey)
    syms = sorted(s for (l, s) in present if l == lib)
    partial = [s for s in syms if present[(lib, s)] != set(vers)]
    random.shuffle(partial)
    n0 = len(Q)
    used = 0
    for s in partial:
        if used == TRAP_PAIRS:
            break
        okv = [v for v in sorted(present[(lib, s)], key=vkey) if ok(lib, s, v)]
        absent = [v for v in vers if v not in present[(lib, s)]]
        if not okv or not absent:
            continue
        tv = random.choice(absent)
        src = random.choice(okv)
        rv = random.choice(okv)
        Q.append(dict(lib=lib, q=question(lib, s, tv, src), user_version=tv, target=None, trap=True, kind="absent"))
        Q.append(dict(lib=lib, q=question(lib, s, rv, rv), user_version=rv, target=s, trap=False, kind="present"))
        used += 1
    stable = [s for s in syms if present[(lib, s)] == set(vers) and all(ok(lib, s, v) for v in vers)]
    changed = [s for s in stable if len({by[(lib, s, v)]["signature"] for v in vers}) > 1]
    rest = [s for s in stable if s not in changed]
    random.shuffle(changed)
    random.shuffle(rest)
    for s in (changed + rest):
        if len(Q) - n0 >= PER_LIB:
            break
        v = random.choice(vers)
        Q.append(dict(lib=lib, q=question(lib, s, v, v), user_version=v, target=s, trap=False,
                      kind="changed" if s in changed else "stable"))
    print(f"{lib}: {len(Q) - n0} questions (trap {sum(q['trap'] for q in Q[n0:])})", flush=True)

json.dump(Q, open("data/benchmark_multi.json", "w"), indent=2)

searcher = Searcher(use_reranker=True, device="cpu")
configs = [
    ("No version filter, no reranker", False, False),
    ("Version filter, no reranker", True, False),
    ("No version filter + reranker", False, True),
    ("Version filter + reranker (full system)", True, True),
]
pct = lambda x: f"{100 * x:.1f}%"


def metrics(rows):
    trap = [r for r in rows if r["trap"]]
    rec = [r for r in rows if r["hit"] is not None]
    return dict(
        stale1=np.mean([r["stale"][0] for r in trap]) if trap else float("nan"),
        stale5=np.mean([any(r["stale"]) for r in trap]) if trap else float("nan"),
        wrong1=np.mean([r["wrong_version_top1"] for r in rows]),
        recall5=np.mean([r["hit"] for r in rec]) if rec else float("nan"),
    )


detect_ok = np.mean([detect_target(q["q"])[:2] == (q["lib"], q["user_version"]) for q in Q])
table, details, perlib = [], {}, []
for name, use_filter, rerank in configs:
    for it in Q[:3]:
        lib, ver, _ = detect_target(it["q"])
        searcher.search(it["q"], version=None, rerank=rerank, library=lib)
    lat, rows = [], []
    for n, it in enumerate(Q, 1):
        uv = it["user_version"]
        t0 = time.perf_counter()
        lib, ver, _ = detect_target(it["q"])
        res = searcher.search(it["q"], version=ver if use_filter else None, k=5, rerank=rerank, library=lib)
        lat.append((time.perf_counter() - t0) * 1000)
        rows.append(dict(
            q=it["q"], lib=it["lib"], user_version=uv, target=it["target"], trap=it["trap"],
            top5=[f'{r["symbol"]} v{r["version"]}' for r in res],
            stale=[r["symbol"] not in exists[(it["lib"], uv)] for r in res],
            wrong_version_top1=res[0]["version"] != uv,
            hit=(any(r["symbol"] == it["target"] and r["version"] == uv for r in res) if it["target"] else None),
        ))
        if n % 50 == 0:
            print(f"  {name}: {n}/{len(Q)}", flush=True)
    m = metrics(rows)
    table.append(f"| {name} | {pct(m['stale1'])} | {pct(m['stale5'])} | {pct(m['wrong1'])} | {pct(m['recall5'])} | "
                 f"{np.percentile(lat, 50):.0f} | {np.percentile(lat, 95):.0f} |")
    details[name] = rows
    if rerank and use_filter:
        for lib in ("pandas", "numpy", "sklearn"):
            sub = [r for r in rows if r["lib"] == lib]
            mm = metrics(sub)
            perlib.append(f"| {lib} | {len(sub)} | {sum(r['trap'] for r in sub)} | {pct(mm['stale1'])} | "
                          f"{pct(mm['stale5'])} | {pct(mm['recall5'])} |")
    print("done:", name, flush=True)

n_trap = sum(q["trap"] for q in Q)
n_rec = sum(q["target"] is not None for q in Q)
md = f"""# Evaluation results

Benchmark: {len(Q)} auto-generated questions across pandas (1.5, 2.0, 2.2), NumPy (1.26, 2.1) and scikit-learn (1.3, 1.5),
{PER_LIB} per library. Trap questions (symbol absent in the user's version): {n_trap}. Recall questions: {n_rec}.
Library and version detection accuracy: {pct(detect_ok)}. Index: {len(chunks)} chunks.

| Config | Stale@1 (trap) | Stale@5 (trap) | Wrong-version@1 | Recall@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
""" + "\n".join(table) + """

Full system, per library:

| Library | Questions | Trap | Stale@1 | Stale@5 | Recall@5 |
|---|---|---|---|---|---|
""" + "\n".join(perlib) + """

Definitions:
- Stale@1 / Stale@5: share of trap questions where the top-1 / any of the top-5 results is a symbol that does not exist in the user's library version.
- Wrong-version@1: share of all questions whose top-1 chunk belongs to another version of the library.
- Recall@5: share of recall questions where the correct symbol, in the user's version, is in the top 5.
- All configs filter by library (detected from the question); "version filter" adds the detected version.
- Latency: search only, per query, MacBook M1 CPU, after 3 warm-up queries.
- Caveat: questions are built from docstring summaries, so they leak some wording of the target symbol.
- The 80 hand-labeled samples (below) were drawn from the earlier pandas-only benchmark, not this one.
"""
old = open("results.md").read()
i = old.find("\n## ")
open("results.md", "w").write(md + (old[i:] if i != -1 else ""))
json.dump(details, open("data/eval_details_multi.json", "w"), indent=2)
print(md)
