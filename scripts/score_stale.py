import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from docpilot.checker import check_code

data = json.loads((ROOT / "data" / "ai_systems.json").read_text())
FENCE = re.compile(r"```(?:python|py)?\n(.*?)```", re.S)


def blocks(text):
    b = FENCE.findall(text)
    return b


def findings(code):
    try:
        res = check_code(code, "2.2")
    except Exception:
        return None
    if isinstance(res, dict):
        res = res.get("findings") or res.get("issues") or []
    return list(res)


printed_type = False
out = {}
for sysname in ("plain", "full"):
    with_code = flagged = unparsable = 0
    rows = []
    for i, d in data.items():
        bs = blocks(d[sysname]["answer"])
        if not bs:
            continue
        with_code += 1
        allf = []
        for b in bs:
            f = findings(b)
            if f is None:
                unparsable += 1
                continue
            allf += f
        if allf:
            flagged += 1
            rows.append((i, [str(x)[:90] for x in allf[:2]]))
    out[sysname] = {"answers": len(data), "with_code": with_code,
                    "flagged_stale": flagged, "unparsable_blocks": unparsable,
                    "flagged_ids": [r[0] for r in rows]}
    print("===", sysname, "===")
    print(out[sysname]["answers"], "answers |", with_code, "with code |", flagged, "flagged stale |", unparsable, "blocks could not be parsed")
    for i, f in rows:
        print(" ", i, f)
json.dump(out, open(ROOT / "data" / "ai_stale.json", "w"), indent=1)
