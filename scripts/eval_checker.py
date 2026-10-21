import json, sys
sys.path.insert(0, ".")
from docpilot.checker import check_code

S = []
def add(version, code, exp):
    S.append({"id": len(S) + 1, "version": version,
              "code": code.strip("\n") + "\n", "expected": exp})

# ---- 20 true positives / version-gating ----
add("2.2", '''
import pandas as pd
df = pd.DataFrame({"a": [1]})
df = df.append({"a": 2}, ignore_index=True)
''', [[3, "DataFrame.append"]])
add("1.5", '''
import pandas as pd
df = pd.DataFrame({"a": [1]})
df = df.append({"a": 2}, ignore_index=True)
''', [])
add("2.0", '''
import pandas as pd
s = pd.Series([1, 2])
for i, v in s.iteritems():
    print(i, v)
''', [[3, "Series.iteritems"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
print(df.mad())
''', [[3, "DataFrame.mad"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
x = df.lookup(rows, cols)
''', [[3, "DataFrame.lookup"]])
add("2.0", '''
import pandas as pd
df = pd.read_csv("x.csv")
shifted = df.tshift(1)
''', [[3, "DataFrame.tshift"]])
add("2.2", '''
import pandas as pd
ser = pd.Series([1, 2, 3])
out = ser.slice_shift(1)
''', [[3, "Series.slice_shift"]])
add("2.2", '''
import pandas as pd
s = pd.Series([1, 2, 3])
if s.is_monotonic:
    print("sorted")
''', [[3, "Series.is_monotonic"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
df = df.applymap(lambda x: x * 2)
''', [[3, "DataFrame.applymap"]])
add("2.0", '''
import pandas as pd
df = pd.read_csv("x.csv")
df = df.applymap(lambda x: x * 2)
''', [])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
df = df.backfill()
''', [[3, "DataFrame.backfill"]])
add("2.2", '''
import pandas as pd
s = pd.Series([1, None])
s = s.pad()
''', [[3, "Series.pad"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
t = df.swapaxes(0, 1)
''', [[3, "DataFrame.swapaxes"]])
add("2.2", '''
import pandas as pd
s = pd.Series([True])
if s.bool():
    print("yes")
''', [[3, "Series.bool"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv", index_col=0, parse_dates=True)
head = df.first("3D")
''', [[3, "DataFrame.first"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv", index_col=0, parse_dates=True)
tail = df.last("1W")
''', [[3, "DataFrame.last"]])
add("2.2", '''
import pandas as pd
df = pd.read_gbq("SELECT 1", project_id="p")
''', [[2, "pd.read_gbq"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
df.to_gbq("ds.tbl", project_id="p")
''', [[3, "DataFrame.to_gbq"]])
add("2.2", '''
import pandas as pd
s = pd.Series([1, 2])
a = s.ravel()
''', [[3, "Series.ravel"]])
add("2.2", '''
import pandas as pd
s = pd.Series([1, 2])
v = s.view("int64")
''', [[3, "Series.view"]])

# ---- 9 clean snippets (nothing should be flagged) ----
add("2.2", '''
import pandas as pd
rows = []
for i in range(3):
    rows.append({"a": i})
df = pd.DataFrame(rows)
''', [])
add("2.2", '''
import numpy as np
a = np.array([[1, 2], [3, 4]])
b = a.ravel()
c = a.view(np.int8)
d = a.swapaxes(0, 1)
''', [])
add("2.2", '''
import pandas as pd
d = {"a": 1}
for k, v in d.items():
    print(k, v)
df = pd.DataFrame([d])
for k, v in df.items():
    print(k)
''', [])
add("2.2", '''
import pandas as pd
df = pd.DataFrame({"a": [1]})
df = pd.concat([df, pd.DataFrame({"a": [2]})], ignore_index=True)
df = df.map(str)
df = df.bfill()
''', [])
add("2.2", '''
class Queue:
    def first(self):
        return 1
q = Queue()
print(q.first())
''', [])
add("2.2", '''
d = {"a": 1}
for k, v in d.iteritems():
    print(k, v)
''', [])  # plain Python 2 dict, not pandas
add("1.5", '''
import pandas as pd
df = pd.read_csv("x.csv")
for k, v in df.iteritems():
    print(k)
''', [])
add("2.2", '''
import pandas as pd
# df.append is removed, use concat
msg = "do not call df.append(x)"
df = pd.DataFrame()
''', [])
add("2.2", '''
df.append(
''', [])  # syntax error: no findings expected

# ---- 11 harder snippets ----
add("2.2", '''
import pandas as pd
class Loader:
    def __init__(self):
        self.df = pd.read_csv("x.csv")
    def add(self, row):
        self.df = self.df.append(row, ignore_index=True)
''', [[6, "DataFrame.append"]])
add("2.2", '''
from pandas import read_gbq
df = read_gbq("SELECT 1")
''', [[2, "pd.read_gbq"]])
add("2.2", '''
import pandas as pd
data = pd.read_csv("x.csv")
data = data.append({"a": 1}, ignore_index=True)
''', [[3, "DataFrame.append"]])
add("2.2", '''
import pandas as pd
def load():
    return pd.read_csv("x.csv")
frame = load()
frame = frame.append({"a": 1}, ignore_index=True)
''', [[5, "DataFrame.append"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
for name, g in df.groupby("k"):
    g = g.append({"a": 1})
''', [[4, "DataFrame.append"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
df = df.append({"a": 1}, ignore_index=True)
for k, v in df.iteritems():
    print(k)
print(df.applymap(str))
print(df["a"].is_monotonic)
''', [[3, "DataFrame.append"], [4, "DataFrame.iteritems"],
      [6, "DataFrame.applymap"], [7, "Series.is_monotonic"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("a.csv").append(pd.read_csv("b.csv"))
''', [[2, "DataFrame.append"]])
add("2.2", '''
import pandas as pd
df = pd.read_csv("x.csv")
for i, v in df["a"].iteritems():
    print(i, v)
''', [[3, "Series.iteritems"]])
add("2.2", '''
import pandas as pd
items = ["a", "b"]
first = items[0]
df = pd.DataFrame({"a": items})
print(first, df.shape)
''', [])
add("2.0", '''
import pandas as pd
s = pd.Series([1, 2])
s2 = s.append(pd.Series([3]))
print(s2.mad())
''', [[3, "Series.append"], [4, "Series.mad"]])
add("2.0", '''
import pandas as pd
df = pd.read_gbq("SELECT 1")
''', [])

assert len(S) == 40, len(S)
json.dump(S, open("data/checker_testset.json", "w"), indent=1)

def name(sym):
    return sym.split(".")[-1]

tot = {"strict": [0, 0, 0], "name": [0, 0, 0]}
exact_snip = 0
rows = []
for s in S:
    out = check_code(s["code"], s["version"])
    pred = {(f["line"], f["symbol"]) for f in out["findings"]}
    exp = {(l, y) for l, y in s["expected"]}
    for mode, fn in (("strict", lambda t: t), ("name", lambda t: (t[0], name(t[1])))):
        p = {fn(t) for t in pred}; e = {fn(t) for t in exp}
        tot[mode][0] += len(p & e); tot[mode][1] += len(p - e); tot[mode][2] += len(e - p)
    if pred == exp:
        exact_snip += 1
    else:
        rows.append((s["id"], s["version"], sorted(exp - pred), sorted(pred - exp)))

res = {"snippets": 40, "expected_findings": sum(len(s["expected"]) for s in S), "exact_match_snippets": exact_snip}
for mode, (tp, fp, fn_) in tot.items():
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn_) if tp + fn_ else 0.0
    res[mode] = {"tp": tp, "fp": fp, "fn": fn_, "precision": round(pr, 3), "recall": round(rc, 3)}
json.dump(res, open("data/checker_eval.json", "w"), indent=1)
print(json.dumps(res, indent=1))
print("\nMISMATCHES (id, version, MISSED, FALSE ALARMS):")
for r in rows:
    print(" ", r)
