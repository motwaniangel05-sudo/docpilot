import re

DEFAULT = "2.2"


def detect_version(text):
    """Return (version, message). Supported versions: '1.5' and '2.2'."""
    m = re.search(r"pandas\s*(?:==|>=|<=|~=|=|>|<)?\s*v?(\d+)\.(\d+)(?:\.\d+)?", text, re.I)
    if not m:
        m = re.search(r"(?:version|v)\s*(\d+)\.(\d+)", text, re.I)
    if not m:
        m = re.search(r"(?<![\d.])(1\.5|2\.2)(?![\d])", text)
        if m:
            major, minor = m.group(1).split(".")
            m = re.match(r"(\d+)\.(\d+)", f"{major}.{minor}")
    if not m:
        return DEFAULT, "No pandas version found in your question, so I assumed pandas 2.2."
    major, minor = int(m.group(1)), int(m.group(2))
    found = f"{major}.{minor}"
    if found in ("1.5", "2.2"):
        return found, f"Detected pandas {found}."
    if major == 1:
        return "1.5", f"Detected pandas {found}; using the closest indexed version, 1.5."
    if major == 2:
        return "2.2", f"Detected pandas {found}; using the closest indexed version, 2.2."
    return DEFAULT, f"pandas {found} is not supported, so I assumed pandas 2.2."
