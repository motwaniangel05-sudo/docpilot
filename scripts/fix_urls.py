import csv

path = "data/labels.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
fields = list(rows[0].keys())
for r in rows:
    r["url"] = r["url"].replace("pandas.pd.", "pandas.")
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print("RECHECK these rows (open the URL, set y if page loads, n if 404):\n")
for r in rows:
    if r["candidate"].startswith("pd."):
        print(f"{r['id']:4} v{r['user_version']} benchmark={r['benchmark_says']} human={r['human']:1} {r['url']}")
