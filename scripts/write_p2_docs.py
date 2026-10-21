import json
n = json.load(open("data/faithfulness_normalized.json"))
o = json.load(open("data/faithfulness.json"))
bl = n["by_lib"]
results = f"""

## P2: Cited answers (Groq gpt-oss-20b, retrieved chunks only)

The app writes a short answer from the top 3 retrieved chunks (version-filtered, no reranker) and cites each symbol as `[Symbol | library version]`. If the key is missing or the API fails, the app falls back to a one-line extractive answer with a citation.

Faithfulness script: `scripts/eval_faithfulness.py` (generation, cached) and `scripts/rescore_faithfulness.py` (scoring). Sample: {o['sampled']} questions from the 150-question multi-library benchmark (20 per library, up to 6 traps each, seed 42). {o['abstained']} answers said "Cannot confirm", leaving {n['answered']} answered. An answer is faithful if every cited symbol was retrieved and valid at the chosen version, and every other API it names was among the retrieved chunks.

| Metric | Value |
|---|---|
| First scoring, exact name match (unnormalized) | {o['faithful']}/{o['answered']} = {o['faithfulness_rate']*100:.1f}% |
| Normalized (short names match prefixed symbols, generic names ignored) | {n['faithful_normalized']}/{n['answered']} = {n['faithfulness_rate_normalized']*100:.1f}% |
| Normalized, and no chunk-number citation format errors | {n['faithful_and_no_format_error']}/{n['answered']} = {n['rate_incl_format_errors']*100:.1f}% |
| Trap questions answered / faithful | {n['trap_answered']} / {n['trap_faithful']} |
| By library (faithful/answered) | pandas {bl['pandas'][0]}/{bl['pandas'][1]}, numpy {bl['numpy'][0]}/{bl['numpy'][1]}, sklearn {bl['sklearn'][0]}/{bl['sklearn'][1]} |
| Answers with at least one citation | {o['with_citation_rate']*100:.1f}% |

Why two numbers: the first scoring compared `trapz` with the stored name `np.trapz`, and `AgglomerativeClustering` with `sklearn.cluster.AgglomerativeClustering`, so it flagged correct answers. I fixed the matcher after seeing this. The ignored generic names ({", ".join(n['generic_names_ignored'])}) were chosen by me after viewing the violations, so the normalized rate is tuned on the same sample.

Remaining failures: one real hallucination (cited `DataFrame.map` on a NumPy std question); 3 answers cited chunk numbers (`[1 | ...]`) instead of symbols.

Limitations: 60 questions, one run, temperature 0; questions are built from docstring summaries, so they are easier than real ones; the checker verifies named symbols, not whether the explanation is correct; {100 - o['with_citation_rate']*100:.1f}% of answers had no citation at all.
"""
readme = f"""

## Cited answers (P2)

Search results now come with a short LLM answer written only from the top 3 retrieved chunks, with `[Symbol | library version]` citations. The key is read from the Streamlit secret `GROQ_API_KEY` (never in the repo); without it the app shows an extractive one-line answer and keeps working.

- Faithfulness (60-question sample, {n['answered']} answered): {n['faithful_normalized']}/{n['answered']} = {n['faithfulness_rate_normalized']*100:.1f}% normalized; {n['rate_incl_format_errors']*100:.1f}% when chunk-number citations also count as errors; {o['faithfulness_rate']*100:.1f}% with the first, strict name matching (which wrongly flagged short vs prefixed names). Details in `results.md`.
- Limits: tuned scoring on the same sample, small sample, 1 real hallucination found.
"""
open("results.md", "a").write(results)
open("README.md", "a").write(readme)
print("appended")
