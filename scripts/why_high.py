import ast, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from docpilot.checker import _aliases, _known_pandas, _root, NAME_HINT

d = json.loads((ROOT / "data" / "repo_scan.json").read_text())
for name, o in d.items():
    print("=====", name)
    for r in o["sample"]:
        if r["confidence"] != "high":
            continue
        src = (Path("/tmp/repos") / name / r["file"]).read_text(errors="replace")
        lines = src.split("\n")
        tree = ast.parse(src)
        pd_names, attr = None, r["symbol"].split(".")[-1]
        pd_names = _aliases(tree)
        known = _known_pandas(tree, pd_names)
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.lineno == r["line"] and n.attr == attr:
                root = _root(n.value)
                why = ("pd_name" if root in pd_names else "known" if root in known
                       else "name_hint" if root and NAME_HINT.match(root) else "qualified/other")
                asg = [f"{i + 1}: {l.strip()[:60]}" for i, l in enumerate(lines)
                       if root and re.match(rf"\s*{re.escape(root)}\s*=", l)][:2]
                print(f"{r['file'].split('/')[-1]}:{r['line']} {attr} root={root} why={why} assigns={asg}")
                break
