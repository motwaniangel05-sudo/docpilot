import os, sys
os.environ["DOCPILOT_ALLOW_EXEC"] = "1"
sys.path.insert(0, ".")
from docpilot.sandbox import run_snippet

cases = [
 ("1.5", "print(df['a'].sum())", "ok"),
 ("1.5", "df2 = df.append({'a': 9, 'b': 1.0, 'c': 'q'}, ignore_index=True)", "warning"),
 ("2.2", "df2 = df.append({'a': 9}, ignore_index=True)", "error"),
 ("2.2", "df.applymap(str)", "warning"),
 ("2.2", "df.map(str)", "ok"),
 ("2.2", "while True: pass", "timeout"),
 ("2.2", "import os; print(len(os.listdir('.')))", "ok"),
]
good = 0
for v, code, want in cases:
    r = run_snippet(code, v, timeout=5)
    flag = "OK " if r["status"] == want else "BAD"
    good += r["status"] == want
    print(f"{flag} pandas {v:4} want={want:8} got={r['status']:8} {r['detail'][:70]}")
print(good, "/", len(cases))
os.environ.pop("DOCPILOT_ALLOW_EXEC")
print("without switch:", run_snippet("print(1)", "2.2")["status"])
