import sys
sys.path.insert(0, ".")
from docpilot.checker import check_code

code = '''import pandas as pd
import numpy as np
df = pd.DataFrame({"a": [1, 2]})
items = []
items.append(3)
df = df.append({"a": 3}, ignore_index=True)
for k, v in df.iteritems():
    print(k)
arr = np.zeros((2, 3)).swapaxes(0, 1)
s = df["a"]
print(s.is_monotonic, df.applymap(str))
x = pd.read_gbq("select 1")
'''
for v in ["1.5", "2.0", "2.2"]:
    r = check_code(code, v)
    print(f"\n== pandas {v}: {len(r['findings'])} findings")
    for f in r["findings"]:
        print(f"  line {f['line']:2} {f['status']:10} {f['confidence']:6} {f['symbol']}")
print(check_code("df.append(", "2.2")["error"])
