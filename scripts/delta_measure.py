import json
from collections import defaultdict

chunks = json.load(open("data/chunks.json"))
groups = defaultdict(list)
for c in chunks:
    groups[(c["library"], c["symbol"], c["text"])].append(c["version"])

per_lib = defaultdict(lambda: [0, 0])
for (lib, sym, text), vers in groups.items():
    per_lib[lib][0] += len(vers)
    per_lib[lib][1] += 1

naive = len(chunks)
delta = len(groups)
chars_naive = sum(len(c["text"][:2000]) for c in chunks)
chars_delta = sum(len(t[:2000]) for (_, _, t) in groups)
print(f"naive chunks (one per symbol per version): {naive}")
print(f"delta chunks (unique symbol text):         {delta}")
print(f"chunk reduction: {100 * (1 - delta / naive):.1f}%")
print(f"text chars naive={chars_naive:,} delta={chars_delta:,} reduction={100 * (1 - chars_delta / chars_naive):.1f}%")
for lib, (n, d) in per_lib.items():
    print(f"  {lib}: naive={n} delta={d} reduction={100 * (1 - d / n):.1f}%")
