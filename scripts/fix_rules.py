import json

rules = json.load(open("data/api_rules.json"))

DROP = {"DataFrame.iloc", "Series.iloc"}  # partial deprecation, not the whole symbol

FIX = {  # method name -> replacement text (applied to DataFrame.* and Series.*)
 "applymap": "DataFrame.map",
 "backfill": "bfill",
 "pad": "ffill",
 "first": "df.loc[:start + offset] (slice by date offset)",
 "last": "df.loc[end - offset:] (slice by date offset)",
 "bool": "df.iloc[0, 0] or Series.item()",
 "swapaxes": "transpose",
}

out = []
for r in rules:
    if r["symbol"] in DROP:
        continue
    name = r["symbol"].split(".", 1)[1]
    if r["status"] == "deprecated" and name in FIX:
        r["replacement"] = FIX[name]
        r["source"] = "docstring-directive + manual replacement"
    out.append(r)

json.dump(out, open("data/api_rules.json", "w"), indent=1)
print("rules:", len(out))
for r in out:
    print(f'{r["status"]:10} {r["symbol"]:26} since {r["since"]:6} -> {r["replacement"]}')
