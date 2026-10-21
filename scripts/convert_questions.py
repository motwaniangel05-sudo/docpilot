import csv, collections, re

rows = list(csv.DictReader(open("data/real_questions.csv", encoding="utf-8-sig")))

def map_version(v):
    v = v.strip().lower()
    if v == "1.5":
        return "1.5"
    if v == "2.0":
        return "2.0"
    if re.fullmatch(r"2\.(1|2|3)( warnings| deprecation)?", v):
        return "2.2"
    return ""

out = []
for r in rows:
    ver = map_version(r["pandas_version_from"])
    api = r["removed_or_changed_api"].strip()
    vague = (not api) or api.lower().startswith("multiple")
    out.append({
        "id": r["id"],
        "question": r["question"].strip(),
        "pandas_version": ver,
        "expected_api": api,
        "source": "chatgpt",
        "url_unverified": r["source_url"].strip(),
        "usable": "yes" if ver and not vague else "no",
    })

with open("data/ai_questions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

use = [o for o in out if o["usable"] == "yes"]
print("total rows:", len(out))
print("usable rows:", len(use))
print("usable by version:", dict(collections.Counter(o["pandas_version"] for o in use)))
print("skipped: no supported version:", sum(1 for o in out if not o["pandas_version"]))
print("skipped: vague API:", sum(1 for o in out if o["pandas_version"] and o["usable"] == "no"))
print()
for o in use[:8]:
    print(o["id"], "|", o["pandas_version"], "|", o["expected_api"][:35], "|", o["question"][:60])
