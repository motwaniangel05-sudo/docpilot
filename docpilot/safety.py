import os


def exec_allowed():
    """Code execution is OFF unless the env var DOCPILOT_ALLOW_EXEC is exactly "1".
    Never set it on the deployed app. Only the local eval script sets it."""
    return os.environ.get("DOCPILOT_ALLOW_EXEC") == "1"
