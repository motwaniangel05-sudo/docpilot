#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f scripts/extract_lib.py || { echo "MISSING scripts/extract_lib.py"; exit 1; }

mk() {
  d="$1"; check="$2"; shift 2
  if [ -x "$d/bin/python" ] && "$d/bin/python" -c "$check" 2>/dev/null; then echo "ok: $d"; return; fi
  rm -rf "$d"; echo ">> installing $d"
  python3.11 -m venv "$d"
  "$d/bin/pip" install --progress-bar off "$@" 2>&1 | tail -2
}

mk .venv-pd20  "import pandas;assert pandas.__version__=='2.0.3'" pandas==2.0.3 "numpy<2"
mk .venv-np126 "import numpy;assert numpy.__version__=='1.26.4'" numpy==1.26.4
mk .venv-np21  "import numpy;assert numpy.__version__=='2.1.3'" numpy==2.1.3
mk .venv-sk13  "import sklearn;assert sklearn.__version__=='1.3.2'" scikit-learn==1.3.2 "numpy<2"
mk .venv-sk15  "import sklearn;assert sklearn.__version__=='1.5.2'" scikit-learn==1.5.2 numpy==2.1.3

.venv-pd20/bin/python  scripts/extract_symbols.py data/symbols_2.0.json
.venv-np126/bin/python scripts/extract_lib.py numpy   data/symbols_numpy_1.26.json
.venv-np21/bin/python  scripts/extract_lib.py numpy   data/symbols_numpy_2.1.json
.venv-sk13/bin/python  scripts/extract_lib.py sklearn data/symbols_sklearn_1.3.json
.venv-sk15/bin/python  scripts/extract_lib.py sklearn data/symbols_sklearn_1.5.json
echo "ALL EXTRACTED"
