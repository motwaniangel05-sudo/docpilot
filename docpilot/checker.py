import ast
import json
import os
import re

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "api_rules.json")
SUPPORTED = ["1.5", "2.0", "2.2"]

# method names also used by list / dict / numpy: flag only if receiver looks like pandas
AMBIGUOUS = {"append", "first", "last", "pad", "view", "ravel", "bool", "lookup", "swapaxes"}
NOT_PANDAS_RESULT = {"tolist", "to_list", "to_numpy", "keys", "unique", "split", "join",
                     "values", "index", "columns", "shape", "item", "items"}
NAME_HINT = re.compile(r"^(df|ser|series)\w*$|^\w+_df$")


def vkey(v):
    return tuple(int(x) for x in str(v).split(".")[:2])


def load_rules(path=RULES_PATH):
    by_name, qualified = {}, {}
    for r in json.load(open(path)):
        if r["symbol"].startswith("pd."):
            qualified[r["symbol"][3:]] = r
        else:
            kind, name = r["symbol"].split(".", 1)
            by_name.setdefault(name, {})[kind] = r
    return by_name, qualified


def _root(node):
    while True:
        if isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        else:
            break
    return node.id if isinstance(node, ast.Name) else None


def _aliases(tree):
    pd_names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "pandas":
                    pd_names.add(a.asname or "pandas")
    return pd_names


def _known_pandas(tree, pd_names):
    known = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for a in n.args.posonlyargs + n.args.args + n.args.kwonlyargs:
                if NAME_HINT.match(a.arg):
                    known.add(a.arg)
    for _ in range(3):  # a few passes so chains of assignments propagate
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                v = n.value
                r = _root(v)
                ok = r is not None and (r in pd_names or r in known)
                if ok and isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) \
                        and v.func.attr in NOT_PANDAS_RESULT:
                    ok = False
                if ok and isinstance(v, ast.Attribute):
                    ok = False
                if ok:
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            known.add(t.id)
    return known


SERIES_HINT = re.compile(r"^(s|ser\w*|series\w*)$")


def _series_expr(v, pd_names, known):
    if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "Series" \
            and _root(v.func) in pd_names:
        return True
    if isinstance(v, ast.Subscript) and (_root(v) in known or _root(v) in pd_names) \
            and not isinstance(v.slice, ast.List):
        return True
    return False


def _series_names(tree, pd_names, known):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if _series_expr(n.value, pd_names, known):
                out.add(n.targets[0].id)
    return out


def _is_series(recv, series, pd_names, known):
    if isinstance(recv, ast.Name):
        return recv.id in series or bool(SERIES_HINT.match(recv.id))
    return _series_expr(recv, pd_names, known)


def _looks_pandas(recv, known, pd_names):
    r = _root(recv)
    if r is None:
        return False
    return r in known or r in pd_names or bool(NAME_HINT.match(r))


_CHAIN_SKIP = {"groupby", "resample", "rolling", "expanding", "ewm"}


def _chain_attrs(node):
    out = []
    while True:
        if isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Subscript):
            node = node.value
        else:
            break
    return set(out)


def _assign_index(tree):
    idx = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    idx.setdefault(t.id, []).append((n.lineno, n.value))
    for v in idx.values():
        v.sort(key=lambda x: x[0])
    return idx


_PLAIN = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp, ast.Constant, ast.Tuple)


def _ambiguous_ok(recv, lineno, assigns, pd_names, known):
    """For names like append/first/ravel: is the receiver clearly pandas at this line?"""
    if _chain_attrs(recv) & (_CHAIN_SKIP | NOT_PANDAS_RESULT):
        return False
    if isinstance(recv, ast.Name):
        prior = [v for ln, v in assigns.get(recv.id, []) if ln < lineno]
        if prior:
            v = prior[-1]
            if isinstance(v, _PLAIN) or (_chain_attrs(v) & _CHAIN_SKIP):
                return False
            r = _root(v)
            return r is not None and (r in pd_names or r in known)
    return True


def check_code(code, version, rules=None):
    """Return {"error": str|None, "findings": [...]}. Never executes the code."""
    if version not in SUPPORTED:
        raise ValueError(f"version must be one of {SUPPORTED}")
    by_name, qualified = rules or load_rules()
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": f"SyntaxError line {e.lineno}: {e.msg}", "findings": []}
    pd_names = _aliases(tree)
    known = _known_pandas(tree, pd_names)
    series = _series_names(tree, pd_names, known)
    assigns = _assign_index(tree)
    findings = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Attribute):
            continue
        rule, conf = None, None
        if isinstance(n.value, ast.Name) and n.value.id in pd_names and n.attr in qualified:
            rule, conf = qualified[n.attr], "high"
        elif n.attr in by_name:
            kinds = by_name[n.attr]
            if "Series" in kinds and _is_series(n.value, series, pd_names, known):
                rule = kinds["Series"]
            else:
                rule = kinds.get("DataFrame") or kinds["Series"]
            pandas_like = _looks_pandas(n.value, known, pd_names)
            if n.attr in AMBIGUOUS:
                if pandas_like:
                    conf = "high" if _root(n.value) in known or _root(n.value) in pd_names else "medium"
            else:
                conf = "high" if pandas_like else "medium"
        if rule is None or conf is None:
            continue
        if n.attr in AMBIGUOUS and not _ambiguous_ok(n.value, n.lineno, assigns, pd_names, known):
            continue
        if vkey(version) < vkey(rule["since"]):
            continue
        name = rule["symbol"]
        verb = "was removed" if rule["status"] == "removed" else "is deprecated"
        findings.append({
            "line": n.lineno, "col": n.col_offset, "symbol": name,
            "status": rule["status"], "since": rule["since"],
            "replacement": rule["replacement"], "confidence": conf,
            "message": f"{name} {verb} in pandas {rule['since']}. Use: {rule['replacement']}",
        })
    findings.sort(key=lambda f: (f["line"], f["col"]))
    return {"error": None, "findings": findings}
