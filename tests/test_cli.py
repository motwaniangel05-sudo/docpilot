import pytest

from docpilot.cli import main

BAD = "import pandas as pd\ndf = pd.DataFrame()\ndf = df.append(df)\n"
CLEAN = "import pandas as pd\ndf = pd.DataFrame()\nprint(df.shape)\n"


def test_exit_1_when_breaking_calls(tmp_path, capsys):
    f = tmp_path / "a.py"
    f.write_text(BAD)
    assert main(["check", str(f), "--pandas", "2.2"]) == 1
    assert "DataFrame.append" in capsys.readouterr().out


def test_exit_0_when_clean(tmp_path):
    f = tmp_path / "a.py"
    f.write_text(CLEAN)
    assert main(["check", str(f), "--pandas", "2.2"]) == 0


def test_exit_0_when_removed_after_target_version(tmp_path):
    f = tmp_path / "a.py"
    f.write_text(BAD)
    assert main(["check", str(f), "--pandas", "1.5"]) == 0


def test_exit_2_on_missing_path(tmp_path):
    assert main(["check", str(tmp_path / "nope.py"), "--pandas", "2.2"]) == 2


def test_exit_2_when_folder_has_no_py_files(tmp_path):
    assert main(["check", str(tmp_path), "--pandas", "2.2"]) == 2


def test_exit_2_on_bad_version(tmp_path):
    f = tmp_path / "a.py"
    f.write_text(CLEAN)
    with pytest.raises(SystemExit) as e:
        main(["check", str(f), "--pandas", "9.9"])
    assert e.value.code == 2


def test_folder_scan_skips_venv(tmp_path):
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "x.py").write_text(BAD)
    (tmp_path / "ok.py").write_text(CLEAN)
    assert main(["check", str(tmp_path), "--pandas", "2.2"]) == 0


def test_syntax_error_does_not_crash(tmp_path):
    (tmp_path / "bad.py").write_text("def (:\n")
    (tmp_path / "ok.py").write_text(BAD)
    assert main(["check", str(tmp_path), "--pandas", "2.2"]) == 1
