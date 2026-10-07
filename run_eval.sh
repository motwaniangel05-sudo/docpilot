#!/usr/bin/env bash
# Reruns everything: venvs, symbol extraction, chunks, index, multi-library benchmark, evaluation -> results.md
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv-pd15 ] || { python3.11 -m venv .venv-pd15 && .venv-pd15/bin/pip install -q pandas==1.5.3 "numpy<2"; }
[ -d .venv-pd22 ] || { python3.11 -m venv .venv-pd22 && .venv-pd22/bin/pip install -q pandas==2.2.3; }
[ -d .venv-app ] || { python3.11 -m venv .venv-app && .venv-app/bin/pip install -q -r requirements.txt; }

.venv-pd15/bin/python scripts/extract_symbols.py data/symbols_1.5.json
.venv-pd22/bin/python scripts/extract_symbols.py data/symbols_2.2.json
./scripts/setup_u4.sh
.venv-app/bin/python scripts/build_chunks.py
.venv-app/bin/python scripts/build_index.py
.venv-app/bin/python scripts/run_eval_multi.py
.venv-app/bin/python scripts/add_agreement.py > /dev/null
.venv-app/bin/python scripts/add_abstention.py > /dev/null
echo "Done. See results.md"
