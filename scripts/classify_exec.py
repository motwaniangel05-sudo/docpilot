import json, collections

d = json.load(open("data/exec_results.json"))
blocks = json.load(open("data/exec_blocks.json"))

for r in d["results"]:
    if r["status"] == "error" and r["message"].startswith("NameError"):
        r["category"] = "incomplete_snippet"
    elif r["status"] == "error":
        r["category"] = "real_error"
    else:
        r["category"] = "ran_" + r["status"]

c = collections.Counter(r["category"] for r in d["results"])
d["categories"] = dict(c)
json.dump(d, open("data/exec_results.json", "w"), indent=1)
print(dict(c))

for r in d["results"]:
    if r["category"] == "real_error":
        print("\n=== pandas", r["version"], r["symbol"], "|", r["message"])
        for b in blocks:
            if b["idx"] == r["idx"] and b["symbol"] == r["symbol"]:
                print(b["code"])
