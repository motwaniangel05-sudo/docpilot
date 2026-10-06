import csv

rows = list(csv.DictReader(open("data/labels.csv", encoding="utf-8-sig")))
rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in rows]

unlabeled = [r["id"] for r in rows if r["human"].lower() not in ("y", "n")]
if unlabeled:
    print("UNLABELED or invalid human value (must be y or n):", unlabeled)
    raise SystemExit(1)


def rate(rs):
    ok = sum(r["human"].lower() == r["benchmark_says"] for r in rs)
    return ok, len(rs), (100 * ok / len(rs) if rs else 0.0)


q = [r for r in rows if r["task"] == "question"]
v = [r for r in rows if r["task"] == "validity"]
out = []
for name, rs in (("Question labels", q), ("Version-validity labels", v), ("Overall", rows)):
    ok, n, p = rate(rs)
    out.append(f"{name}: {ok}/{n} agree = {p:.1f}%")

errs = [r for r in rows if r["human"].lower() != r["benchmark_says"]]
out.append(f"\nDisagreements: {len(errs)}")
for r in errs:
    out.append(f"- {r['id']} | v{r['user_version']} | {r['candidate']} | benchmark={r['benchmark_says']} human={r['human']} | note: {r['note']}\n  {r['url']}")

text = "\n".join(out)
print(text)
open("data/label_report.txt", "w").write(text)
