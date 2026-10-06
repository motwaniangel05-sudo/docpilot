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

## Next: Day 3 - BM25 + dense search, RRF, version filter, reranker, CLI test