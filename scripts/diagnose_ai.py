import json, pickle, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from docpilot.checker import load_rules

def vk(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v)))

def flatten(x, out):
    if isinstance(x, dict):
        if "symbol" in x and "status" in x:
            out.append(x)
        else:
            for v in x.values():
                flatten(v, out)
    elif isinstance(x, (list, tuple)):
        for v in x:
            flatten(v, out)
    return out

rules = flatten(load_rules(), [])
chunks = pickle.load(open(ROOT / "index" / "bm25.pkl", "rb"))["chunks"]
res = json.load(open(ROOT / "data" / "ai_results.json"))["results"]

counts = {"found": 0, "missed_but_in_index": 0, "not_in_index": 0}
out = []
for r in res:
    ps = r["parts"]
    in_ver = any(any(p in c["symbol"].lower() for p in ps) and r["version"] in c["applies"] for c in chunks)
    in_any = any(any(p in c["symbol"].lower() for p in ps) for c in chunks)
    found = r["recall5_symbol_fast"] or r["recall5_symbol_rerank"]
    if found:
        kind = "found"
    elif in_ver:
        kind = "missed_but_in_index"
    else:
        kind = "not_in_index"
    counts[kind] += 1
    matched = [ru for ru in rules if any(p == str(ru["symbol"]).lower().replace("pd.", "") or p.split(".")[-1] == str(ru["symbol"]).lower().split(".")[-1] for p in ps)]
    r2 = dict(r, kind=kind, in_index_at_version=in_ver, in_index_any_version=in_any,
              flagged_at_2_2=any(vk(m["since"]) <= (2, 2) for m in matched))
    out.append(r2)
    if kind != "found":
        print(r["id"], r["version"], kind, "| any_version:", in_any)
        print("   Q:", r["question"][:90])
        print("   expected:", r["expected_api"][:60], "| parts:", ps)
        print("   top5:", r["top5_fast"])
print()
print(counts)
rr = [x for x in out if x["has_rule"]]
print("questions with a rule:", len(rr), "| flagged at 2.2:", sum(x["flagged_at_2_2"] for x in rr))
json.dump(out, open(ROOT / "data" / "ai_diagnosis.json", "w"), indent=1)
