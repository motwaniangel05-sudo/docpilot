import json
rules = json.load(open("data/api_rules.json"))
for r in rules:
    if r["symbol"] == "Series.view":
        r["replacement"] = "Series.astype(dtype) or Series.to_numpy().view(dtype)"
    if r["symbol"] in ("Series.bool", "DataFrame.bool"):
        r["replacement"] = "Series.item() or df.iloc[0, 0]"
    if r["symbol"] == "Series.ravel":
        r["replacement"] = "Series.to_numpy()"
json.dump(rules, open("data/api_rules.json", "w"), indent=1)
print("patched", len(rules))
