import json, os, random, re, sys, time
sys.path.insert(0, ".")
from docpilot.answer import generate_answer, CITE
from docpilot.observe import ObservedSearcher

CACHE = "data/answers_cache.json"
IGNORE = {"DataFrame", "Series", "array", "Index"}
chunks = json.load(open("data/chunks.json"))
by = {(c["library"], c["symbol"], c["version"]) for c in chunks}
known = {}
for c in chunks:
    known.setdefault(c["library"], set()).add(c["symbol"].split(".")[-1])

bench = json.load(open("data/benchmark_multi.json"))
rng = random.Random(42)
sample = []
for lib in ["pandas", "numpy", "sklearn"]:
    qs = [b for b in bench if b["lib"] == lib]
    tr = [b for b in qs if b["trap"]]; nt = [b for b in qs if not b["trap"]]
    t = rng.sample(tr, min(6, len(tr)))
    sample += t + rng.sample(nt, 20 - len(t))

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
searcher = ObservedSearcher(use_reranker=False, device="cpu")

def get_answer(i, b, top):
    k = str(i)
    if k in cache:
        return cache[k]
    for _ in range(6):
        r = generate_answer(b["q"], top, b["lib"], b["user_version"])
        if r["used_llm"]:
            cache[k] = r
            json.dump(cache, open(CACHE, "w"))
            time.sleep(3)
            return r
        if r["error"] and ("RateLimit" in r["error"] or "429" in r["error"]):
            print("  rate limited, waiting 25s"); time.sleep(25); continue
        break
    return r

def mentions(ans):
    text = CITE.sub(" ", ans)
    out = set()
    for blk in re.findall(r"```.*?```", text, re.S):
        out |= {m for m in re.findall(r"\b[A-Za-z_]\w*\.([A-Za-z_]\w*)\s*\(", blk)}
    for t in re.findall(r"`([^`\n]+)`|\*\*([^*\n]+)\*\*", text):
        tok = (t[0] or t[1]).strip().rstrip("()").split("(")[0]
        if re.fullmatch(r"[A-Za-z_][\w.]*", tok):
            out.add(tok.split(".")[-1])
    return out

rows, n_fb = [], 0
for i, b in enumerate(sample):
    lib, ver = b["lib"], b["user_version"]
    top = [dict(r, version=ver, library=lib) for r in searcher.search(b["q"], version=ver, k=5, rerank=False, library=lib)[:3]]
    r = get_answer(i, b, top)
    print(f"[{i+1}/{len(sample)}] {lib} {ver} llm={r['used_llm']}")
    if not r["used_llm"]:
        n_fb += 1; continue
    ans = r["answer"]
    if ans.strip().startswith("Cannot confirm"):
        rows.append({"q": b["q"], "trap": b["trap"], "lib": lib, "abstain": True, "faithful": None, "violations": [], "n_cites": 0})
        continue
    names = {t["symbol"] for t in top}
    lasts = {t["symbol"].split(".")[-1]: t["symbol"] for t in top}
    viol = []
    cites = CITE.findall(ans)
    for s, _, v in cites:
        if s not in names: viol.append(f"cited symbol not retrieved: {s}")
        elif v != ver: viol.append(f"cited version {v} != chosen {ver}: {s}")
        elif (lib, s, ver) not in by: viol.append(f"not valid in {ver}: {s}")
    for m in mentions(ans):
        if m in IGNORE or m not in known[lib]: continue
        if m not in lasts: viol.append(f"named but not retrieved: {m}")
        elif (lib, lasts[m], ver) not in by: viol.append(f"not valid in {ver}: {m}")
    rows.append({"q": b["q"], "trap": b["trap"], "lib": lib, "abstain": False, "faithful": not viol,
                 "violations": viol, "n_cites": len(cites), "answer": ans})

ans_rows = [r for r in rows if not r["abstain"]]
fa = sum(r["faithful"] for r in ans_rows)
res = {"sampled": len(sample), "llm_answers": len(rows), "fallback_not_counted": n_fb,
       "abstained": sum(r["abstain"] for r in rows), "answered": len(ans_rows),
       "faithful": fa, "faithfulness_rate": round(fa / len(ans_rows), 3) if ans_rows else None,
       "with_citation_rate": round(sum(r["n_cites"] > 0 for r in ans_rows) / len(ans_rows), 3) if ans_rows else None,
       "trap_answered": sum(r["trap"] for r in ans_rows),
       "trap_faithful": sum(r["trap"] and r["faithful"] for r in ans_rows)}
json.dump(res, open("data/faithfulness.json", "w"), indent=1)
json.dump(rows, open("data/faithfulness_details.json", "w"), indent=1)
print(json.dumps(res, indent=1))
print("\nUNFAITHFUL ANSWERS:")
for r in ans_rows:
    if not r["faithful"]:
        print("-", r["lib"], "|", r["q"][:80]); [print("    ", v) for v in r["violations"]]
