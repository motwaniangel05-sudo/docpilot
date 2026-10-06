import streamlit as st

from docpilot.changes import Changes
from docpilot.search import Searcher
from docpilot.version import detect_version

st.set_page_config(page_title="DocPilot", page_icon="🐼", layout="wide")


@st.cache_resource
def load():
    s = Searcher(use_reranker=True, device="cpu")
    return s, Changes(s.chunks)


searcher, changes = load()

st.title("🐼 DocPilot")
st.caption("Version-aware pandas assistant (pandas 1.5 vs 2.2). Free Spaces sleep when idle, so the first load can be slow.")

question = st.text_area(
    "Ask a pandas question (mention your version, or paste your requirements.txt)",
    placeholder="how do I append a row to a dataframe in pandas 2.2?",
    height=100,
)

if st.button("Search") and question.strip():
    version, msg = detect_version(question)
    st.info(msg)

    with st.spinner("Searching..."):
        results = searcher.search(question, version=version, k=5)
        wide = searcher.search(question, version=None, k=10, rerank=False)

    for w in changes.warnings(wide, version):
        st.warning(w)

    for r in results:
        with st.container(border=True):
            st.subheader(f"{r['symbol']}  (pandas {r['version']})")
            st.code(f"{r['symbol']}{r['signature']}", language="python")
            note = changes.note(r["symbol"], version)
            if note:
                st.warning(note)
            with st.expander("Docstring"):
                st.text(r["docstring"])
