import sys

sys.path.insert(0, ".")
from docpilot.abstain import THRESHOLD, scored_search, should_abstain
from docpilot.search import Searcher

s = Searcher(use_reranker=True, device="cpu")
tests = [
    ("In pandas 1.5, how do I append rows to a dataframe", "1.5", False),
    ("In pandas 2.2, how do I compute the mean of a Series", "2.2", False),
    ("In pandas 2.2, how do I bake sourdough bread at home", "2.2", True),
    ("In pandas 1.5, how to center a div in CSS", "1.5", True),
]
ok = 0
for q, v, expect in tests:
    score, res = scored_search(s, q, v)
    got = should_abstain(score)
    ok += got == expect
    print(f"score={score:.3f} abstain={got} expected={expect} top1={res[0]['symbol']} | {q}")
print(f"threshold={THRESHOLD}  {ok}/{len(tests)} as expected")
