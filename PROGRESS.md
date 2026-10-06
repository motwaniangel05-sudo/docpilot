# PROGRESS

## Day 1 (done)
- Installed Homebrew, VS Code, Git, Python 3.11
- Created ~/docpilot, GitHub repo pushed
- Created .venv-pd15 (pandas 1.5.3) and .venv-pd22 (pandas 2.2.3)
- Extracted symbols to data/symbols_1.5.json and data/symbols_2.2.json

## Day 2 (done)
- Built data/chunks.json (938 chunks, valid_from/valid_until)
- Hand-checked ~30 symbols (append/iteritems/mad removed in 2.2, merge/drop/concat in both)
- Created .venv-app (sentence-transformers, qdrant-client, rank_bm25)
- Built index/ (Qdrant local + bm25.pkl, 14 MB), pushed to GitHub

## Day 3 (done)
- Wrote docpilot/search.py: dense (Qdrant) + BM25 + RRF + version filter + bge-reranker-base
- Tested with scripts/cli_test.py: append excluded for 2.2, present for 1.5, items/iteritems correct
- Known failure (for README): vague queries like "combine two dataframes by rows" miss pd.concat

## Day 4 (done)
- Wrote docpilot/version.py (version detection) and docpilot/changes.py (programmatic "changed in X" notes)
- Wrote app.py (Streamlit) and tested locally
- DEVIATION: Hugging Face Spaces now requires a paid plan for Docker/Gradio, so deployed on Streamlit Community Cloud instead
- Live app: https://docpilot-5ov2htcjpmznaondpjkiqg.streamlit.app

## Next: Day 5 - auto-generate benchmark, run evaluation and ablations, produce results.md
