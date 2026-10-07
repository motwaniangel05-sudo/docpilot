import re

SUPPORTED = {"pandas": ["1.5", "2.0", "2.2"], "numpy": ["1.26", "2.1"], "sklearn": ["1.3", "1.5"]}
ALIASES = {"pandas": "pandas", "numpy": "numpy", "scikit-learn": "sklearn", "scikit_learn": "sklearn", "sklearn": "sklearn"}
NAME = r"(pandas|numpy|scikit[-_]learn|sklearn)"
OP = r"(?:==|>=|<=|~=|=|>|<)?"


def _key(v):
    a, b = v.split(".")
    return (int(a), int(b))


def _nearest(lib, found):
    """Largest supported version <= found, else the smallest supported."""
    vs = SUPPORTED[lib]
    below = [v for v in vs if _key(v) <= _key(found)]
    return (max(below, key=_key) if below else min(vs, key=_key))


def detect_target(text, default_library="pandas"):
    """Return (library, version, message)."""
    m = re.search(NAME + r"\s*" + OP + r"\s*v?(\d+)\.(\d+)", text, re.I)
    if m:
        lib = ALIASES[m.group(1).lower()]
        found = f"{m.group(2)}.{m.group(3)}"
    else:
        low = text.lower()
        if re.search(r"scikit[-_]learn|sklearn", low):
            lib = "sklearn"
        elif re.search(r"numpy|\bnp\.", low):
            lib = "numpy"
        elif re.search(r"pandas|\bpd\.|dataframe", low):
            lib = "pandas"
        else:
            lib = default_library
        m2 = re.search(r"(?:version|v)\s*(\d+)\.(\d+)", text, re.I) or re.search(r"(?<![\d.])(\d+)\.(\d+)(?![\d])", text)
        found = f"{m2.group(1)}.{m2.group(2)}" if m2 else None
    if found is None:
        v = max(SUPPORTED[lib], key=_key)
        return lib, v, f"No {lib} version found, so I assumed {lib} {v}."
    v = _nearest(lib, found)
    if v == found:
        return lib, v, f"Detected {lib} {v}."
    return lib, v, f"Detected {lib} {found}; using the closest indexed version, {v}."
