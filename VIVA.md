# DocPilot: 10 viva questions

1. **What problem does DocPilot solve?**
Pandas answers change across versions (e.g. `DataFrame.append` was removed in 2.0). Normal search recommends removed APIs. DocPilot filters by the user's version and warns about differences.

2. **What is RAG?**
Retrieval-Augmented Generation: retrieve relevant documents first, then use them to answer. Here the retrieved API docs are the answer, so no LLM is required.

3. **Why one chunk per symbol per version?**
Each API symbol is a natural unit, and keeping a separate chunk per version lets the filter return only what exists in the user's version.

4. **Why hybrid search (BM25 + dense)?**
BM25 matches exact names like `iteritems`. Dense embeddings match meaning like "add a row". Reciprocal Rank Fusion merges both rankings without needing comparable scores.

5. **How does the version filter work?**
Each chunk stores its version. Qdrant filters on that field for dense search, and the BM25 results are filtered the same way, before fusion.

6. **How is the "changed in X" note produced?**
Programmatically: the code compares each symbol's signature in 1.5 and 2.2 and reports removed, added, or changed parameters. No LLM, so it cannot hallucinate.

7. **What are your headline results?**
On 90 auto-generated questions (14 stale-answer traps), the filter cut top-1 stale answers from 57.1% to 0.0% and top-5 from 100% to 0.0%, with recall@5 at 97.4%. Search latency is about 266 ms p50 and 296 ms p95 without the reranker.

8. **Why is the reranker off by default?**
It added about 6.5 s per query and gave no recall gain on this benchmark (97.4% with and without it). It also saves memory on the free host.

9. **What are the limitations?**
Only 14 trap questions qualified, so the sample is small. Questions are built from docstrings, so recall is optimistic. Only 2 versions are indexed. Signature comparison misses behavior changes that don't change the signature.

10. **Why Streamlit Community Cloud instead of Hugging Face Spaces?**
Free Hugging Face accounts could only create Static Spaces at deployment time (Docker and Gradio required a paid plan). Streamlit Community Cloud is free and runs the app unchanged. A Dockerfile is included for self-hosting.
