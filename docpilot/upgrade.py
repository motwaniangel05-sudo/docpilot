import io
import zipfile
from collections import Counter

from docpilot.checker import check_code, vkey

SKIP_DIRS = {".git", "site-packages", "node_modules", "__pycache__", ".venv", "venv", "env", ".tox", "build", "dist"}
MAX_FILES = 500
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024


def _skip(name):
    parts = [p for p in name.replace("\\", "/").split("/") if p]
    if name.startswith("/") or ".." in parts:
        return True
    return any(p in SKIP_DIRS or p.startswith(".venv") for p in parts[:-1])


def load_zip(data):
    """Return ({name: bytes}, [warnings]). Reads in memory only, never extracts to disk."""
    files, warns, total = {}, [], 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            n = info.filename
            if info.is_dir() or not n.endswith(".py"):
                continue
            if _skip(n):
                warns.append(f"skipped {n}")
                continue
            if info.file_size > MAX_FILE_BYTES:
                warns.append(f"skipped {n} (over 2 MB)")
                continue
            total += info.file_size
            if len(files) >= MAX_FILES or total > MAX_TOTAL_BYTES:
                warns.append("stopped early: upload too large (max 500 files / 20 MB)")
                break
            files[n] = z.read(info)
    return files, warns


def scan_files(files, frm, to):
    """files: {name: bytes}. Returns a report dict. Never executes anything."""
    if vkey(frm) >= vkey(to):
        raise ValueError("'from' version must be older than 'to' version")
    breaking, already, errors, low = [], [], [], []
    for name in sorted(files):
        code = files[name].decode("utf-8", errors="replace")
        out = check_code(code, to)
        if out["error"]:
            errors.append({"file": name, "error": out["error"]})
            continue
        for f in out["findings"]:
            row = {"file": name, "line": f["line"], "symbol": f["symbol"], "status": f["status"],
                   "since": f["since"], "fix": f["replacement"], "confidence": f["confidence"]}
            if f["confidence"] != "high":
                if vkey(f["since"]) > vkey(frm):
                    low.append(row)
                continue
            (breaking if vkey(f["since"]) > vkey(frm) else already).append(row)
    breaking.sort(key=lambda r: (r["file"], r["line"]))
    already.sort(key=lambda r: (r["file"], r["line"]))
    return {
        "from": frm, "to": to, "files_scanned": len(files),
        "breaking_total": len(breaking),
        "breaking_removed": sum(r["status"] == "removed" for r in breaking),
        "breaking_deprecated": sum(r["status"] == "deprecated" for r in breaking),
        "breaking": breaking, "already_in_from": already, "syntax_errors": errors,
        "low_confidence": low,
        "top_symbols": Counter(r["symbol"] for r in breaking).most_common(5),
    }
