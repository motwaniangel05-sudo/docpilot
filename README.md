# DocPilot

**Live app: https://docpilot-5ov2htcjpmznaondpjkiqg.streamlit.app**

Version-aware RAG assistant for API docs: pandas (1.5, 2.0, 2.2), NumPy (1.26, 2.1), scikit-learn (1.3, 1.5). It retrieves the right API symbol for your library version and warns when the answer differs (for example `DataFrame.append` exists in pandas 1.5 and was removed in 2.0).

## Headline numbers

| What | Result |
|---|---|
| Benchmark | 150 auto-generated questions (29 trap), 3 libraries |
| Stale-answer rate@1 (full system) | 0.0% (69.0% without the version filter) |
| Recall@5 | 100% full system, 98.3% without reranker (the deployed default) |
| Benchmark validation | 80/80 hand-checked labels (pandas-only sample) |
| CI | Fails on any regression vs `baseline.json` |
| Cost per query | $0.00 (local models, free hosting) |
| Abstention | 85% of off-topic questions abstained, 95% of correct natural answers kept (opt-in) |
| Index | 3017 to 2700 chunks, 45.3 to 41.2 MB with delta indexing |
| Peak RAM | 589 MB without reranker, about 1.4 GB with it |

## Known limitations

- Benchmark questions come from docstring summaries, so they are easier than real queries.
- The 0.0% stale rate is partly by construction (the version filter makes absent symbols unreachable).
- Abstention does not catch trap questions, and its threshold was tuned on the evaluation set.
- Hand validation covered only the pandas benchmark.
- The fine-tuned embedder is not deployed.

Free Streamlit Community Cloud apps sleep when idle. If you see a "wake up" button, click it and wait a minute or two.

## Results

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

**Headline:** the version filter cuts the stale-answer rate (top-1) from 57.1% to 0.0% and top-5 from 100% to 0.0%, with recall@5 unchanged at 97.4%. The reranker adds about 6.5 s per query and gives no recall gain, so the live app has it off by default.

## How it works

- **Data:** every public DataFrame/Series method, property and top-level function extracted from pandas 1.5.3 and 2.2.3 with Python's `inspect` (name, signature, docstring). 938 chunks, one per symbol per version, with `valid_from` / `valid_until`.
- **Retrieval:** BM25 (`rank_bm25`) + dense search (`BAAI/bge-small-en-v1.5` in Qdrant local mode), fused with Reciprocal Rank Fusion. A version filter keeps only chunks from the user's pandas version. Optional cross-encoder reranker (`BAAI/bge-reranker-base`).
- **Version detection:** regex on the question or a pasted requirements.txt. If no version is found, it defaults to 2.2 and says so.
- **"Changed in X" notes:** computed programmatically by comparing each symbol's signature across versions. No LLM is involved.
- **No LLM needed:** the app shows the retrieved symbol, signature, docstring and change note. The index is built offline and committed in `index/`; the app only loads it.

## Run it yourself

```
./run_eval.sh                 # rebuilds extraction, chunks, index, benchmark, results.md (about 15 min)
streamlit run app.py          # local app
```

## Failure analysis

**Recall misses (version filter, no reranker, the deployed default):**

- **Target:** `Series.apply` (pandas 1.5)
  - Question: In pandas 1.5, with a Series: Invoke function on values of Series
  - Top 5 returned: Series.transform v1.5, Series.aggregate v1.5, Series.agg v1.5, Series.map v1.5, Series.isin v1.5
- **Target:** `pd.read_table` (pandas 2.2)
  - Question: In pandas 2.2, with a top-level function: Read general delimited file into DataFrame
  - Top 5 returned: pd.read_clipboard v2.2, pd.read_fwf v2.2, pd.read_feather v2.2, pd.read_sas v2.2, pd.read_json v2.2

**Other observed failures and limitations:**

- Vague "how do I" questions can miss the canonical function. In manual tests, "combine two dataframes by rows" returned `combine`, `combine_first` and `compare` instead of `pd.concat`, because dense and keyword search both match the docstring wording, not the intent.
- The benchmark questions are built from docstring summaries, so they share wording with the target symbol. Recall is therefore optimistic compared with real user questions.
- Only 14 stale-answer trap questions qualified (12 removed + 2 added symbols with usable docstrings). The 0.0% result is real but the sample is small.
- Only two pandas versions (1.5.3 and 2.2.3) are indexed. Other versions are mapped to the nearest one, and the app says so.
- Chunks contain signature and docstring only, with no usage examples from the user guide, so the app finds the right API but does not write code.
- Behavior changes without a signature change (for example changed defaults inside the function body) are not detected by the signature comparison.
- The reranker was slow on CPU (about 6.5 s per query) and did not improve recall on this benchmark.

## Future work

Optional LLM summary (Groq or Gemini free tier, key stored as a secret, app must still run without it), indexing user-guide examples, more pandas versions.

## Deployment note

Hugging Face Spaces was the original target, but at deployment time free accounts could only create Static Spaces (Docker and Gradio required a paid plan), so the app is deployed on Streamlit Community Cloud. A `Dockerfile` is included for self-hosting.

## Benchmark validation

I hand-checked 80 samples (50 benchmark questions, 30 symbol/version pairs) against the official pandas 1.5.3 and 2.2.3 docs: 80/80 agree with the benchmark's version labels. Details in `results.md`; raw labels in `data/labels.csv`.

## CI and production metrics

- GitHub Actions (`.github/workflows/eval.yml`) runs `scripts/ci_eval.py` on every push and fails if stale@1 or recall@5 is worse than `baseline.json` (stale@1 0.0%, recall@5 97.4%).
- `docpilot/observe.py` adds an LRU query cache, JSON-lines logging (`logs/queries.jsonl`), and cost tracking. `scripts/log_report.py` writes p50/p95 latency and cache hit rate to `results.md`.
- Demo run (20 queries, 50% repeats): cache miss p50 6052 ms, cache hit about 0 ms. Cost per query is $0.00 because all models run locally on CPU with free hosting.

## Abstention

DocPilot answers "Cannot confirm for your version." when the top reranker score is below 0.105 (`data/risk_coverage.png`). On 134 questions (docstring-style, natural-phrased, trap, off-topic) it abstains on 85.0% of off-topic questions, keeps 95.0% of natural questions that have a correct answer, and cuts risk from 29.8% to 19.8%. It does not catch trap questions; the version filter handles those. The threshold was revised twice after a first value over-abstained on natural phrasing, and it is tuned on the evaluation set. See `results.md`.

## Coverage: pandas, NumPy, scikit-learn

Index now covers pandas (1.5, 2.0, 2.2), NumPy (1.26, 2.1) and scikit-learn (1.3, 1.5), built by the same extraction pipeline (`scripts/extract_symbols.py`, `scripts/extract_lib.py`, `scripts/build_chunks.py`). Every chunk has `library`, `version`, `valid_from`, `valid_until`; search filters on library and version.

Re-run on a new 150-question benchmark (50 per library, 29 trap questions; `data/benchmark_multi.json`). Full system (version filter + reranker): stale@1 0.0%, recall@5 100.0%. Without the reranker: stale@1 0.0%, recall@5 98.3%. Without the version filter, stale@1 is 69.0% (no reranker) and 79.3% (with reranker). The sklearn trap set is small (5), and stale 0.0% is partly by construction because the version filter makes absent symbols unreachable. Earlier pandas-only tables, the 80 hand-labeled samples and the abstention threshold come from the pandas-only benchmark; they were not redone for NumPy or scikit-learn.

Size and memory (measured on an M1 Mac): 938 to 3017 chunks; index 14 MB to 45 MB. Peak RAM is 589 MB without the reranker and about 1.4 to 1.6 GB with it (bfloat16 did not reduce it). Because of this, abstention is opt-in in the deployed app. CI runs the no-reranker config (baseline: stale@1 0.0, recall@5 0.9835).

Reranker effect on natural phrasing (6 hand-picked queries, not a benchmark): the target is in the top 2 for 5 of 6 queries without the reranker. The exception is "numpy 2.1 product of array elements", where `np.prod` is rank 8 without the reranker and rank 1 with it. The deployed app runs without the reranker by default (RAM), so tick "Use reranker for ranking" for harder queries.

## Delta indexing

Identical symbol text across versions is stored once with a version list. On the 3-library index this cut 3017 chunks to 2700 and index size from 45.3 MB to 41.2 MB (9.2% smaller). Small, because most docstrings change slightly between versions. Stale@1 (0.0%) and recall@5 (98.35%) are unchanged. Details in `results.md`.

## Embedding fine-tuning ablation

Fine-tuned bge-small on 1132 synthetic question-chunk pairs (symbols from the benchmark and natural questions excluded from training). With the version filter on and no reranker: dense Recall@1 81.0% to 90.9% and Recall@5 98.3% to 100.0%. In the hybrid (dense + BM25) config the deployed app uses, Recall@1 goes 83.5% to 90.1% but Recall@5 is unchanged at 98.3%. Natural-phrased R@5 (24 questions, so 1 question = 4.2 points) is 91.7% to 95.8% dense and 83.3% for both models hybrid. Stale@1 stays 0.0%. The fine-tuned model is not deployed (about 130 MB; the app still uses base bge-small). Caveats: training questions are templates over docstring first lines, the same source as the benchmark, and some NumPy pairs are just signatures. Full table in `results.md`.


## Code checker (P1)

New tab in the app: paste a Python snippet, choose pandas 1.5, 2.0 or 2.2, and DocPilot lists calls that were removed or deprecated in that version, with line number, replacement and the version of the change. It uses Python's `ast` module and never runs your code.

- Rules: `data/api_rules.json` (29 APIs: 12 removed, 17 deprecated), built by `scripts/build_rules.py` from the symbol files and docstring deprecation notes, with hand-added replacements from the pandas whatsnew.
- Tests: `pytest tests/test_checker.py` (20 tests).
- Evaluation (`python scripts/eval_checker.py`, 40 hand-written snippets): strict precision 92.9% / recall 83.9%; name-level precision 96.4% / recall 87.1%.
- Known limits: misses `self.df`, `from pandas import ...` and values returned from functions; flags `iteritems` on plain dicts. The test set is self-written, so treat the numbers as an upper bound.


## Cited answers (P2)

Search results now come with a short LLM answer written only from the top 3 retrieved chunks, with `[Symbol | library version]` citations. The key is read from the Streamlit secret `GROQ_API_KEY` (never in the repo); without it the app shows an extractive one-line answer and keeps working.

- Faithfulness (60-question sample, 54 answered): 53/54 = 98.1% normalized; 92.6% when chunk-number citations also count as errors; 55.6% with the first, strict name matching (which wrongly flagged short vs prefixed names). Details in `results.md`.
- Limits: tuned scoring on the same sample, small sample, 1 real hallucination found.

## Execution check (P3)

DocPilot can run the code in its saved answers on the pandas version the answer
cites, to see if the code really works there. Of 16 runnable pandas snippets,
8 ran without error (50% raw). 5 were incomplete examples with undefined
variables; of the 11 self-contained ones, 10 ran after fixing the test data
(90.9%, adjusted after the fact). Details and limits are in `results.md`.

Running code is off by default. It only runs on your own machine with
`DOCPILOT_ALLOW_EXEC=1` and is not a security boundary. The deployed app shows
the saved results from `data/exec_results.json` and never executes code.

    DOCPILOT_ALLOW_EXEC=1 PYTHONPATH=. python scripts/run_exec.py

## Test on AI-generated questions (pandas 1.5 and 2.2)

I tested search on 38 usable questions (19 for pandas 1.5, 19 for pandas 2.2). **ChatGPT wrote the questions and the expected-API labels. They are not from real users.** The `source_url` column was never verified and is not used.

- **Recall@5:** 26.3% without the reranker (what the live app uses), 31.6% with it.
- **Why it is low:** the index has no page for 26 of the 38 expected APIs. About 16 of those are not API pages at all (frequency aliases, "pandas 3.0 migration"). The rest are API names the index lacks, such as `Index.*`, `GroupBy.apply` and `ExcelWriter`.
- **When the API is in the index:** it was found in the top 5 for 12 of 12 questions with the reranker, and 10 of 12 without it.
- **Label check:** I looked up 10 labeled APIs. All 10 are present in pandas 1.5.3 and missing in 2.2.3. Only 1.5 questions were checked, and 2.0 and the 2.2 labels were not.
- **Not tested:** no LLM answers and no code execution in this test.

Details: see `results.md`.

## Three-system comparison (AI-generated questions)

**ChatGPT wrote the 38 questions and their expected-API labels. They are not from real users, and the labels are only partly checked.** One Groq model (`openai/gpt-oss-20b`) was used for all systems. The sample is small.

| | Plain LLM | Retrieval only | Full DocPilot |
|---|---|---|---|
| Questions answered | 38 of 38 | 38 of 38 | 14 of 38 (24 abstained) |
| Code blocks run (pandas 2.2) | 38 | none | 13 |
| Ran without error, raw / adjusted* | 47.4% / 52.6% | not applicable | 38.5% / 53.8% |
| Median / p95 latency (s) | 1.15 / 2.8 | 0.09 / 0.16 | 14.79 / 18.02 |
| Answers I judged wrong by reading | at least 9 | not applicable | 0 found (only a few read) |

*Adjusted = I added columns and a date index to the test data after seeing failures. It fixed 3 blocks.

- **Stale-answer rate did not separate the systems.** The checker flagged 2 answers. Both showed the removed API as a "before" example, so both are 0 after reading them.
- **The real difference is abstention.** Full DocPilot declined 24 questions, matching the 26 whose API is missing from the index. Plain answered everything, and at least 9 of its answers were wrong. This is a lower bound, since I read only errored and flagged answers.
- **Full DocPilot is about 13 times slower** at the median. I did not test why.
- **Code blocks were run locally only.** Running without error does not prove an answer is correct.

Details and failure analysis: see `results.md`.

## Upgrade report (pandas 1.5 to 2.2)

Upload a `.py` file or a `.zip` in the **Upgrade report** tab. DocPilot parses every `.py` file with `ast` (nothing is run or saved) and lists calls that break between two pandas versions, with file, line and fix. Only **high-confidence** findings count as breaking. Medium-confidence ones (receiver not clearly pandas) are listed apart as "check by hand". Limits are 500 files, 20 MB, and zip paths are checked.

**Test on 3 open-source repos (current HEAD, scanned 1.5 to 2.2).** These are modern codebases, not pandas 1.x projects, so most were probably already migrated.

| Repo (commit) | Files | High (counted) | Low (apart) |
|---|---|---|---|
| xarray (989e6ff) | 245 | 5 | 2 |
| statsmodels (30df665) | 1250 | 21 | 21 |
| scikit-learn (718eedb) | 1038 | 2 | 1 |

**I read all 52 findings by hand** (one source line each, so types are not verified):
- **High (28):** 18 likely real, 8 false positives, 2 unclear. Precision 18 of 28 (64.3%), counting unclear as wrong. 15 of the 18 are `applymap` calls in statsmodels, and one of those (`news.py:932`) may be on a Series.
- **Low (24):** all 24 were false positives (statsmodels' own `mad` functions, an object's own `is_monotonic`, a `hasattr`-guarded `iteritems`). This is why they are not counted.
- **Remaining false positives:** `Index.append`, `defaultdict(list)` items, and a results object's `.append`. The checker cannot tell these from DataFrames by name.
- **Recall was not measured on real repos.**

**What changed along the way:** the first scan had 93 findings, and a 35-finding sample was only 8.6% real. The cause was that a name which was a list early in a file and a DataFrame later counted as pandas everywhere. I made the ambiguous-method check order-aware and rescanned. xarray also had 43 files unparsable on Python 3.11 because they use 3.12 syntax, so the final scan ran on 3.12.

**P1 re-checked after the change:** strict precision 92.9% and recall 83.9% on the 40 hand-written snippets, unchanged. Those snippets rarely use list names like pandas objects, so this does not show the repo problem is solved. 34 tests pass.

Details: `results.md`. Raw scans: `data/repo_scan_before_fix.json`, `data/repo_scan_after_fix.json`, `data/repo_scan_final.json`.

## Command line: docpilot check

Check a file or a folder from the terminal. Nothing is run: files are only parsed with `ast`.

    python -m docpilot check path/to/file.py --pandas 2.2
    python -m docpilot check path/to/project --pandas 2.2

- `--pandas` is the target version (1.5, 2.0 or 2.2).
- Only **high-confidence** findings count as breaking. Low-confidence ones print as "check by hand" and do not change the exit code.
- Exit codes: `1` if breaking calls are found, `0` if none, `2` on bad input (missing path, no `.py` files, bad version).
- It uses only the standard library, so it needs no install and no torch.
- Same limits as the upgrade report: name-based checks, so it can miss calls and can flag non-pandas objects (see the P5 section). It checks the target version only, not a from/to range.
- 8 tests cover the exit codes and folder scanning (42 tests in total).

## GitHub Action: check pull requests

The workflow `.github/workflows/docpilot-check.yml` runs on pull requests that change `.py` files.

- It checks only the changed `.py` files, skipping the `scripts/` folder. Nothing is run, and files are only parsed with `ast`.
- The target is pandas 2.2. To change it, edit `PANDAS_TARGET` in the workflow file.
- It posts one comment on the pull request and updates that comment on later pushes.
- It fails the check if high-confidence breaking calls are found.
- It installs only Python, with no torch, so it finishes in about a minute.
- **Tested on one real pull request** with one planted `DataFrame.append` call, and it reported that call correctly. It was not tested on forks, large pull requests, or other pandas versions.
- On fork pull requests GitHub gives a read-only token, so the comment step would only log a warning and the check result would still apply.
- Same limits as the CLI: name-based checks, so it can miss calls and can flag non-pandas objects (see the P5 section).
