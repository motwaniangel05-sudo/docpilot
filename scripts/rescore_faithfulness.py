import json, re, sys
sys.path.insert(0, ".")
from docpilot.answer import CITE
from docpilot.observe import ObservedSearcher

# generic method/argument names: not treated as API claims (reviewable judgment list)
GENERIC = {"DataFrame", "Series", "array", "Index", "size", "seed", "sum", "mean", "std", "gt",
           "join", "factorize", "axis", "x", "y", "dx", "a", "b", "df", "n"}
last = lambda s: s.split(".")[-1]

chunks = json.load(open("data/chunks.json"))
valid = {(c["library"], last(c["symbol"]), c["version"]) for c in chunks}
exists_lib = {}
for c in chunks:
    exists_lib.setdefault(c["library"], set()).add(last(c["symbol"]))

rows = json.load(open("data/faithfulness_details.json"))
bench = json.load(open("data/benchmark_multi.json"))
by_q = {b["q"]: b for b in bench}
searcher = ObservedSearcher(use_reranker=False, device="cpu")

def mentions(ans):
    text = CITE.sub(" ", ans)
    out = set()
    for blk in re.findall(r"```.*?```", text, re.S):
        out |= set(re.findall(r"\b[A-Za-z_]\w*\.([A-Za-z_]\w*)\s*\(", blk))
    for t in re.findall(r"`([^`\n]+)`|\*\*([^*\n]+)\*\*", text):
        tok = (t[0] or t[1]).strip().rstrip("()").split("(")[0]
        if re.fullmatch(r"[A-Za-z_][\w.]*", tok):
            out.add(last(tok))
    return out

res_rows = []
for r in rows:
    if r["abstain"]:
        continue
    b = by_q[r["q"]]; lib, ver = b["lib"], b["user_version"]
    top = searcher.search(b["q"], version=ver, k=5, rerank=False, library=lib)[:3]
    top_last = {last(t["symbol"]) for t in top}
    viol, fmt = [], []
    for s, _, v in CITE.findall(r["answer"]):
        if s.isdigit():
            fmt.append(f"chunk-number citation: {s}")
        elif last(s) not in top_last:
            viol.append(f"cited symbol not retrieved: {s}")
        elif v != ver:
            viol.append(f"cited version {v} != {ver}: {s}")
        elif (lib, last(s), ver) not in valid:
            viol.append(f"not valid in {ver}: {s}")
    for m in mentions(r["answer"]):
        if m in GENERIC or m not in exists_lib[lib]:
            continue
        if m not in top_last:
            viol.append(f"named but not retrieved: {m}")
    res_rows.append({"q": r["q"], "lib": lib, "trap": r["trap"], "viol": viol, "fmt": fmt,
                     "has_cite": bool(CITE.findall(r["answer"]))})

n = len(res_rows)
faith = [x for x in res_rows if not x["viol"]]
faith_strict_fmt = [x for x in res_rows if not x["viol"] and not x["fmt"]]
out = {"answered": n,
       "faithful_normalized": len(faith), "faithfulness_rate_normalized": round(len(faith) / n, 3),
       "faithful_and_no_format_error": len(faith_strict_fmt),
       "rate_incl_format_errors": round(len(faith_strict_fmt) / n, 3),
       "unnormalized_original": {"faithful": 30, "answered": 54, "rate": 0.556},
       "trap_answered": sum(x["trap"] for x in res_rows),
       "trap_faithful": sum(x["trap"] and not x["viol"] for x in res_rows),
       "by_lib": {l: [sum(1 for x in res_rows if x["lib"] == l and not x["viol"]),
                      sum(1 for x in res_rows if x["lib"] == l)] for l in ["pandas", "numpy", "sklearn"]},
       "generic_names_ignored": sorted(GENERIC)}
json.dump(out, open("data/faithfulness_normalized.json", "w"), indent=1)
print(json.dumps(out, indent=1))
print("\nREMAINING VIOLATIONS:")
for x in res_rows:
    if x["viol"] or x["fmt"]:
        print("-", x["lib"], "|", x["q"][:70]); [print("    ", v) for v in x["viol"] + x["fmt"]]
