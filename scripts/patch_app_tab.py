p = "app.py"
lines = open(p).read().split("\n")
src = "\n".join(lines)
assert "tab_check" not in src, "already patched"

start = next(i for i, l in enumerate(lines) if l.startswith('st.write("Try an example:")'))
end = next(i for i, l in enumerate(lines) if l.startswith('res = Path("results.md")'))

block = [("    " + l if l.strip() else l) for l in lines[start:end]]

checker_tab = '''
with tab_check:
    st.subheader("Code checker")
    st.caption("Paste a Python snippet and pick a pandas version. DocPilot parses it with Python's ast module (the code is never run) and flags calls that were removed or deprecated in that version.")
    cv = st.selectbox("pandas version", CHECK_VERSIONS, index=len(CHECK_VERSIONS) - 1, key="check_version")
    sample = (
        "import pandas as pd\\n"
        "df = pd.DataFrame({'a': [1, 2]})\\n"
        "df = df.append({'a': 3}, ignore_index=True)\\n"
        "for k, v in df.iteritems():\\n"
        "    print(k)\\n"
        "print(df.applymap(str))\\n"
    )
    code = st.text_area("Python code", value=sample, height=260, key="check_code")
    if st.button("Check code", type="primary", key="check_btn"):
        out = check_code(code, cv)
        if out["error"]:
            st.error(out["error"])
        elif not out["findings"]:
            st.success(f"No removed or deprecated pandas APIs found for pandas {cv} (among the {N_RULES} APIs DocPilot knows).")
        else:
            n_rem = sum(f["status"] == "removed" for f in out["findings"])
            st.write(f"**{len(out['findings'])} finding(s)** for pandas {cv}: {n_rem} removed, {len(out['findings']) - n_rem} deprecated.")
            for f in out["findings"]:
                msg = f"Line {f['line']}: {f['message']} (confidence: {f['confidence']})"
                (st.error if f["status"] == "removed" else st.warning)(msg)
        st.caption("Limits: checks only the APIs in DocPilot's rules file and uses name-based heuristics for method calls, so it can miss calls on unusual variable names. Medium confidence means the receiver was not clearly a pandas object.")
'''.split("\n")

head = lines[:start]
head += ['tab_search, tab_check = st.tabs(["Search docs", "Code checker"])', "", "with tab_search:"]
new = head + block + checker_tab + [""] + lines[end:]
out = "\n".join(new)

out = out.replace(
    "from docpilot.changes import Changes",
    "from docpilot.changes import Changes\nfrom docpilot.checker import SUPPORTED as CHECK_VERSIONS, check_code, load_rules",
    1,
)
out = out.replace('st.set_page_config(page_title="DocPilot", page_icon="🐼", layout="wide")',
                  'st.set_page_config(page_title="DocPilot", page_icon="🐼", layout="wide")\nN_RULES = len(json.load(open("data/api_rules.json")))', 1)
open(p, "w").write(out)
print("patched")
