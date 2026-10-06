import sys
sys.path.insert(0, ".")
from docpilot.version import detect_version
from docpilot.changes import Changes
from docpilot.search import Searcher

for t in ["how to append rows in pandas 1.5", "pandas==2.2.3\nnumpy==1.26", "pandas>=1.4.2",
          "drop duplicates on pandas v2.1", "how to merge dataframes"]:
    print(repr(t), "->", detect_version(t))

s = Searcher(use_reranker=False)
ch = Changes(s.chunks)
for sym, v in [("DataFrame.append", "2.2"), ("DataFrame.iteritems", "2.2"),
               ("DataFrame.groupby", "2.2"), ("DataFrame.to_csv", "1.5")]:
    print(sym, v, "->", ch.note(sym, v))
print("WARNINGS:", ch.warnings(s.search("add a row with append", version=None, rerank=False, k=10), "2.2"))
