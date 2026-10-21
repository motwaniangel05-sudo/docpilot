import json
r = json.load(open("data/checker_eval.json"))
s, n = r["strict"], r["name"]

results = f"""

## P1: Code checker (static, AST-based)

Parses a pasted Python snippet with Python's `ast` module (the code is never executed) and flags calls to pandas APIs that were removed or deprecated in the chosen version (1.5, 2.0 or 2.2), with the replacement and the version where it changed.

Rules (`data/api_rules.json`, 29 rules): 12 removed APIs found by diffing the symbol JSONs of 1.5 and 2.0, and 17 deprecated APIs parsed from `.. deprecated::` docstring directives (symbol-level only; parameter-level deprecations are ignored). Replacements for removed APIs were added by hand from the pandas 2.0 whatsnew and are marked as manual in the file. Some deprecated replacements were also fixed by hand.

Evaluation on a hand-written set of {r['snippets']} snippets ({r['expected_findings']} expected findings), `data/checker_testset.json`, script `scripts/eval_checker.py`:

| Scoring | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| Strict (line and full symbol, e.g. `Series.mad` is not `DataFrame.mad`) | {s['tp']} | {s['fp']} | {s['fn']} | {s['precision']*100:.1f}% | {s['recall']*100:.1f}% |
| Name-level (line and method name) | {n['tp']} | {n['fp']} | {n['fn']} | {n['precision']*100:.1f}% | {n['recall']*100:.1f}% |

Snippets matched exactly: {r['exact_match_snippets']}/{r['snippets']}. 20 unit tests in `tests/test_checker.py` pass.

Failures (reported as measured):
- 1 false alarm: `iteritems` is flagged by name, so a plain Python 2 `dict.iteritems()` is flagged (medium confidence).
- 1 wrong label: `s2.mad()` on a Series obtained from `s.append(...)` was reported as `DataFrame.mad` instead of `Series.mad`.
- 4 misses: `self.df` attributes, `from pandas import read_gbq`, a DataFrame returned from a user function, and a `groupby` loop variable. The checker tracks only simple assignments from `pd.*` calls and variable names like `df`, `ser`.

Limitations: the test set was written by the same person who built the checker, so it is not independent and the numbers are likely optimistic. It checks only the 29 APIs in the rules file (only symbols in DocPilot's index), not every pandas change. Detection is name-based with heuristics, not type inference.
"""

readme = f"""

## Code checker (P1)

New tab in the app: paste a Python snippet, choose pandas 1.5, 2.0 or 2.2, and DocPilot lists calls that were removed or deprecated in that version, with line number, replacement and the version of the change. It uses Python's `ast` module and never runs your code.

- Rules: `data/api_rules.json` (29 APIs: 12 removed, 17 deprecated), built by `scripts/build_rules.py` from the symbol files and docstring deprecation notes, with hand-added replacements from the pandas whatsnew.
- Tests: `pytest tests/test_checker.py` (20 tests).
- Evaluation (`python scripts/eval_checker.py`, 40 hand-written snippets): strict precision {s['precision']*100:.1f}% / recall {s['recall']*100:.1f}%; name-level precision {n['precision']*100:.1f}% / recall {n['recall']*100:.1f}%.
- Known limits: misses `self.df`, `from pandas import ...` and values returned from functions; flags `iteritems` on plain dicts. The test set is self-written, so treat the numbers as an upper bound.
"""
open("results.md", "a").write(results)
open("README.md", "a").write(readme)
print("appended to results.md and README.md")
