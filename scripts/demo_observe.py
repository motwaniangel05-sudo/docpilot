import json
import sys

sys.path.insert(0, ".")
from docpilot.observe import ObservedSearcher
from docpilot.version import detect_version

bench = json.load(open("data/benchmark.json"))
s = ObservedSearcher()
for item in bench[:10] + bench[:10]:
    ver, _ = detect_version(item["q"])
    s.search(item["q"], version=ver)
print("ran 20 queries (10 unique, 10 repeated)")
