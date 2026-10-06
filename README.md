# DocPilot

**Live app: https://docpilot-5ov2htcjpmznaondpjkiqg.streamlit.app**

Version-aware RAG assistant for the pandas library. Ask "how do I do X in pandas?" for pandas 1.5 or 2.2. It retrieves the right API symbol for your version and warns when the answer differs (for example `DataFrame.append` exists in 1.5 and was removed in 2.0).

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
