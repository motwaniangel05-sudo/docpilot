import csv, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groq import Groq
from docpilot.delta import DeltaSearcher
from docpilot.answer import generate_answer, extractive, MODEL

client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=30)
PLAIN_SYS = ("You are a pandas assistant. Answer the question in at most 4 sentences, "
             "plus an optional code example of at most 6 lines.")

OUT = ROOT / "data" / "ai_systems.json"
done = json.loads(OUT.read_text()) if OUT.exists() else {}

rows = [r for r in csv.DictReader(open(ROOT / "data" / "ai_questions.csv")) if r["usable"] == "yes"]
s = DeltaSearcher(use_reranker=False)


def plain(q, ver):
    t = time.time()
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=0, max_tokens=1500, reasoning_effort="low",
            messages=[{"role": "system", "content": PLAIN_SYS},
                      {"role": "user", "content": f"pandas {ver}\n\nQuestion: {q}"}])
        a = (r.choices[0].message.content or "").strip()
        if not a:
            raise ValueError("empty reply")
        return {"answer": a, "error": None, "seconds": round(time.time() - t, 2)}
    except Exception as e:
        return {"answer": "", "error": f"{type(e).__name__}: {str(e)[:120]}",
                "seconds": round(time.time() - t, 2)}


for r in rows:
    i, q, ver = r["id"], r["question"], r["pandas_version"]
    d = done.get(i)
    if d and d["plain"]["error"] is None and d["full"]["used_llm"]:
        continue
    t0 = time.time()
    chunks = s.search(q, version=ver, k=5, rerank=False)
    t_search = round(time.time() - t0, 2)
    retr = {"answer": extractive(chunks, "pandas", ver) if chunks else "Cannot confirm from the retrieved docs.",
            "top5": [c["symbol"] for c in chunks], "seconds": t_search}
    t1 = time.time()
    g = generate_answer(q, chunks, "pandas", ver)
    full = dict(g, seconds=round(t_search + time.time() - t1, 2))
    pl = plain(q, ver)
    done[i] = {"id": i, "question": q, "version": ver, "expected_api": r["expected_api"],
               "plain": pl, "retrieval": retr, "full": full}
    OUT.write_text(json.dumps(done, indent=1))
    print(i, ver, "plain", "ok" if pl["error"] is None else "ERR",
          "| full", "ok" if full["used_llm"] else "ERR", "|",
          pl["seconds"], retr["seconds"], full["seconds"])
    time.sleep(2)

n = len(done)
print()
print("questions saved:", n)
print("plain errors:", sum(1 for d in done.values() if d["plain"]["error"]))
print("full errors (fell back to extractive):", sum(1 for d in done.values() if not d["full"]["used_llm"]))
