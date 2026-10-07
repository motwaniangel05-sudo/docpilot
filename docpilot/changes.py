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


def vkey(v):
    return tuple(int(x) for x in v.split("."))


class Changes:
    def __init__(self, chunks):
        self.by_key = {(c["library"], c["symbol"], c["version"]): c for c in chunks}
        self.versions = {}
        for c in chunks:
            self.versions.setdefault(c["library"], set()).add(c["version"])

    def _present(self, library, symbol):
        return sorted((v for v in self.versions[library] if (library, symbol, v) in self.by_key), key=vkey)

    def exists(self, symbol, version, library="pandas"):
        return (library, symbol, version) in self.by_key

    def note(self, symbol, version, library="pandas"):
        present = self._present(library, symbol)
        if not present:
            return None
        if version not in present:
            if vkey(version) < vkey(present[0]):
                return f"NOT AVAILABLE: {symbol} was added in {library} {present[0]} and does not exist in {version}."
            if vkey(version) > vkey(present[-1]):
                return f"REMOVED: {symbol} exists in {library} {present[-1]} but not in {version}."
            return f"NOT AVAILABLE: {symbol} does not exist in {library} {version} (present in {', '.join(present)})."
        allv = sorted(self.versions[library], key=vkey)
        gone = [v for v in allv if vkey(v) > vkey(version) and v not in present]
        if gone:
            return f"NOTE: {symbol} exists in {library} {version} but is gone in {gone[0]}. Avoid it in new code."
        mine = self.by_key[(library, symbol, version)]["signature"]
        others = [o for o in present if o != version and self.by_key[(library, symbol, o)]["signature"] != mine]
        if others:
            o = min(others, key=lambda x: abs(allv.index(x) - allv.index(version)))
            pa = _params(mine)
            pb = _params(self.by_key[(library, symbol, o)]["signature"])
            if pa is not None and pb is not None and pa != pb:
                parts = []
                if pb - pa:
                    parts.append("added " + ", ".join(sorted(pb - pa)))
                if pa - pb:
                    parts.append("removed " + ", ".join(sorted(pa - pb)))
                return f"CHANGED in {library} {o}: parameters {'; '.join(parts)}."
            return f"CHANGED in {library} {o}: signature or type hints differ from {version}."
        return None

    def warnings(self, results_any_version, version, library="pandas"):
        out, seen = [], set()
        for r in results_any_version:
            sym = r["symbol"]
            if r.get("library", library) != library or sym in seen or self.exists(sym, version, library):
                continue
            seen.add(sym)
            out.append(self.note(sym, version, library))
        return [w for w in out if w]
