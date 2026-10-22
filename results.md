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

## P3: Execution check (pandas answers only)

Code blocks from the saved LLM answers (60 answers) were run on the pandas
version each answer cited (1.5 on pandas 1.5.3, 2.0 and 2.2 on pandas 2.2.3).
Each block ran in a temporary folder with a 10 s timeout and small synthetic
data. Run locally only, never on the deployed app.

| Measure | Result |
|---|---|
| Answers with a code block and a citation tag | 33 of 60 (23 had no code block, 6 had no citation tag) |
| Code blocks that could be run (pandas only) | 16 (NumPy 6 and sklearn 11 not run: no venvs) |
| Raw: ran without error (ok + warning) | 8 / 16 = 50.0% |
| Raw: ran with no warning | 6 / 16 = 37.5% |
| Incomplete snippets (use a variable the answer never creates) | 5 |
| Self-contained snippets (16 - 5) | 11 |
| Self-contained: ran after test-data fix | 10 / 11 = 90.9% |
| Real failures | 1 (a non-ASCII hyphen inside a date string in a tz_convert example) |

Notes and limits:
- 2 `shift(freq=...)` snippets failed only because the sandbox index was a plain
  number index. They passed when re-run on a date index. This fix was chosen
  after seeing the failures, so the 90.9% is an adjusted number. The raw 50%
  is the unadjusted one.
- "Ran without error" means the code runs. It does not prove the output is correct.
- 2 of the 8 passing runs gave a deprecation warning (Series.append, Series.slice_shift),
  which is correct for pandas 1.5.
- Small sample (16 blocks). Treat the rates as rough, not precise.

## P4: AI-generated test questions (pandas 1.5 and 2.2)

**Important:** these 50 questions were generated by ChatGPT, not collected from real users. The `source_url` column was never verified and is not cited. The `expected_api` labels were checked only partly (see below).

**Setup:** 50 questions. 38 were usable (19 for pandas 1.5, 19 for pandas 2.2). 12 were skipped because their version labels (for example "3.0 deprecation" or "Future release") are not supported by DocPilot. The test used search and the rule checker only. No LLM was called and no code was run.

**Retrieval (recall@5, API symbol found in the top 5 results):**

| Setup | Found | Rate |
|---|---|---|
| Without reranker (what the live app uses) | 10 / 38 | 26.3% |
| With reranker | 12 / 38 | 31.6% |

**Why it is low:** this is a coverage gap, not a ranking failure.
- 26 of 38 expected APIs have no matching symbol in the index. The index holds only `pd.*`, `DataFrame.*` and `Series.*` pages.
- About 16 of those 26 are not API pages at all (frequency aliases like `M`/`Q`/`BM`, "pandas 3.0 migration", "default string dtype").
- The other 10 are API names the index lacks, such as `Int64Index`, `Index.*`, `GroupBy.apply`, `ExcelWriter`, `Categorical`, `Series.str.*` and a config option (counted by hand).
- Every question whose expected API is in the index was found in the top 5 with the reranker (12 of 12). Without it, 10 of 12.
- "Not in index" comes from name matching, so near-matches may be missed. For example `pd.date_range` appears in the top 5 for the alias questions.

**Rule checker:** 8 of the 38 questions match one of the 29 rules, and 6 of those 8 have a rule that applies by pandas 2.2. This is a rough count, not a rate. The first version of this check used the wrong version and was dropped.

**Label spot-check (10 labels):** I looked up 10 APIs ChatGPT labeled as removed (`Int64Index`, `core.indexes.numeric`, `DataFrame.append`, `DataFrame.iteritems`, `Index.is_monotonic`, `DataFrame.mad`, `mode.use_inf_as_null`, `io.json.json_normalize`, `Categorical.to_dense`, `ExcelWriter.save`). All 10 exist in pandas 1.5.3 and all 10 are missing in pandas 2.2.3.
- This confirms only "present in 1.5.3, gone by 2.2.3".
- It does not confirm deprecated versus removed, or the exact version of removal. I did not test 2.0.
- All 10 came from the 1.5 questions. The 2.2 labels were not checked.
- The sample is small, and I picked APIs that were easy to test.

**Takeaway:** DocPilot retrieves well when the API is in its index, and the main limit is what the index covers. Adding `Index`, `GroupBy` and `ExcelWriter` pages, and a short notes section for non-API topics, is the next fix.

## P4: three-system comparison (38 AI-generated questions, pandas 1.5 and 2.2)

**Important:** ChatGPT wrote the questions and the expected-API labels. They are not from real users, and the labels are only partly checked (see the section above). Everything below uses one Groq model (`openai/gpt-oss-20b`) and is a small sample.

**Systems:** (1) plain LLM, no retrieval. (2) Retrieval only: the top search chunk, no LLM and no code. (3) Full DocPilot: retrieval plus the cited LLM answer.

| | Plain LLM | Retrieval only | Full DocPilot |
|---|---|---|---|
| Questions answered | 38 of 38 | 38 of 38 | 14 of 38 (24 abstained, 2 answered without code) |
| Answers with code | 37 | 0 | 12 |
| Stale answers flagged by the checker (pandas 2.2) | 1 of 37 | not applicable | 1 of 12 |
| Stale after reading the flagged answers | 0 | not applicable | 0 |
| Code blocks run (pandas 2.2) | 38 | not applicable | 13 |
| Ran without error, raw | 18 (47.4%) | not applicable | 5 (38.5%) |
| Ran without error, adjusted* | 20 (52.6%) | not applicable | 7 (53.8%) |
| Median / p95 latency (s) | 1.15 / 2.8 | 0.09 / 0.16 | 14.79 / 18.02 |
| Answers I judged wrong by reading (lower bound) | at least 9 | not applicable | 0 found (only 5 answers read) |

*Adjusted means I added columns and a date index to the test data after seeing the failures. It fixed only 3 blocks.

**Stale-answer rate does not separate the systems.** The checker flagged 2 answers. Both showed the removed API as a "before" example, so both were false positives. After reading them, both systems score 0 stale. The checker only sees calls covered by the 29 rules.

**The real difference is abstention.** Full DocPilot declined 24 of 38 questions, which fits the 26 questions whose API is not in the index. The plain model answered everything, and at least 9 of its answers were wrong.

**Failure analysis (plain LLM, 15 blocks still failing after the test-data fix, my hand judgment):**
- 7: the answer's code is wrong. 005 tells you to import a removed module. 016 calls `.to_numpy()` on a NumPy array. 019 says an Index can be mutated. 023 uses a `date_parser` argument `to_datetime()` does not have. 032 invents a `pandas_compat` module. 042 uses `format='business_quarter_end'`, which is not a frequency alias. 043 recommends `B-Y`, which is invalid. The correct alias is `BYE`.
- 3: expected errors ("before" examples or a deliberate raise): 009 block 0, 014, 031.
- 5: my test environment: 009 block 1, 012, 017, 028, 029.
- Wrong text with code that runs: 025 says `Series.view` was removed (it is deprecated). 031 says `skipna` was removed and that no warning is issued. A check on pandas 2.2.3 showed a FutureWarning.

**Full DocPilot (2 errors left):** 011 is a "before" example. 007 is an incomplete fragment.

**Limits:**
- Full DocPilot wrote only 13 blocks, so its execution rate is too small to compare with plain.
- 9 wrong plain answers is a lower bound, because I read only errored and flagged answers.
- Full DocPilot is about 13 times slower than plain at the median. I did not test why.
- Running without error does not prove the answer is correct.
