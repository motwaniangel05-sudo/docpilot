import importlib
import inspect
import json
import sys

lib, out_path = sys.argv[1], sys.argv[2]
symbols = []


def add(name, obj, kind, version):
    try:
        sig = str(inspect.signature(obj))
    except (TypeError, ValueError):
        sig = "(...)"
    symbols.append({"symbol": name, "kind": kind, "signature": sig,
                    "docstring": inspect.getdoc(obj) or "", "version": version})


if lib == "numpy":
    import numpy as np
    version = ".".join(np.__version__.split(".")[:2])
    for modname, mod in [("np", np), ("np.linalg", np.linalg), ("np.random", np.random), ("np.fft", np.fft)]:
        for attr in dir(mod):
            if attr.startswith("_"):
                continue
            obj = getattr(mod, attr, None)
            if obj is None or inspect.isclass(obj) or inspect.ismodule(obj) or not callable(obj):
                continue
            add(f"{modname}.{attr}", obj, "function", version)
elif lib == "sklearn":
    import sklearn
    version = ".".join(sklearn.__version__.split(".")[:2])
    for m in ["cluster", "decomposition", "ensemble", "linear_model", "metrics", "model_selection",
              "neighbors", "preprocessing", "svm", "tree", "pipeline", "impute", "feature_selection"]:
        mod = importlib.import_module(f"sklearn.{m}")
        for attr in getattr(mod, "__all__", dir(mod)):
            if attr.startswith("_"):
                continue
            obj = getattr(mod, attr, None)
            if inspect.isclass(obj):
                add(f"sklearn.{m}.{attr}", obj, "class", version)
            elif inspect.isfunction(obj):
                add(f"sklearn.{m}.{attr}", obj, "function", version)
else:
    raise SystemExit("unknown lib")

with open(out_path, "w") as f:
    json.dump(symbols, f, indent=2)
print(f"{lib} {version}: saved {len(symbols)} symbols to {out_path}")
