import json, os, sys
sys.path.insert(0, ".")
from docpilot.answer import generate_answer

syms = {s["symbol"]: s for s in json.load(open("data/symbols_2.2.json"))}
chunks = [syms["DataFrame.map"], syms["DataFrame.applymap"], syms["DataFrame.drop_duplicates"]]
q = "How do I apply a function to every element of a DataFrame?"
for label, key in [("WITH KEY", os.environ.get("GROQ_API_KEY")), ("NO KEY", "")]:
    if label == "NO KEY":
        os.environ.pop("GROQ_API_KEY", None)
    r = generate_answer(q, chunks, "pandas", "2.2", api_key=key or None)
    print(f"\n== {label}: used_llm={r['used_llm']} error={r['error']}")
    print(r["answer"])
    print("cited:", r["cited"])
