import os
import subprocess
import sys
import tempfile
import textwrap

from docpilot.safety import exec_allowed

VENVS = {"1.5": ".venv-pd15", "2.0": ".venv-pd22", "2.2": ".venv-pd22"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PRELUDE = '''import warnings, json, sys
warnings.simplefilter("always")
import pandas as pd
import numpy as np
df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0], "c": ["x", "y", "z"]})
s = pd.Series([1, 2, 3], name="a")
_caught = []
_ctx = warnings.catch_warnings(record=True)
_caught = _ctx.__enter__()
warnings.simplefilter("always")
'''

EPILOGUE = '''
_ctx.__exit__(None, None, None)
_w = [f"{w.category.__name__}: {str(w.message)[:150]}" for w in _caught
      if issubclass(w.category, (DeprecationWarning, FutureWarning, PendingDeprecationWarning))]
print("__WARN__" + json.dumps(_w))
'''


def run_snippet(code, version, timeout=10):
    if not exec_allowed():
        return {"status": "disabled", "detail": "execution disabled (set DOCPILOT_ALLOW_EXEC=1 locally)", "warnings": []}
    py = os.path.join(ROOT, VENVS[version], "bin", "python")
    if not os.path.exists(py):
        return {"status": "error", "detail": f"missing interpreter {py}", "warnings": []}
    src = PRELUDE + "\n" + textwrap.dedent(code) + "\n" + EPILOGUE
    env = {"PATH": "/usr/bin:/bin", "HOME": "", "OMP_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    with tempfile.TemporaryDirectory(prefix="docpilot_run_") as tmp:
        f = os.path.join(tmp, "snippet.py")
        open(f, "w").write(src)
        try:
            p = subprocess.run([py, f], cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "detail": f"exceeded {timeout}s", "warnings": []}
    warns = []
    for line in p.stdout.splitlines():
        if line.startswith("__WARN__"):
            import json
            warns = json.loads(line[8:])
    if p.returncode != 0:
        last = (p.stderr.strip().splitlines() or ["unknown error"])[-1][:200]
        return {"status": "error", "detail": last, "warnings": warns}
    if warns:
        return {"status": "warning", "detail": warns[0], "warnings": warns}
    return {"status": "ok", "detail": "", "warnings": []}
