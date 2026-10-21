import json, re, collections

FENCE = chr(96) * 3
block_re = re.compile(FENCE + r"(?:python|py)?\s*\n(.*?)" + FENCE, re.S)
cite_re = re.compile(r"\[([^\]|]+)\|\s*(pandas|numpy|sklearn)\s*([0-9.]+)\s*\]")

cache = json.load(open("data/answers_cache.json"))
out, skipped = [], collections.Counter()

for idx, rec in cache.items():
    ans = rec.get("answer") or ""
    if not rec.get("used_llm") or rec.get("error") or not ans:
        skipped["no answer"] += 1
        continue
    blocks = block_re.findall(ans)
    if not blocks:
        skipped["no code block"] += 1
        continue
    cites = cite_re.findall(ans)
    if not cites:
        skipped["no citation tag"] += 1
        continue
    symbol, lib, ver = cites[0]
    for code in blocks:
        out.append({"idx": idx, "lib": lib, "version": ver,
                    "symbol": symbol.strip(), "code": code.strip()})

json.dump(out, open("data/exec_blocks.json", "w"), indent=1)
print("answers in cache:", len(cache))
print("code blocks found:", len(out))
print("by lib/version:", dict(collections.Counter((b["lib"], b["version"]) for b in out)))
print("skipped answers:", dict(skipped))
