import json, collections
from docpilot.sandbox import run_snippet

d = json.load(open("data/exec_results.json"))
blocks = json.load(open("data/exec_blocks.json"))
PREFIX = ("import pandas as pd\n"
          "s = pd.Series([1, 2, 3], index=pd.date_range('2024-01-01', periods=3, freq='D'))\n"
          "df = s.to_frame('a')\n")

def status_of(r):
    if isinstance(r, dict):
        return r.get("status") or r.get("got") or r.get("result")
    if isinstance(r, (tuple, list)):
        return r[0]
    return getattr(r, "status", None)

for r in d["results"]:
    code = next((b["code"] for b in blocks
                 if b["idx"] == r["idx"] and b["symbol"] == r["symbol"]), "")
    if r["category"] != "real_error":
        continue
    if "shift" in r["symbol"]:
        s2 = status_of(run_snippet(PREFIX + code, r["version"]))
        r["retest_with_date_index"] = s2
        r["category"] = "needs_date_index_ok" if s2 in ("ok", "warning") else "real_error"
    elif any(ord(ch) > 127 for ch in code):
        r["category"] = "real_error_nonascii_char"

c = collections.Counter(r["category"] for r in d["results"])
d["categories"] = dict(c)
json.dump(d, open("data/exec_results.json", "w"), indent=1)

n = len(d["results"])
ran = c["ran_ok"] + c["ran_warning"]
complete = n - c["incomplete_snippet"]
ran_adj = ran + c["needs_date_index_ok"]
print(dict(c))
print("raw: ran without error %d / %d = %.1f%%" % (ran, n, 100 * ran / n))
print("self-contained snippets: %d" % complete)
print("self-contained, ran after test-data fix: %d / %d = %.1f%%" % (ran_adj, complete, 100 * ran_adj / complete))
for r in d["results"]:
    if "retest_with_date_index" in r:
        print("retest", r["version"], r["symbol"], "->", r["retest_with_date_index"])
