# Evaluation results

Benchmark: 150 auto-generated questions across pandas (1.5, 2.0, 2.2), NumPy (1.26, 2.1) and scikit-learn (1.3, 1.5),
50 per library. Trap questions (symbol absent in the user's version): 29. Recall questions: 121.
Library and version detection accuracy: 100.0%. Index: 3017 chunks.

| Config | Stale@1 (trap) | Stale@5 (trap) | Wrong-version@1 | Recall@5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| No version filter, no reranker | 69.0% | 100.0% | 48.0% | 96.7% | 253 | 296 |
| Version filter, no reranker | 0.0% | 0.0% | 0.0% | 98.3% | 268 | 307 |
| No version filter + reranker | 79.3% | 96.6% | 53.3% | 95.9% | 7483 | 9043 |
| Version filter + reranker (full system) | 0.0% | 0.0% | 0.0% | 100.0% | 8048 | 11823 |

Full system, per library:

| Library | Questions | Trap | Stale@1 | Stale@5 | Recall@5 |
|---|---|---|---|---|---|
| pandas | 50 | 12 | 0.0% | 0.0% | 100.0% |
| numpy | 50 | 12 | 0.0% | 0.0% | 100.0% |
| sklearn | 50 | 5 | 0.0% | 0.0% | 100.0% |

Definitions:
- Stale@1 / Stale@5: share of trap questions where the top-1 / any of the top-5 results is a symbol that does not exist in the user's library version.
- Wrong-version@1: share of all questions whose top-1 chunk belongs to another version of the library.
- Recall@5: share of recall questions where the correct symbol, in the user's version, is in the top 5.
- All configs filter by library (detected from the question); "version filter" adds the detected version.
- Latency: search only, per query, MacBook M1 CPU, after 3 warm-up queries.
- Caveat: questions are built from docstring summaries, so they leak some wording of the target symbol.
- The 80 hand-labeled samples (below) were drawn from the earlier pandas-only benchmark, not this one.

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

## Delta indexing

Symbols whose text is identical across versions are stored and embedded once, with the list of versions they apply to (`applies`); search filters on library and that list (`docpilot/delta.py`, `scripts/build_index_delta.py`).

| | Naive (one chunk per symbol per version) | Delta |
|---|---|---|
| Chunks | 3017 | 2700 |
| Index size on disk | 45.3 MB | 41.2 MB |

Size reduction: **9.2%** (chunks: 10.5%; pandas 16.6%, scikit-learn 11.8%, NumPy 1.1%). The gain is small because most docstrings change at least slightly between versions, so few chunks are byte-identical. Stale@1 (0.0%) and recall@5 (98.35%, no reranker, 150 questions) are identical to the naive index. 127/150 top-5 lists are identical; the rest differ in order only. Limitation: unchanged-text detection is exact string match, with no near-duplicate merging.

## Embedding fine-tuning ablation

bge-small fine-tuned with MultipleNegativesRankingLoss on 1132 synthetic (question, chunk) pairs built from docstring summaries (2 epochs, lr 2e-5, batch 32). Symbols and summaries used in the 150-question benchmark or the 24 natural questions were excluded from training. Version filter on, no reranker. Benchmark = 121 recall questions (Recall@1, Recall@5) and 29 trap questions (Stale@1); Natural = 24 hand-written questions.

| Embedder | Retrieval | Recall@1 | Recall@5 | Stale@1 | Natural R@1 | Natural R@5 |
|---|---|---|---|---|---|---|
| base bge-small | dense | 81.0% | 98.3% | 0.0% | 54.2% | 91.7% |
| base bge-small | hybrid | 83.5% | 98.3% | 0.0% | 58.3% | 83.3% |
| fine-tuned bge-small | dense | 90.9% | 100.0% | 0.0% | 58.3% | 95.8% |
| fine-tuned bge-small | hybrid | 90.1% | 98.3% | 0.0% | 58.3% | 83.3% |

Caveats: training questions are synthetic templates over docstring first lines (the same source as the benchmark, so the benchmark is easier than real queries); NumPy ufunc docstrings start with a signature, which adds noisy pairs; the natural set is small.


## P1: Code checker (static, AST-based)

Parses a pasted Python snippet with Python's `ast` module (the code is never executed) and flags calls to pandas APIs that were removed or deprecated in the chosen version (1.5, 2.0 or 2.2), with the replacement and the version where it changed.

Rules (`data/api_rules.json`, 29 rules): 12 removed APIs found by diffing the symbol JSONs of 1.5 and 2.0, and 17 deprecated APIs parsed from `.. deprecated::` docstring directives (symbol-level only; parameter-level deprecations are ignored). Replacements for removed APIs were added by hand from the pandas 2.0 whatsnew and are marked as manual in the file. Some deprecated replacements were also fixed by hand.

Evaluation on a hand-written set of 40 snippets (31 expected findings), `data/checker_testset.json`, script `scripts/eval_checker.py`:

| Scoring | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| Strict (line and full symbol, e.g. `Series.mad` is not `DataFrame.mad`) | 26 | 2 | 5 | 92.9% | 83.9% |
| Name-level (line and method name) | 27 | 1 | 4 | 96.4% | 87.1% |

Snippets matched exactly: 34/40. 20 unit tests in `tests/test_checker.py` pass.

Failures (reported as measured):
- 1 false alarm: `iteritems` is flagged by name, so a plain Python 2 `dict.iteritems()` is flagged (medium confidence).
- 1 wrong label: `s2.mad()` on a Series obtained from `s.append(...)` was reported as `DataFrame.mad` instead of `Series.mad`.
- 4 misses: `self.df` attributes, `from pandas import read_gbq`, a DataFrame returned from a user function, and a `groupby` loop variable. The checker tracks only simple assignments from `pd.*` calls and variable names like `df`, `ser`.

Limitations: the test set was written by the same person who built the checker, so it is not independent and the numbers are likely optimistic. It checks only the 29 APIs in the rules file (only symbols in DocPilot's index), not every pandas change. Detection is name-based with heuristics, not type inference.


## P2: Cited answers (Groq gpt-oss-20b, retrieved chunks only)

The app writes a short answer from the top 3 retrieved chunks (version-filtered, no reranker) and cites each symbol as `[Symbol | library version]`. If the key is missing or the API fails, the app falls back to a one-line extractive answer with a citation.

Faithfulness script: `scripts/eval_faithfulness.py` (generation, cached) and `scripts/rescore_faithfulness.py` (scoring). Sample: 60 questions from the 150-question multi-library benchmark (20 per library, up to 6 traps each, seed 42). 6 answers said "Cannot confirm", leaving 54 answered. An answer is faithful if every cited symbol was retrieved and valid at the chosen version, and every other API it names was among the retrieved chunks.

| Metric | Value |
|---|---|
| First scoring, exact name match (unnormalized) | 30/54 = 55.6% |
| Normalized (short names match prefixed symbols, generic names ignored) | 53/54 = 98.1% |
| Normalized, and no chunk-number citation format errors | 50/54 = 92.6% |
| Trap questions answered / faithful | 11 / 11 |
| By library (faithful/answered) | pandas 18/18, numpy 18/19, sklearn 17/17 |
| Answers with at least one citation | 81.5% |

Why two numbers: the first scoring compared `trapz` with the stored name `np.trapz`, and `AgglomerativeClustering` with `sklearn.cluster.AgglomerativeClustering`, so it flagged correct answers. I fixed the matcher after seeing this. The ignored generic names (DataFrame, Index, Series, a, array, axis, b, df, dx, factorize, gt, join, mean, n, seed, size, std, sum, x, y) were chosen by me after viewing the violations, so the normalized rate is tuned on the same sample.

Remaining failures: one real hallucination (cited `DataFrame.map` on a NumPy std question); 3 answers cited chunk numbers (`[1 | ...]`) instead of symbols.

Limitations: 60 questions, one run, temperature 0; questions are built from docstring summaries, so they are easier than real ones; the checker verifies named symbols, not whether the explanation is correct; 18.5% of answers had no citation at all.
