import io
import zipfile

import pytest

from docpilot.upgrade import load_zip, scan_files

CODE = "import pandas as pd\ndf = pd.DataFrame()\ndf = df.append(df)\nprint(df.applymap(str))\n"


def make_zip(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for name, text in entries.items():
            z.writestr(name, text)
    return b.getvalue()


def test_zip_keeps_py_files_only():
    files, _ = load_zip(make_zip({"a.py": "x=1\n", "readme.txt": "hi"}))
    assert list(files) == ["a.py"]


def test_zip_skips_venv_and_git():
    files, warns = load_zip(make_zip({"venv/x.py": "x=1\n", ".git/y.py": "x=1\n", "ok.py": "x=1\n"}))
    assert list(files) == ["ok.py"]
    assert len(warns) == 2


def test_zip_rejects_unsafe_paths():
    files, warns = load_zip(make_zip({"../evil.py": "x=1\n", "/abs.py": "x=1\n"}))
    assert files == {}
    assert len(warns) == 2


def test_bad_zip_raises():
    with pytest.raises(zipfile.BadZipFile):
        load_zip(b"not a zip")


def test_scan_counts_breaking_calls():
    r = scan_files({"a.py": CODE.encode()}, "1.5", "2.2")
    assert r["breaking_total"] == 2
    assert r["breaking_removed"] == 1
    assert r["breaking_deprecated"] == 1


def test_scan_reports_file_and_line():
    r = scan_files({"a.py": CODE.encode()}, "1.5", "2.2")
    assert (r["breaking"][0]["file"], r["breaking"][0]["line"]) == ("a.py", 3)


def test_applymap_not_breaking_when_target_is_2_0():
    r = scan_files({"a.py": CODE.encode()}, "1.5", "2.0")
    assert r["breaking_total"] == 1


def test_already_removed_in_from_version_is_separate():
    r = scan_files({"a.py": CODE.encode()}, "2.0", "2.2")
    assert r["breaking_total"] == 1
    assert len(r["already_in_from"]) == 1


def test_syntax_error_is_reported_not_raised():
    r = scan_files({"bad.py": b"def (:\n"}, "1.5", "2.2")
    assert r["breaking_total"] == 0
    assert r["syntax_errors"][0]["file"] == "bad.py"


def test_from_must_be_older_than_to():
    with pytest.raises(ValueError):
        scan_files({"a.py": b"x=1\n"}, "2.2", "1.5")


def test_medium_confidence_is_not_counted_as_breaking():
    code = b"import pandas as pd\nx = something()\nx.mad()\n"
    r = scan_files({"a.py": code}, "1.5", "2.2")
    assert r["breaking_total"] == 0
    assert len(r["low_confidence"]) == 1
