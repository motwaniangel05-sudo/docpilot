import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

d = json.load(open("data/abstain_scores.json"))
for r in json.load(open("data/natural_scores.json")):
    d.append(dict(q=r["q"], group="natural", rr_top=r["score"], hit=r["hit"]))

grp = np.array([x["group"] for x in d])
rr = np.array([x["rr_top"] for x in d])
hit = np.array([bool(x["hit"]) for x in d])
answerable = np.isin(grp, ["recall", "natural"])
good = answerable & hit
oos = grp == "oos"
nat_good = (grp == "natural") & hit
wrong = ~good

vals = np.array(sorted(set(rr)))
best = None
for i, t in enumerate(vals):
    j = (rr[nat_good] >= t).mean() - (rr[oos] >= t).mean()
    if best is None or j > best[0] + 1e-12:
        prev = vals[i - 1] if i > 0 else 0.0
        best = (j, round(float((t + prev) / 2), 3))
J, T = best
ans = rr >= T

xs, ys = [], []
for t in list(vals) + [rr.max() + 1e-6]:
    a = rr >= t
    if a.sum():
        xs.append(a.mean())
        ys.append(wrong[a].mean())
fig, ax = plt.subplots(figsize=(6.5, 4.5))
ax.plot(xs, ys, label="reranker score")
ax.scatter([ans.mean()], [wrong[ans].mean()], color="red", zorder=5, label=f"chosen threshold {T}")
ax.set_xlabel("Coverage (share of questions answered)")
ax.set_ylabel("Risk (share of answers that are wrong or unanswerable)")
ax.set_title(f"Risk-coverage curve ({len(d)} questions)")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("data/risk_coverage.png", dpi=150)

stats = {
    "threshold": T,
    "n_questions": len(d),
    "coverage": round(float(ans.mean()), 4),
    "risk": round(float(wrong[ans].mean()), 4),
    "risk_no_abstention": round(float(wrong.mean()), 4),
    "recall_answered": round(float(ans[grp == "recall"].mean()), 4),
    "natural_answered": round(float(ans[grp == "natural"].mean()), 4),
    "natural_good_kept": round(float(ans[nat_good].mean()), 4),
    "oos_abstained": round(float((~ans[oos]).mean()), 4),
    "trap_abstained": round(float((~ans[grp == "trap"]).mean()), 4),
}
json.dump(stats, open("data/abstain_config.json", "w"), indent=2)
print(json.dumps(stats, indent=2))
print("oos scores above threshold:", sorted(round(float(x), 3) for x in rr[oos & ans]))
print("natural hits abstained:", int((nat_good & ~ans).sum()), "of", int(nat_good.sum()))
