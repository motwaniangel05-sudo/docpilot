import json
from collections import defaultdict

LIBS = {
    "pandas": [("1.5", "data/symbols_1.5.json"), ("2.0", "data/symbols_2.0.json"), ("2.2", "data/symbols_2.2.json")],
    "numpy": [("1.26", "data/symbols_numpy_1.26.json"), ("2.1", "data/symbols_numpy_2.1.json")],
    "sklearn": [("1.3", "data/symbols_sklearn_1.3.json"), ("1.5", "data/symbols_sklearn_1.5.json")],
}


def vkey(v):
    return tuple(int(x) for x in v.split("."))


chunks = []
for lib, versions in LIBS.items():
    order = [v for v, _ in versions]
    per = defaultdict(dict)  # symbol -> {version: record}
    for ver, path in versions:
        for s in json.load(open(path)):
            per[s["symbol"]][ver] = s
    n_before = len(chunks)
    for sym in sorted(per):
        present = sorted(per[sym], key=vkey)
        vf, vu = present[0], present[-1]
        for ver in present:
            s = per[sym][ver]
            chunks.append({
                "library": lib,
                "symbol": sym,
                "kind": s["kind"],
                "version": ver,
                "signature": s["signature"],
                "docstring": s["docstring"],
                "text": f"{sym}{s['signature']}\n{s['docstring']}",
                "valid_from": vf,
                "valid_until": vu,
                "versions": present,
            })
    print(f"{lib}: versions={order} symbols={len(per)} chunks={len(chunks) - n_before}")

json.dump(chunks, open("data/chunks.json", "w"), indent=2)
print("total chunks:", len(chunks))
