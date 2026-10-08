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
