import ast
import re


def _params(sig):
    s = re.sub(r"<[^>]*>", "None", sig)
    try:
        fn = ast.parse(f"def f{s}: pass").body[0].args
    except SyntaxError:
        return None
    names = [a.arg for a in fn.posonlyargs + fn.args + fn.kwonlyargs]
    if fn.vararg:
        names.append("*" + fn.vararg.arg)
    if fn.kwarg:
        names.append("**" + fn.kwarg.arg)
    return {n for n in names if n != "self"}


class Changes:
    def __init__(self, chunks):
        self.by_key = {(c["symbol"], c["version"]): c for c in chunks}

    def note(self, symbol, version):
        """Programmatic 'changed in X' note for a symbol, seen from the user's version."""
        a = self.by_key.get((symbol, "1.5"))
        b = self.by_key.get((symbol, "2.2"))
        if a and not b:
            if version == "2.2":
                return f"REMOVED: {symbol} exists in pandas 1.5 but was removed in 2.x."
            return f"NOTE: {symbol} exists in 1.5 but is removed in pandas 2.x. Avoid it in new code."
        if b and not a:
            if version == "1.5":
                return f"NOT AVAILABLE: {symbol} was added in pandas 2.x and does not exist in 1.5."
            return f"NOTE: {symbol} is new in pandas 2.x (not in 1.5)."
        if a and b and a["signature"] != b["signature"]:
            pa, pb = _params(a["signature"]), _params(b["signature"])
            if pa is not None and pb is not None and pa != pb:
                added, removed = sorted(pb - pa), sorted(pa - pb)
                parts = []
                if added:
                    parts.append("added " + ", ".join(added))
                if removed:
                    parts.append("removed " + ", ".join(removed))
                return f"CHANGED in 2.x: parameters {'; '.join(parts)}."
            return "CHANGED in 2.x: signature or type hints differ between 1.5 and 2.2."
        return None

    def warnings(self, results_any_version, version):
        """Warn about relevant symbols that do NOT exist in the user's version."""
        out = []
        seen = set()
        for r in results_any_version:
            sym = r["symbol"]
            if sym in seen or (sym, version) in self.by_key:
                continue
            seen.add(sym)
            out.append(self.note(sym, version))
        return [w for w in out if w]
