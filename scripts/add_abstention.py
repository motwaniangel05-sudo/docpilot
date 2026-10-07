import json
import re

c = json.load(open("data/abstain_config.json"))
P = lambda x: f"{100 * x:.1f}%"
section = (
    "\n## Abstention (confidence threshold)\n\n"
    "Confidence = top reranker score (bge-reranker-base) after version-filtered hybrid retrieval. "
    f"If it is below **{c['threshold']}**, the app answers \"Cannot confirm for your version.\"\n\n"
    f"Eval set ({c['n_questions']} questions): 76 docstring-style answerable, 24 natural-phrased answerable "
    "(for example \"remove duplicate rows pandas 2.2\"), 14 trap (symbol removed or not yet added in the user's version), "
    "20 off-topic.\n\n"
    "How the threshold was chosen (full disclosure): a first threshold of 0.394, tuned on docstring-style questions only, "
    "answered just 54% of natural questions. A second rule (all answerable questions) gave 0.623 and dropped half of "
    "natural questions. The final rule, picked after seeing those results, maximizes (natural good answers kept) minus "
    "(off-topic questions let through), giving the threshold above.\n\n"
    "| Metric | Value |\n|---|---|\n"
    f"| Threshold | {c['threshold']} |\n"
    f"| Coverage (share answered) | {P(c['coverage'])} |\n"
    f"| Risk (answered but wrong or unanswerable) at threshold | {P(c['risk'])} |\n"
    f"| Risk with no abstention | {P(c['risk_no_abstention'])} |\n"
    f"| Docstring-style questions still answered | {P(c['recall_answered'])} |\n"
    f"| Natural questions answered | {P(c['natural_answered'])} |\n"
    f"| Natural questions with a correct answer that are kept | {P(c['natural_good_kept'])} |\n"
    f"| Off-topic questions correctly abstained | {P(c['oos_abstained'])} |\n"
    f"| Trap questions abstained | {P(c['trap_abstained'])} |\n\n"
    "Limitations: the threshold was tuned on the same questions it is evaluated on, with no held-out set. "
    "The natural set is only 24 hand-written questions. 3 of 20 off-topic questions still get answered. "
    "Abstention does not catch trap questions: with the version filter on, a removed symbol is replaced by a close "
    "neighbor that scores high. Traps are handled by the version filter (stale@1 0.0%) and the REMOVED/CHANGED notes. "
    "Some wrong answers also score high (for example a merge question returning `DataFrame.combine`), so a high score is not a guarantee.\n\n"
    "![risk-coverage](data/risk_coverage.png)\n"
)
md = open("results.md").read()
md = re.sub(r"\n## Abstention.*?(?=\n## |\Z)", "", md, flags=re.S).rstrip() + "\n" + section
open("results.md", "w").write(md)
print(section)
