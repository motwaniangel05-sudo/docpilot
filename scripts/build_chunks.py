import json

with open("data/symbols_1.5.json") as f:
    s15 = {x["symbol"]: x for x in json.load(f)}
with open("data/symbols_2.2.json") as f:
    s22 = {x["symbol"]: x for x in json.load(f)}

chunks = []
stats = {"both": 0, "removed": 0, "added": 0, "sig_changed": 0}

for name in sorted(set(s15) | set(s22)):
    a, b = s15.get(name), s22.get(name)
    if a and b:
        valid_from, valid_until = "1.5", "2.2"
        stats["both"] += 1
        if a["signature"] != b["signature"]:
            stats["sig_changed"] += 1
    elif a:
        valid_from, valid_until = "1.5", "1.5"
        stats["removed"] += 1
    else:
        valid_from, valid_until = "2.2", "2.2"
        stats["added"] += 1

    for ver, sym in (("1.5", a), ("2.2", b)):
        if sym is None:
            continue
        text = f"{sym['symbol']}{sym['signature']}\n{sym['docstring']}"
        chunks.append({
            "symbol": sym["symbol"],
            "kind": sym["kind"],
            "version": ver,
            "signature": sym["signature"],
            "docstring": sym["docstring"],
            "text": text,
            "valid_from": valid_from,
            "valid_until": valid_until,
        })

with open("data/chunks.json", "w") as f:
    json.dump(chunks, f, indent=2)

print(f"chunks: {len(chunks)}")
print(stats)
