import ast, collections, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "repo_scan.json").read_text())
for name, o in d.items():
    print("=====", name)
    for r in o["sample"]:
        lines = (Path("/tmp/repos") / name / r["file"]).read_text(errors="replace").split("\n")
        print(f"{r['file'].split('/')[-1]}:{r['line']} [{r['symbol']} {r['confidence']}] {lines[r['line'] - 1].strip()[:110]}")

print("===== xarray parse errors (first 3 + reasons)")
reasons, shown = collections.Counter(), 0
for p in sorted((Path("/tmp/repos") / "xarray").rglob("*.py")):
    try:
        ast.parse(p.read_text(errors="replace"))
    except SyntaxError as e:
        reasons[e.msg[:60]] += 1
        if shown < 3:
            shown += 1
            print(p.name, e.lineno, e.msg)
print(reasons.most_common(4))
