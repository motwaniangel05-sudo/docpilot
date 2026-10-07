import json
import re

d = json.load(open("data/delta_size.json"))
section = (
    "\n## Delta indexing\n\n"
    "Symbols whose text is identical across versions are stored and embedded once, with the list of versions they apply to "
    "(`applies`); search filters on library and that list (`docpilot/delta.py`, `scripts/build_index_delta.py`).\n\n"
    "| | Naive (one chunk per symbol per version) | Delta |\n|---|---|---|\n"
    f"| Chunks | {d['naive_chunks']} | {d['delta_chunks']} |\n"
    f"| Index size on disk | {d['naive_mb']} MB | {d['delta_mb']} MB |\n\n"
    f"Size reduction: **{d['reduction_pct']}%** (chunks: 10.5%; pandas 16.6%, scikit-learn 11.8%, NumPy 1.1%). "
    "The gain is small because most docstrings change at least slightly between versions, so few chunks are byte-identical. "
    "Stale@1 (0.0%) and recall@5 (98.35%, no reranker, 150 questions) are identical to the naive index. "
    "127/150 top-5 lists are identical; the rest differ in order only. "
    "Limitation: unchanged-text detection is exact string match, with no near-duplicate merging.\n"
)
md = open("results.md").read()
md = re.sub(r"\n## Delta indexing.*?(?=\n## |\Z)", "", md, flags=re.S).rstrip() + "\n" + section
open("results.md", "w").write(md)
print(section)
