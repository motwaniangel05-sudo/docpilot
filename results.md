# Evaluation results

Benchmark: 90 auto-generated questions from symbol differences between pandas 1.5.3 and 2.2.3
(removed=12, added=2, changed signatures=62).
Trap questions (stale-answer test): 14. Recall questions: 76. Version detection accuracy: 100.0%.

| Config | Stale@1 (trap) | Stale@5 (trap) | Wrong-version@1 | Recall@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| No filter, no reranker | 57.1% | 100.0% | 38.9% | 96.1% | 260 | 288 |
| Version filter, no reranker | 0.0% | 0.0% | 0.0% | 97.4% | 266 | 296 |
| No filter + reranker | 71.4% | 100.0% | 51.1% | 94.7% | 6526 | 7257 |
| Version filter + reranker (full system) | 0.0% | 0.0% | 0.0% | 97.4% | 6814 | 7614 |

Definitions:
- Stale@1 / Stale@5: share of trap questions where the top-1 / any of the top-5 results is a symbol that does not exist in the user's pandas version (for example DataFrame.append for a pandas 2.2 user).
- Wrong-version@1: share of all questions whose top-1 chunk belongs to the other pandas version.
- Recall@5: share of recall questions where the correct symbol, in the user's version, is in the top 5.
- Latency: search only, per query, on a MacBook (M1) CPU, after 3 warm-up queries.
- Caveat: questions are built from docstring summaries, so they leak some wording of the target symbol.

## Benchmark validation (hand-labeled)

- Question labels: 50/50 agree (100.0%)
- Version-validity labels: 30/30 agree (100.0%)
- Overall: 80/80 agree (100.0%)
- Method: 50 random benchmark questions and 30 (symbol, version) pairs checked by hand against the official pandas 1.5.3 and 2.2.3 docs pages. Raw labels: data/labels.csv.

## Production metrics (from logs/queries.jsonl)

- Queries logged: 20; cache hit rate: 50.0%
- Latency p50 / p95 (all): 2448 / 6327 ms
- Latency p50 / p95 (cache miss, full pipeline): 6052 / 6737 ms
- Latency p50 / p95 (cache hit): 0 / 0 ms
- Cost per query: $0.00 (total $0.00). It is zero because all models run locally on CPU, there are no paid API calls, and hosting is on a free tier.

## Abstention (confidence threshold)

Confidence = top reranker score (bge-reranker-base) after version-filtered hybrid retrieval. If it is below **0.105**, the app answers "Cannot confirm for your version."

Eval set (134 questions): 76 docstring-style answerable, 24 natural-phrased answerable (for example "remove duplicate rows pandas 2.2"), 14 trap (symbol removed or not yet added in the user's version), 20 off-topic.

How the threshold was chosen (full disclosure): a first threshold of 0.394, tuned on docstring-style questions only, answered just 54% of natural questions. A second rule (all answerable questions) gave 0.623 and dropped half of natural questions. The final rule, picked after seeing those results, maximizes (natural good answers kept) minus (off-topic questions let through), giving the threshold above.

| Metric | Value |
|---|---|
| Threshold | 0.105 |
| Coverage (share answered) | 86.6% |
| Risk (answered but wrong or unanswerable) at threshold | 19.8% |
| Risk with no abstention | 29.8% |
| Docstring-style questions still answered | 100.0% |
| Natural questions answered | 95.8% |
| Natural questions with a correct answer that are kept | 95.0% |
| Off-topic questions correctly abstained | 85.0% |
| Trap questions abstained | 0.0% |

Limitations: the threshold was tuned on the same questions it is evaluated on, with no held-out set. The natural set is only 24 hand-written questions. 3 of 20 off-topic questions still get answered. Abstention does not catch trap questions: with the version filter on, a removed symbol is replaced by a close neighbor that scores high. Traps are handled by the version filter (stale@1 0.0%) and the REMOVED/CHANGED notes. Some wrong answers also score high (for example a merge question returning `DataFrame.combine`), so a high score is not a guarantee.

![risk-coverage](data/risk_coverage.png)
