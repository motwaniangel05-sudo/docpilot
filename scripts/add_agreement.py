import csv
import json
import re

rows = list(csv.DictReader(open("data/labels.csv", encoding="utf-8-sig")))
rows = [{k.strip(): (v or "").strip().lower() for k, v in r.items() if k} for r in rows]
q = [r for r in rows if r["task"] == "question"]
v = [r for r in rows if r["task"] == "validity"]


def agree(rs):
    return sum(r["human"] == r["benchmark_says"] for r in rs)


stats = {
    "question_agree": agree(q), "question_n": len(q),
    "validity_agree": agree(v), "validity_n": len(v),
    "overall_agree": agree(rows), "overall_n": len(rows),
}
json.dump(stats, open("data/label_agreement.json", "w"), indent=2)

section = (
    "\n## Benchmark validation (hand-labeled)\n\n"
    f"- Question labels: {stats['question_agree']}/{stats['question_n']} agree "
    f"({100 * stats['question_agree'] / stats['question_n']:.1f}%)\n"
    f"- Version-validity labels: {stats['validity_agree']}/{stats['validity_n']} agree "
    f"({100 * stats['validity_agree'] / stats['validity_n']:.1f}%)\n"
    f"- Overall: {stats['overall_agree']}/{stats['overall_n']} agree "
    f"({100 * stats['overall_agree'] / stats['overall_n']:.1f}%)\n"
    "- Method: 50 random benchmark questions and 30 (symbol, version) pairs checked by hand "
    "against the official pandas 1.5.3 and 2.2.3 docs pages. Raw labels: data/labels.csv.\n"
)
md = open("results.md").read()
md = re.sub(r"\n## Benchmark validation.*", "", md, flags=re.S).rstrip() + "\n" + section
open("results.md", "w").write(md)
print(section)
