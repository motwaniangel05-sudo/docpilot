import os
import re

MODEL = "openai/gpt-oss-20b"
CITE = re.compile(r"\[([\w.]+) \| ([A-Za-z\-]+) ([\d.]+)\]")

SYSTEM = (
    "You are DocPilot, a documentation assistant. Answer ONLY from the numbered API chunks provided. "
    "Rules: (1) Mention only API symbols that appear in the chunks. (2) After every claim or code line "
    "that uses a symbol, cite it exactly as [Symbol | library version], for example [DataFrame.map | pandas 2.2]. "
    "(3) If the chunks do not contain enough to answer, reply exactly: Cannot confirm from the retrieved docs. "
    "(4) Keep it short: at most 4 sentences plus an optional code example of at most 6 lines. "
    "(5) Never use outside knowledge or other symbols."
)


def build_context(chunks, library, version, max_chars=1200):
    parts = []
    for i, c in enumerate(chunks, 1):
        lib = c.get("library", library)
        ver = c.get("version", version)
        parts.append(f"[{i}] {c['symbol']}{c.get('signature', '')}  (library: {lib}, version: {ver})\n"
                     f"{c.get('docstring', '')[:max_chars]}")
    return "\n\n".join(parts)


def extractive(chunks, library, version):
    c = chunks[0]
    first = next((l.strip() for l in c.get("docstring", "").split("\n") if l.strip()), "")
    return f"{c['symbol']}{c.get('signature', '')}: {first} [{c['symbol']} | {library} {version}]"


def cited(answer):
    return [(s, lib, v) for s, lib, v in CITE.findall(answer)]


def generate_answer(question, chunks, library, version, api_key=None):
    """Never raises. Returns {answer, used_llm, error, cited}."""
    if not chunks:
        return {"answer": "Cannot confirm from the retrieved docs.", "used_llm": False,
                "error": None, "cited": []}
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        a = extractive(chunks, library, version)
        return {"answer": a, "used_llm": False, "error": "no API key (extractive fallback)", "cited": cited(a)}
    try:
        from groq import Groq
        r = Groq(api_key=key, timeout=30).chat.completions.create(
            model=MODEL, temperature=0, max_tokens=1500, reasoning_effort="low",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Library: {library} {version}\n\nChunks:\n"
                                            f"{build_context(chunks, library, version)}\n\nQuestion: {question}"},
            ],
        )
        a = (r.choices[0].message.content or "").strip()
        if not a:
            raise ValueError("empty reply")
        return {"answer": a, "used_llm": True, "error": None, "cited": cited(a)}
    except Exception as e:
        a = extractive(chunks, library, version)
        return {"answer": a, "used_llm": False, "error": f"{type(e).__name__}: {str(e)[:120]}", "cited": cited(a)}
