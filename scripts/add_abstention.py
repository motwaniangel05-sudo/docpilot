import json
import re

c = json.load(open("data/abstain_config.json"))
P = lambda x: f"{100 * x:.1f}%"
section = (
    "\n## Abstention (confidence threshold)\n\n"
    "Confidence = top reranker score (bge-reranker-base) after version-filtered hybrid retrieval. "
    f"If it is below **{c['threshold']}**, the app answers \"Cannot confirm for your version.\" "
    "The threshold was chosen from the risk-coverage curve (`data/risk_coverage.png`) by a rule fixed in advance: "
    "the lowest threshold that lets at most 1 of 20 off-topic questions through.\n\n"
    "Eval set (110 questions): 76 answerable, 14 trap (symbol removed or not yet added in the user's version), "
    "20 off-topic.\n\n"
    "| Metric | Value |\n|---|---|\n"
    f"| Threshold | {c['threshold']} |\n"
    f"| Coverage (share answered) | {P(c['coverage'])} |\n"
    f"| Risk (answered but wrong or unanswerable) at threshold | {P(c['risk'])} |\n"
    f"| Risk with no abstention | {P(c['risk_no_abstention'])} |\n"
    f"| Answerable questions still answered | {P(c['recall_answered'])} |\n"
    f"| Off-topic questions correctly abstained | {P(c['oos_abstained'])} |\n"
    f"| Trap questions abstained | {P(c['trap_abstained'])} |\n\n"
    "Limitations: the reranker score separates off-topic questions cleanly but not trap questions. "
    "With the version filter on, a removed symbol (for example `Series.is_monotonic`) is replaced by a close "
    "neighbor (`Series.is_monotonic_increasing`) that scores high, so traps are not caught by abstention. "
    "They are handled by the version filter (stale@1 0.0%) and the REMOVED/CHANGED notes. "
    "The threshold was tuned on the same 110 questions, with no held-out set.\n\n"
    "![risk-coverage](data/risk_coverage.png)\n"
)
md = open("results.md").read()
md = re.sub(r"\n## Abstention.*?(?=\n## |\Z)", "", md, flags=re.S).rstrip() + "\n" + section
open("results.md", "w").write(md)
print(section)
