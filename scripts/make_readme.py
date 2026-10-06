import json

URL = "https://docpilot-5ov2htcjpmznaondpjkiqg.streamlit.app"
F = "`" * 3
res = open("results.md").read().split("\n", 1)[1].strip()
details = json.load(open("data/eval_details.json"))
rows = details["Version filter, no reranker"]
misses = [r for r in rows if r["hit"] is False]

miss_md = ""
for r in misses:
    miss_md += "- **Target:** `" + str(r["target"]) + "` (pandas " + r["user_version"] + ")\n"
    miss_md += "  - Question: " + r["q"] + "\n"
    miss_md += "  - Top 5 returned: " + ", ".join(r["top5"]) + "\n"
if not miss_md:
    miss_md = "- No recall misses in this run.\n"

readme = """# DocPilot

**Live app: """ + URL + """**

Version-aware RAG assistant for the pandas library. Ask "how do I do X in pandas?" for pandas 1.5 or 2.2. It retrieves the right API symbol for your version and warns when the answer differs (for example `DataFrame.append` exists in 1.5 and was removed in 2.0).

Free Streamlit Community Cloud apps sleep when idle. If you see a "wake up" button, click it and wait a minute or two.

## Results

""" + res + """

**Headline:** the version filter cuts the stale-answer rate (top-1) from 57.1% to 0.0% and top-5 from 100% to 0.0%, with recall@5 unchanged at 97.4%. The reranker adds about 6.5 s per query and gives no recall gain, so the live app has it off by default.

## How it works

- **Data:** every public DataFrame/Series method, property and top-level function extracted from pandas 1.5.3 and 2.2.3 with Python's `inspect` (name, signature, docstring). 938 chunks, one per symbol per version, with `valid_from` / `valid_until`.
- **Retrieval:** BM25 (`rank_bm25`) + dense search (`BAAI/bge-small-en-v1.5` in Qdrant local mode), fused with Reciprocal Rank Fusion. A version filter keeps only chunks from the user's pandas version. Optional cross-encoder reranker (`BAAI/bge-reranker-base`).
- **Version detection:** regex on the question or a pasted requirements.txt. If no version is found, it defaults to 2.2 and says so.
- **"Changed in X" notes:** computed programmatically by comparing each symbol's signature across versions. No LLM is involved.
- **No LLM needed:** the app shows the retrieved symbol, signature, docstring and change note. The index is built offline and committed in `index/`; the app only loads it.

## Run it yourself

""" + F + """
./run_eval.sh                 # rebuilds extraction, chunks, index, benchmark, results.md (about 15 min)
streamlit run app.py          # local app
""" + F + """

## Failure analysis

**Recall misses (version filter, no reranker, the deployed default):**

""" + miss_md + """
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
"""
open("README.md", "w").write(readme)
print(miss_md)
