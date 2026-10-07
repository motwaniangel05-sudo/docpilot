import json
import time
from pathlib import Path

import streamlit as st
from sentence_transformers import CrossEncoder

from docpilot.abstain import MESSAGE, THRESHOLD, scored_search, should_abstain
from docpilot.changes import Changes
from docpilot.observe import _logger, ObservedSearcher
from docpilot.version import detect_version

st.set_page_config(page_title="DocPilot", page_icon="🐼", layout="wide")

EXAMPLES = [
    "how do I append a row to a dataframe in pandas 2.2?",
    "how do I append a row in pandas 1.5",
    "iterate over columns as key value pairs",
    "pandas==1.5.3\nhow do I compute mean absolute deviation",
]


@st.cache_resource
def load():
    s = ObservedSearcher(use_reranker=False, device="cpu")
    return s, Changes(s.inner.chunks)


@st.cache_resource
def load_reranker():
    return CrossEncoder("BAAI/bge-reranker-base", device="cpu")


@st.cache_data(max_entries=256)
def cached_scored(_inner, query, version):
    return scored_search(_inner, query, version)


def set_q(text):
    st.session_state.q = text


searcher, changes = load()
st.session_state.setdefault("q", "")

with st.sidebar:
    st.header("Settings")
    override = st.selectbox("pandas version", ["Auto-detect", "1.5", "2.2"])
    use_abstain = st.checkbox(
        "Abstain when unsure (uses reranker, about 6 s)", value=True,
        help=f"If the reranker confidence is below {THRESHOLD}, DocPilot says it cannot confirm an answer.",
    )
    use_rr = st.checkbox("Use reranker for ranking (slower, about 6 s per query)", value=False)
    st.caption("Search is hybrid: BM25 + dense (bge-small) fused with RRF, filtered to your pandas version.")
    st.caption("Repeated queries are served from a cache. Cost per query: $0.00 (local models, free hosting).")
    st.caption("Free apps sleep when idle. The first load after sleeping can take a minute or two.")

st.title("🐼 DocPilot")
st.caption("Version-aware pandas assistant (pandas 1.5 vs 2.2). Notes like REMOVED or CHANGED are computed by comparing the real API of both versions, not by an LLM.")

st.write("Try an example:")
cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES):
    col.button(ex.replace("\n", " ")[:38] + "...", on_click=set_q, args=(ex,), use_container_width=True)

question = st.text_area(
    "Ask a pandas question (mention your version, or paste your requirements.txt)",
    key="q",
    height=110,
)

if st.button("Search", type="primary") and question.strip():
    if override == "Auto-detect":
        version, msg = detect_version(question)
        st.info(msg)
    else:
        version = override
        st.info(f"Using pandas {version} (selected in the sidebar).")

    if (use_rr or use_abstain) and searcher.inner.reranker is None:
        with st.spinner("Loading reranker (first time only)..."):
            searcher.inner.reranker = load_reranker()

    t0 = time.perf_counter()
    abstained, score = False, None
    if use_abstain:
        score, results = cached_scored(searcher.inner, question, version)
        abstained = should_abstain(score)
        _logger.info(json.dumps({"query": question, "version": version, "abstain": abstained,
                                 "score": round(score, 4), "cost_usd": 0.0}))
    else:
        results = searcher.search(question, version=version, k=5, rerank=use_rr)
    wide = searcher.inner.search(question, version=None, k=10, rerank=False)
    ms = (time.perf_counter() - t0) * 1000

    for w in changes.warnings(wide, version):
        st.warning(w)

    if abstained:
        st.error(f"{MESSAGE} (pandas {version}; confidence {score:.3f} is below the threshold {THRESHOLD}.)")
        with st.expander("Closest matches (low confidence)"):
            for r in results:
                st.write(f"- {r['symbol']}{r['signature']}")
    else:
        st.caption(f"Top {len(results)} results for pandas {version} in {ms:.0f} ms")
        for i, r in enumerate(results):
            with st.container(border=True):
                st.subheader(f"{i + 1}. {r['symbol']}")
                st.code(f"{r['symbol']}{r['signature']}", language="python")
                note = changes.note(r["symbol"], version)
                if note:
                    st.warning(note)
                with st.expander("Docstring"):
                    st.text(r["docstring"])

res = Path("results.md")
if res.exists():
    with st.expander("Evaluation results (stale-answer rate, recall@5, latency)"):
        st.markdown(res.read_text())
    png = Path("data/risk_coverage.png")
    if png.exists():
        with st.expander("Risk-coverage curve (abstention)"):
            st.image(str(png))
