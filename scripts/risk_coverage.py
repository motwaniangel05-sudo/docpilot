import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

d = json.load(open("data/abstain_scores.json"))
answerable = np.array([x["group"] == "recall" for x in d])
hit = np.array([bool(x["hit"]) for x in d])
wrong = ~(answerable & hit)  # unanswerable, or answerable but missed


def curve(key):
    c = np.array([x[key] for x in d])
    pts = []
    for t in sorted(set(c)) + [c.max() + 1e-6]:
        ans = c >= t
        if ans.sum() == 0:
            continue
        pts.append((t, ans.mean(), wrong[ans].mean()))
    return c, pts


fig, ax = plt.subplots(figsize=(6.5, 4.5))
for key, label in (("rr_top", "reranker score"), ("dense_top", "dense cosine")):
    _, pts = curve(key)
    ax.plot([p[1] for p in pts], [p[2] for p in pts], label=label)

rr, pts = curve("rr_top")
oos = np.array([x["rr_top"] for x in d if x["group"] == "oos"])
T = round(float(sorted(oos)[-2]) + 0.001, 3)
ans = rr >= T
cov, risk = ans.mean(), wrong[ans].mean()
ax.scatter([cov], [risk], color="red", zorder=5, label=f"chosen threshold {T}")
ax.set_xlabel("Coverage (share of questions answered)")
ax.set_ylabel("Risk (share of answers that are wrong or unanswerable)")
ax.set_title("Risk-coverage curve (110 questions)")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("data/risk_coverage.png", dpi=150)

g = lambda name: np.array([x["group"] == name for x in d])
stats = {
    "threshold": T,
    "coverage": round(float(cov), 4),
    "risk": round(float(risk), 4),
    "recall_answered": round(float(ans[g("recall")].mean()), 4),
    "oos_abstained": round(float((~ans[g("oos")]).mean()), 4),
    "trap_abstained": round(float((~ans[g("trap")]).mean()), 4),
    "risk_no_abstention": round(float(wrong.mean()), 4),
}
json.dump(stats, open("data/abstain_config.json", "w"), indent=2)
print(json.dumps(stats, indent=2))
