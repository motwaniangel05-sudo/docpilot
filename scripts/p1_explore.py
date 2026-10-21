import json, re, subprocess

def load(v):
    return {s["symbol"]: s for s in json.load(open(f"data/symbols_{v}.json"))}

a, b, c = load("1.5"), load("2.0"), load("2.2")
print("counts 1.5/2.0/2.2:", len(a), len(b), len(c))

for name, x, y in [("1.5->2.0", a, b), ("2.0->2.2", b, c), ("1.5->2.2", a, c)]:
    gone = sorted(set(x) - set(y))
    print(f"\nREMOVED {name}: {len(gone)}")
    print(gone[:40])

print("\nKNOWN CHECKS (in 1.5? 2.0? 2.2?)")
for s in ["DataFrame.append", "Series.append", "DataFrame.iteritems", "Series.iteritems",
          "DataFrame.lookup", "DataFrame.mad", "Series.mad", "DataFrame.swapaxes",
          "Index.is_integer", "DataFrame.applymap", "DataFrame.bool", "Series.view"]:
    print(f"{s:25}", s in a, s in b, s in c)

print("\nDEPRECATION TEXT in docstrings")
for v, d in [("1.5", a), ("2.0", b), ("2.2", c)]:
    hits = [k for k, s in d.items() if re.search(r"deprecat", s["docstring"], re.I)]
    print(v, "docstrings mentioning deprecat:", len(hits))
n = 0
for k, s in c.items():
    m = re.search(r"[^\n]*deprecat[^\n]*", s["docstring"], re.I)
    if m and n < 12:
        print(" ", k, "|", m.group(0).strip()[:110])
        n += 1

print("\nGIT")
print(subprocess.run("git status -s | head -10; git remote -v; git log --oneline | head -3",
                     shell=True, capture_output=True, text=True).stdout)
