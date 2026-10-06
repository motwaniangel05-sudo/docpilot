import sys
sys.path.insert(0, ".")
from docpilot.search import Searcher

s = Searcher()
tests = [
    ("how do I add a row to a dataframe with append", "2.2"),
    ("how do I add a row to a dataframe with append", "1.5"),
    ("combine two dataframes by rows", "2.2"),
    ("iterate over columns as key value pairs", "2.2"),
    ("iterate over columns as key value pairs", None),
]
for q, v in tests:
    print(f"\nQ: {q} | version={v}")
    for r in s.search(q, version=v):
        print("  ", r["symbol"], "v" + r["version"])
