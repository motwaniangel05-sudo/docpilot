import json
import time
from pathlib import Path

import streamlit as st
from sentence_transformers import CrossEncoder

from docpilot.abstain import MESSAGE, THRESHOLD, scored_search, should_abstain
from docpilot.changes import Changes
from docpilot.checker import SUPPORTED as CHECK_VERSIONS, check_code, load_rules
from docpilot.answer import generate_answer
from docpilot.detect import SUPPORTED, detect_target
from docpilot.observe import ObservedSearcher, _logger

st.set_page_config(page_title="DocPilot", page_icon="🐼", layout="wide")
N_RULES = len(json.load(open("data/api_rules.json")))


def get_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None


@st.cache_data(max_entries=128, show_spinner=False)
def cached_answer(question, chunks, library, version, _key):
    return generate_answer(question, chunks, library, version, api_key=_key)

EXAMPLES = [
    "how do I append a row to a dataframe in pandas 2.2?",
    "how do I append a row in pandas 1.5",
    "numpy 2.1 product of array elements",
    "scikit-learn 1.3 random forest classifier",
    "pandas==1.5.3\nhow do I compute mean absolute deviation",
]
CHOICES = ["Auto-detect"] + [f"{lib} {v}" for lib, vs in SUPPORTED.items() for v in vs]


@st.cache_resource
def load():
    s = ObservedSearcher(use_reranker=False, device="cpu")
    return s, Changes([dict(c, version=v) for c in s.inner.chunks for v in c['applies']])


@st.cache_resource
def load_reranker():
    return CrossEncoder("BAAI/bge-reranker-base", device="cpu")


@st.cache_data(max_entries=256)
def cached_scored(_inner, query, version, library):
    return scored_search(_inner, query, version, library=library)


def set_q(text):
    st.session_state.q = text


searcher, changes = load()
st.session_state.setdefault("q", "")

with st.sidebar:
    st.header("Settings")
    override = st.selectbox("Library and version", CHOICES)
    use_abstain = st.checkbox(
        "Abstain when unsure (opt-in: loads the reranker, about 1.4 GB RAM, about 6 s)", value=False,
        help=f"If the reranker confidence is below {THRESHOLD}, DocPilot says it cannot confirm an answer.",
    )
    use_rr = st.checkbox("Use reranker for ranking (slower, about 6 s per query)", value=False)
    st.caption("Libraries: pandas (1.5, 2.0, 2.2), NumPy (1.26, 2.1), scikit-learn (1.3, 1.5).")
    st.caption("Search is hybrid: BM25 + dense (bge-small) fused with RRF, filtered to your library and version.")
    st.caption("Repeated queries are served from a cache. Cost per query: $0.00 (local models, free hosting).")
    st.caption("Free apps sleep when idle. The first load after sleeping can take a minute or two.")

st.title("🐼 DocPilot")
st.caption("Version-aware API assistant for pandas, NumPy and scikit-learn. Notes like REMOVED or CHANGED are computed by comparing the real API of each version, not by an LLM.")

tab_search, tab_check = st.tabs(["Search docs", "Code checker"])

with tab_search:
    st.write("Try an example:")
    cols = st.columns(len(EXAMPLES))
    for col, ex in zip(cols, EXAMPLES):
        col.button(ex.replace("\n", " ")[:34] + "...", on_click=set_q, args=(ex,), use_container_width=True)

    question = st.text_area(
        "Ask a question (mention library and version, or paste your requirements.txt)",
        key="q",
        height=110,
    )

    if st.button("Search", type="primary") and question.strip():
        if override == "Auto-detect":
            library, version, msg = detect_target(question)
            st.info(msg)
        else:
            library, version = override.split()
            st.info(f"Using {library} {version} (selected in the sidebar).")

        if (use_rr or use_abstain) and searcher.inner.reranker is None:
            with st.spinner("Loading reranker (first time only)..."):
                searcher.inner.reranker = load_reranker()

        t0 = time.perf_counter()
        abstained, score = False, None
        if use_abstain:
            score, results = cached_scored(searcher.inner, question, version, library)
            abstained = should_abstain(score)
            _logger.info(json.dumps({"query": question, "library": library, "version": version,
                                     "abstain": abstained, "score": round(score, 4), "cost_usd": 0.0}))
        else:
            results = searcher.search(question, version=version, k=5, rerank=use_rr, library=library)
        wide = searcher.inner.search(question, version=None, k=10, rerank=False, library=library)
        ms = (time.perf_counter() - t0) * 1000

        for w in changes.warnings(wide, version, library):
            st.warning(w)

        if abstained:
            st.error(f"{MESSAGE} ({library} {version}; confidence {score:.3f} is below the threshold {THRESHOLD}.)")
            with st.expander("Closest matches (low confidence)"):
                for r in results:
                    st.write(f"- {r['symbol']}{r['signature']}")
        else:
            st.caption(f"Top {len(results)} results for {library} {version} in {ms:.0f} ms")
        with st.spinner("Writing a cited answer from the retrieved docs..."):
            ans = cached_answer(question, [dict(r) for r in results[:3]], library, version, get_key())
        with st.container(border=True):
            st.markdown("**Answer (generated only from the retrieved docs)**")
            st.markdown(ans["answer"])
            if ans["used_llm"]:
                st.caption("Generated by an LLM (Groq, gpt-oss-20b) from the top 3 retrieved chunks. Citations are checked by a faithfulness script (see results.md).")
            else:
                st.caption(f"No LLM answer ({ans['error']}). Showing the top result's summary instead.")
            for i, r in enumerate(results):
                with st.container(border=True):
                    st.subheader(f"{i + 1}. {r['symbol']}")
                    st.code(f"{r['symbol']}{r['signature']}", language="python")
                    note = changes.note(r["symbol"], version, library)
                    if note:
                        st.warning(note)
                    with st.expander("Docstring"):
                        st.text(r["docstring"])


with tab_check:
    st.subheader("Code checker")
    st.caption("Paste a Python snippet and pick a pandas version. DocPilot parses it with Python's ast module (the code is never run) and flags calls that were removed or deprecated in that version.")
    cv = st.selectbox("pandas version", CHECK_VERSIONS, index=len(CHECK_VERSIONS) - 1, key="check_version")
    sample = (
        "import pandas as pd\n"
        "df = pd.DataFrame({'a': [1, 2]})\n"
        "df = df.append({'a': 3}, ignore_index=True)\n"
        "for k, v in df.iteritems():\n"
        "    print(k)\n"
        "print(df.applymap(str))\n"
    )
    code = st.text_area("Python code", value=sample, height=260, key="check_code")
    if st.button("Check code", type="primary", key="check_btn"):
        out = check_code(code, cv)
        if out["error"]:
            st.error(out["error"])
        elif not out["findings"]:
            st.success(f"No removed or deprecated pandas APIs found for pandas {cv} (among the {N_RULES} APIs DocPilot knows).")
        else:
            n_rem = sum(f["status"] == "removed" for f in out["findings"])
            st.write(f"**{len(out['findings'])} finding(s)** for pandas {cv}: {n_rem} removed, {len(out['findings']) - n_rem} deprecated.")
            for f in out["findings"]:
                msg = f"Line {f['line']}: {f['message']} (confidence: {f['confidence']})"
                (st.error if f["status"] == "removed" else st.warning)(msg)
        st.caption("Limits: checks only the APIs in DocPilot's rules file and uses name-based heuristics for method calls, so it can miss calls on unusual variable names. Medium confidence means the receiver was not clearly a pandas object.")


res = Path("results.md")
if res.exists():
    with st.expander("Evaluation results (stale-answer rate, recall@5, latency)"):
        st.markdown(res.read_text())
    png = Path("data/risk_coverage.png")
    if png.exists():
        with st.expander("Risk-coverage curve (abstention)"):
            st.image(str(png))

exec_file = Path("data/exec_results.json")
if exec_file.exists():
    with st.expander("Execution check: did the answers' code actually run? (saved results)"):
        ex = json.loads(exec_file.read_text())
        cats = ex.get("categories", {})
        st.write(
            f"{ex['n']} pandas code blocks were run on the pandas version each answer cited. "
            "These are saved results from a local run. This app never runs code."
        )
        st.write(
            f"Ran with no warning: {cats.get('ran_ok', 0)} | "
            f"Ran with a deprecation warning: {cats.get('ran_warning', 0)} | "
            f"Incomplete example (undefined variable): {cats.get('incomplete_snippet', 0)} | "
            f"Needed a date index in my test data: {cats.get('needs_date_index_ok', 0)} | "
            f"Real error: {cats.get('real_error_nonascii_char', 0) + cats.get('real_error', 0)}"
        )
        st.table([
            {"pandas": r["version"], "API": r["symbol"],
             "result": r.get("category", r["status"]), "message": r["message"][:70]}
            for r in ex["results"]
        ])
        st.caption("Raw rate: 8 of 16 ran without error. Adjusted after seeing the failures: 10 of 11 self-contained snippets. Small sample. 'Ran' does not prove the output is correct.")

ai_file = Path("data/ai_results.json")
if ai_file.exists():
    with st.expander("Test on AI-generated questions (saved results)"):
        ai = json.loads(ai_file.read_text())
        s = ai["summary"]
        rs = ai["results"]
        st.warning(
            "ChatGPT wrote these questions and the expected-API labels. They are not from real users. "
            "The labels are only partly checked (10 of 50, all from pandas 1.5 questions)."
        )
        st.write(
            f"{s['n']} usable questions (19 for pandas 1.5, 19 for pandas 2.2). "
            "These are saved results from a local run. This app never runs code for this test."
        )
        st.write(
            f"Recall@5 without the reranker (what this app uses): {s['recall5_symbol_fast_pct']}% | "
            f"with the reranker: {s['recall5_symbol_rerank_pct']}%"
        )
        st.write(
            "Why it is low: 26 of 38 expected APIs have no page in the index "
            "(about 16 are not API pages at all, such as frequency aliases). "
            "When the API is in the index, it was found 12 of 12 times with the reranker."
        )
        st.table([
            {"id": r["id"], "pandas": r["version"], "expected": r["expected_api"][:45],
             "found (no reranker)": "yes" if r["recall5_symbol_fast"] else "no",
             "found (reranker)": "yes" if r["recall5_symbol_rerank"] else "no"}
            for r in rs
        ])
        st.caption("Small sample, AI-generated, labels not fully verified. 'Not found' mostly means the index has no such page, not that ranking failed.")

sys_file = Path("data/ai_systems.json")
fx_file = Path("data/ai_answer_exec_fixed.json")
raw_file = Path("data/ai_answer_exec.json")
if sys_file.exists() and fx_file.exists() and raw_file.exists():
    with st.expander("Three-system comparison on AI-generated questions (saved results)"):
        import statistics
        sysd = json.loads(sys_file.read_text())
        raw_ex = json.loads(raw_file.read_text())
        fx_ex = json.loads(fx_file.read_text())
        n_q = len(sysd)
        n_abst = sum("Cannot confirm" in x["full"]["answer"] for x in sysd.values())

        def lat(k):
            v = sorted(x[k]["seconds"] for x in sysd.values())
            return f"{statistics.median(v):.2f} / {v[int(0.95 * len(v)) - 1]:.2f}"

        def okrate(e, k):
            c = e[k]["counts"]
            return f"{c.get('ok', 0) + c.get('warning', 0)} of {e[k]['blocks']}"

        st.warning(
            "ChatGPT wrote these questions and the expected-API labels. They are not from real users. "
            "Labels are only partly checked. Small sample, one model. Code was run locally, never in this app."
        )
        st.table([
            {"": "Questions answered", "Plain LLM": f"{n_q} of {n_q}", "Retrieval only": f"{n_q} of {n_q}",
             "Full DocPilot": f"{n_q - n_abst} of {n_q} ({n_abst} abstained)"},
            {"": "Ran without error, raw", "Plain LLM": okrate(raw_ex, "plain"), "Retrieval only": "not applicable",
             "Full DocPilot": okrate(raw_ex, "full")},
            {"": "Ran without error, adjusted", "Plain LLM": okrate(fx_ex, "plain"), "Retrieval only": "not applicable",
             "Full DocPilot": okrate(fx_ex, "full")},
            {"": "Median / p95 latency (s)", "Plain LLM": lat("plain"), "Retrieval only": lat("retrieval"),
             "Full DocPilot": lat("full")},
            {"": "Answers judged wrong by reading", "Plain LLM": "at least 9", "Retrieval only": "not applicable",
             "Full DocPilot": "0 found (only a few read)"},
        ])
        st.write(
            "Stale-answer rate did not separate the systems: the checker flagged 2 answers, both were "
            "'before' examples, so both systems score 0. The real difference is abstention: full DocPilot "
            "declined questions whose API is not in the index, while the plain model answered all of them."
        )
        st.caption("Adjusted = test data changed after seeing failures. 'Ran' does not prove the answer is correct. "
                   "9 wrong plain answers is a lower bound.")
