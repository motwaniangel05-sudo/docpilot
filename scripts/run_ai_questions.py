import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docpilot.delta import DeltaSearcher
from docpilot.checker import load_rules


def vk(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v)))


def flatten(rules):
    out = []
    def walk(x):
        if isinstance(x, dict):
            if "symbol" in x and "status" in x:
                out.append(x)
            else:
                for v in x.values():
                    walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
    walk(rules)
    return out


rows = [r for r in csv.DictReader(open(ROOT / "data" / "ai_questions.csv")) if r["usable"] == "yes"]
rules = flatten(load_rules())
print("usable questions:", len(rows))
print("rules flattened:", len(rules))

s = DeltaSearcher(use_reranker=True)


def parts(expected):
    out = []
    for p in re.split(r"/|,| or ", expected):
        p = re.sub(r"\(.*", "", p).strip().lower()
        p = p.replace("pandas.", "").replace(")", "").strip()
        if len(p) >= 3 and "..." not in p:
            out.append(p)
    return out


def hit(top, ps):
    sym = any(p in str(c.get("symbol", "")).lower() for p in ps for c in top)
    txt = any(p in str(c.get("text", "")).lower() for p in ps for c in top)
    return sym, txt


results = []
for r in rows:
    q, ver, exp = r["question"], r["pandas_version"], r["expected_api"]
    ps = parts(exp)
    top_fast = s.search(q, version=ver, k=5, rerank=False)
    top_rr = s.search(q, version=ver, k=5, rerank=True)
    f_sym, f_txt = hit(top_fast, ps)
    r_sym, r_txt = hit(top_rr, ps)
    matched = []
    for ru in rules:
        sym = str(ru["symbol"]).lower().replace("pd.", "")
        last = sym.split(".")[-1]
        if any(p == sym or p.split(".")[-1] == last for p in ps):
            matched.append(ru)
    has_rule = bool(matched)
    flagged = any(vk(ru["since"]) <= vk(ver) for ru in matched)
    results.append({
        "id": r["id"], "question": q, "version": ver, "expected_api": exp,
        "parts": ps,
        "top5_fast": [c.get("symbol") for c in top_fast],
        "top5_rerank": [c.get("symbol") for c in top_rr],
        "recall5_symbol_fast": f_sym, "recall5_text_fast": f_txt,
        "recall5_symbol_rerank": r_sym, "recall5_text_rerank": r_txt,
        "has_rule": has_rule, "flagged_for_version": flagged,
    })
    print(r["id"], ver,
          "F-sym" if f_sym else "F----", "R-sym" if r_sym else "R----",
          "txt" if (f_txt or r_txt) else "---",
          "rule" if has_rule else "----", "FLAG" if flagged else "----")

n = len(results)
def pct(k, sub=None):
    sub = sub if sub is not None else results
    return round(100 * sum(1 for x in sub if x[k]) / len(sub), 1) if sub else None

with_rule = [x for x in results if x["has_rule"]]
summary = {
    "n": n,
    "recall5_symbol_fast_pct": pct("recall5_symbol_fast"),
    "recall5_symbol_rerank_pct": pct("recall5_symbol_rerank"),
    "recall5_text_fast_pct": pct("recall5_text_fast"),
    "recall5_text_rerank_pct": pct("recall5_text_rerank"),
    "questions_with_a_rule": len(with_rule),
    "flagged_among_with_rule_pct": pct("flagged_for_version", with_rule),
}
for v in ("1.5", "2.2"):
    sub = [x for x in results if x["version"] == v]
    summary["recall5_symbol_fast_" + v] = pct("recall5_symbol_fast", sub)
json.dump({"summary": summary, "results": results},
          open(ROOT / "data" / "ai_results.json", "w"), indent=1)
print()
print(json.dumps(summary, indent=1))
