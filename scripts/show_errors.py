import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "ai_systems.json").read_text())
ex = json.loads((ROOT / "data" / "ai_answer_exec.json").read_text())
FENCE = re.compile(r"```(?:python|py)?\n(.*?)```", re.S)

for sysname in ("plain", "full"):
    for r in ex[sysname]["results"]:
        if r["category"] != "real_error":
            continue
        code = FENCE.findall(data[r["id"]][sysname]["answer"])[r["block"]]
        print("=====", sysname, r["id"], "block", r["block"])
        print("Q:", data[r["id"]]["question"][:100])
        print("ERR:", r["message"][:110])
        print("\n".join(code.strip().split("\n")[:7]))
