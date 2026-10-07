import json
import sys

import numpy as np

sys.path.insert(0, ".")
from docpilot.abstain import THRESHOLD, scored_search
from docpilot.search import Searcher

NAT = [
    ("how do I append a row in pandas 1.5", "1.5", "DataFrame.append"),
    ("how to group rows and sum in pandas 2.2", "2.2", "DataFrame.groupby"),
    ("how do I merge two dataframes in pandas 1.5", "1.5", "DataFrame.merge"),
    ("remove duplicate rows pandas 2.2", "2.2", "DataFrame.drop_duplicates"),
    ("fill missing values in pandas 1.5", "1.5", "DataFrame.fillna"),
    ("sort a dataframe by a column pandas 2.2", "2.2", "DataFrame.sort_values"),
    ("make a pivot table in pandas 1.5", "1.5", "DataFrame.pivot_table"),
    ("count unique values in a series pandas 2.2", "2.2", "Series.value_counts"),
    ("rename columns pandas 1.5", "1.5", "DataFrame.rename"),
    ("drop rows with NaN pandas 2.2", "2.2", "DataFrame.dropna"),
    ("apply a function to each column pandas 1.5", "1.5", "DataFrame.apply"),
    ("iterate over columns as key value pairs pandas 1.5", "1.5", "DataFrame.iteritems"),
    ("iterate over columns as key value pairs pandas 2.2", "2.2", "DataFrame.items"),
    ("read a csv file in pandas 2.2", "2.2", "pd.read_csv"),
    ("combine dataframes vertically pandas 1.5", "1.5", "pd.concat"),
    ("convert strings to datetime pandas 2.2", "2.2", "pd.to_datetime"),
    ("unpivot a dataframe wide to long pandas 1.5", "1.5", "pd.melt"),
    ("select rows by label pandas 2.2", "2.2", "DataFrame.loc"),
    ("get the first 5 rows pandas 1.5", "1.5", "DataFrame.head"),
    ("write dataframe to csv pandas 2.2", "2.2", "DataFrame.to_csv"),
    ("describe summary statistics pandas 1.5", "1.5", "DataFrame.describe"),
    ("change column dtype pandas 2.2", "2.2", "DataFrame.astype"),
    ("reset the index pandas 1.5", "1.5", "DataFrame.reset_index"),
    ("transpose a dataframe pandas 2.2", "2.2", "DataFrame.transpose"),
]
s = Searcher(use_reranker=True, device="cpu")
exists = {(c["symbol"], c["version"]) for c in s.chunks}
rows = []
for q, v, t in NAT:
    if (t, v) not in exists:
        print("SKIP (symbol not in index):", t, v, flush=True)
        continue
    sc, res = scored_search(s, q, v)
    hit = any(r["symbol"] == t and r["version"] == v for r in res)
    rows.append(dict(q=q, version=v, target=t, score=sc, hit=hit, top1=res[0]["symbol"]))
    print(f"{sc:.3f} hit={hit} top1={res[0]['symbol']:28} | {q}", flush=True)
json.dump(rows, open("data/natural_scores.json", "w"), indent=2)
sc = np.array([r["score"] for r in rows])
print(f"\nn={len(rows)} median={np.median(sc):.3f} min={sc.min():.3f} "
      f"answered_at_{THRESHOLD}={np.mean(sc >= THRESHOLD):.1%} hit@5={np.mean([r['hit'] for r in rows]):.1%}")
