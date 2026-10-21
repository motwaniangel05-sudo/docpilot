import json, re
from collections import Counter

VERS = ["1.5", "2.0", "2.2"]
vkey = lambda v: tuple(int(x) for x in v.split("."))
docs = {v: {s["symbol"]: s for s in json.load(open(f"data/symbols_{v}.json"))} for v in VERS}

SECTION = re.compile(r"\n(Parameters|Returns|Yields|Raises|See Also|Notes|Examples|Attributes)\n-{3,}")
DEPR = re.compile(r"\.\. deprecated:: ([\d.]+)[ \t]*\n")

def directives(doc):
    """yield (version, is_symbol_level, hint_text)"""
    m = SECTION.search(doc)
    first_section = m.start() if m else len(doc)
    for d in DEPR.finditer(doc):
        lines, rest = [], doc[d.end():].split("\n")
        for ln in rest:
            if ln.strip() == "" and lines:
                break
            if ln.strip() == "":
                continue
            if not ln.startswith((" ", "\t")):
                break
            lines.append(ln.strip())
        yield d.group(1), d.start() < first_section, " ".join(lines)[:300]

def replacement(hint):
    m = re.search(r"(?:use|using|see|replaced by)\s+`{1,2}([^`]+)`{1,2}", hint, re.I)
    if m:
        return m.group(1)
    names = re.findall(r"`{1,2}([\w.\[\]()]+)`{1,2}", hint)
    return names[0] if names else None

REMOVED_FIX = {
 "DataFrame.append": "pd.concat([df, other])",
 "Series.append": "pd.concat([s, other])",
 "DataFrame.iteritems": "DataFrame.items",
 "Series.iteritems": "Series.items",
 "DataFrame.lookup": "DataFrame.melt + indexing, or df.to_numpy()[row_idx, col_idx]",
 "DataFrame.mad": "(df - df.mean()).abs().mean()",
 "Series.mad": "(s - s.mean()).abs().mean()",
 "DataFrame.slice_shift": "DataFrame.shift",
 "Series.slice_shift": "Series.shift",
 "DataFrame.tshift": "DataFrame.shift",
 "Series.tshift": "Series.shift",
 "Series.is_monotonic": "Series.is_monotonic_increasing",
}

rules = {}
# 1) removed: present in 1.5, absent in a later version
for sym in docs["1.5"]:
    for v in VERS[1:]:
        if sym not in docs[v]:
            rules[sym] = {"symbol": sym, "status": "removed", "since": v,
                          "replacement": REMOVED_FIX.get(sym), "source": "symbol-diff + whatsnew-manual"}
            break

# 2) deprecated (symbol-level only), earliest version seen across docstrings
param_level = Counter()
for sym in set().union(*[set(d) for d in docs.values()]):
    if sym in rules:
        continue
    found = []
    for v in VERS:
        if sym in docs[v]:
            for dv, sym_level, hint in directives(docs[v][sym]["docstring"]):
                if sym_level:
                    found.append((dv, hint))
                else:
                    param_level[sym] += 1
    if found:
        dv, hint = min(found, key=lambda x: vkey(x[0]))
        rules[sym] = {"symbol": sym, "status": "deprecated", "since": dv,
                      "replacement": replacement(hint), "hint": hint, "source": "docstring-directive"}

out = sorted(rules.values(), key=lambda r: r["symbol"])
json.dump(out, open("data/api_rules.json", "w"), indent=1)
c = Counter(r["status"] for r in out)
print("rules:", len(out), dict(c))
print("symbols with only param-level deprecations (ignored):", len(param_level))
print("deprecated with no replacement parsed:", sum(1 for r in out if r["status"] == "deprecated" and not r["replacement"]))
print("\nSAMPLE deprecated:")
for r in [r for r in out if r["status"] == "deprecated"][:15]:
    print(f'  {r["symbol"]:28} since {r["since"]:6} -> {r["replacement"]} | {r["hint"][:70]}')
print("\nSAMPLE removed:")
for r in [r for r in out if r["status"] == "removed"][:4]:
    print("  ", r)
