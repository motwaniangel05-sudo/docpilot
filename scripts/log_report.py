import json
import re
import sys

import numpy as np

sys.path.insert(0, ".")
from docpilot.observe import COST_PER_QUERY_USD, LOG_PATH

rows = [json.loads(line) for line in open(LOG_PATH) if line.strip()]
if not rows:
    raise SystemExit("logs/queries.jsonl is empty")


def pct(vals, p):
    return f"{np.percentile(vals, p):.0f}" if vals else "n/a"


all_l = [r["latency_ms"] for r in rows]
miss = [r["latency_ms"] for r in rows if not r["cache_hit"]]
hit = [r["latency_ms"] for r in rows if r["cache_hit"]]
total_cost = sum(r["cost_usd"] for r in rows)

section = (
    "\n## Production metrics (from logs/queries.jsonl)\n\n"
    f"- Queries logged: {len(rows)}; cache hit rate: {100 * len(hit) / len(rows):.1f}%\n"
    f"- Latency p50 / p95 (all): {pct(all_l, 50)} / {pct(all_l, 95)} ms\n"
    f"- Latency p50 / p95 (cache miss, full pipeline): {pct(miss, 50)} / {pct(miss, 95)} ms\n"
    f"- Latency p50 / p95 (cache hit): {pct(hit, 50)} / {pct(hit, 95)} ms\n"
    f"- Cost per query: ${COST_PER_QUERY_USD:.2f} (total ${total_cost:.2f}). It is zero because "
    "all models run locally on CPU, there are no paid API calls, and hosting is on a free tier.\n"
)
print(section)
md = open("results.md").read()
md = re.sub(r"\n## Production metrics.*?(?=\n## |\Z)", "", md, flags=re.S).rstrip() + "\n" + section
open("results.md", "w").write(md)
