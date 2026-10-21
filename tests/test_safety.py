import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from docpilot.safety import exec_allowed


def test_exec_off_by_default(monkeypatch):
    monkeypatch.delenv("DOCPILOT_ALLOW_EXEC", raising=False)
    assert exec_allowed() is False

def test_exec_off_for_other_values(monkeypatch):
    for v in ["0", "true", "yes", ""]:
        monkeypatch.setenv("DOCPILOT_ALLOW_EXEC", v)
        assert exec_allowed() is False

def test_exec_on_only_for_1(monkeypatch):
    monkeypatch.setenv("DOCPILOT_ALLOW_EXEC", "1")
    assert exec_allowed() is True
