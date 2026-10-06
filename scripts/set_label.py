import csv
import sys

path = "data/labels.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
fields = list(rows[0].keys())
updates = dict(a.split("=") for a in sys.argv[1:])
for r in rows:
    if r["id"] in updates:
        r["human"] = updates[r["id"]]
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print("updated:", ", ".join(f"{k}={v}" for k, v in updates.items()))
