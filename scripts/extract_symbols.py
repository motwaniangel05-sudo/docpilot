import inspect
import json
import sys
import pandas as pd

version = pd.__version__
major_minor = ".".join(version.split(".")[:2])
out_path = sys.argv[1]

symbols = []


def add(name, obj, kind):
    try:
        sig = str(inspect.signature(obj))
    except (TypeError, ValueError):
        sig = "(...)"
    doc = inspect.getdoc(obj) or ""
    symbols.append({
        "symbol": name,
        "kind": kind,
        "signature": sig,
        "docstring": doc,
        "version": major_minor,
    })


for cls_name, cls in [("DataFrame", pd.DataFrame), ("Series", pd.Series)]:
    for attr in dir(cls):
        if attr.startswith("_"):
            continue
        try:
            obj = inspect.getattr_static(cls, attr)
            real = getattr(cls, attr)
        except Exception:
            continue
        if isinstance(obj, property) or inspect.isroutine(real):
            kind = "property" if isinstance(obj, property) else "method"
            add(f"{cls_name}.{attr}", real if kind == "method" else obj, kind)

for attr in dir(pd):
    if attr.startswith("_"):
        continue
    obj = getattr(pd, attr, None)
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        add(f"pd.{attr}", obj, "function")

with open(out_path, "w") as f:
    json.dump(symbols, f, indent=2)

print(f"pandas {version}: saved {len(symbols)} symbols to {out_path}")
