import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from docpilot.checker import check_code, vkey


def syms(code, v):
    return [f["symbol"] for f in check_code(code, v)["findings"]]


def test_01_df_append_removed_in_20():
    assert syms("import pandas as pd\ndf = pd.DataFrame()\ndf = df.append({'a': 1})", "2.0") == ["DataFrame.append"]

def test_02_append_not_flagged_in_15():
    assert syms("import pandas as pd\ndf = pd.DataFrame()\ndf.append({'a': 1})", "1.5") == []

def test_03_list_append_not_flagged():
    assert syms("items = []\nitems.append(3)", "2.2") == []

def test_04_iteritems_flagged():
    assert "DataFrame.iteritems" in syms("import pandas as pd\ndf = pd.DataFrame()\nfor k, v in df.iteritems(): pass", "2.2")

def test_05_series_iteritems_flagged():
    assert "Series.iteritems" in syms("import pandas as pd\ns = pd.Series([1])\ns.iteritems()", "2.0")

def test_06_applymap_not_flagged_in_20():
    assert syms("import pandas as pd\ndf = pd.DataFrame()\ndf.applymap(str)", "2.0") == []

def test_07_applymap_deprecated_in_22():
    r = check_code("import pandas as pd\ndf = pd.DataFrame()\ndf.applymap(str)", "2.2")["findings"]
    assert r[0]["status"] == "deprecated" and r[0]["replacement"] == "DataFrame.map"

def test_08_read_gbq_qualified():
    assert syms("import pandas as pd\npd.read_gbq('select 1')", "2.2") == ["pd.read_gbq"]

def test_09_alias_import():
    assert syms("import pandas as pandas_lib\ndf = pandas_lib.DataFrame()\ndf.append(1)", "2.2") == ["DataFrame.append"]

def test_10_numpy_swapaxes_not_flagged():
    assert syms("import numpy as np\nnp.zeros((2, 3)).swapaxes(0, 1)", "2.2") == []

def test_11_syntax_error_reported():
    r = check_code("df.append(", "2.2")
    assert r["error"].startswith("SyntaxError") and r["findings"] == []

def test_12_bad_version_raises():
    with pytest.raises(ValueError):
        check_code("x = 1", "3.0")

def test_13_empty_code_no_findings():
    assert check_code("", "2.2") == {"error": None, "findings": []}

def test_14_line_numbers():
    f = check_code("import pandas as pd\n\n\ndf = pd.DataFrame()\ndf.append(1)", "2.2")["findings"]
    assert f[0]["line"] == 5

def test_15_multiple_findings_sorted():
    code = "import pandas as pd\ndf = pd.DataFrame()\ndf.iteritems()\ndf.append(1)"
    assert [f["line"] for f in check_code(code, "2.2")["findings"]] == [3, 4]

def test_16_is_monotonic_removed():
    assert syms("import pandas as pd\ns = pd.Series([1])\ns.is_monotonic", "2.0") == ["Series.is_monotonic"]

def test_17_function_argument_df_name_recognised():
    assert syms("def f(df):\n    return df.append(1)", "2.2") == ["DataFrame.append"]

def test_18_chained_assignment_propagates():
    assert syms("import pandas as pd\na = pd.read_csv('x')\nb = a.dropna()\nb.append(1)", "2.2") == ["DataFrame.append"]

def test_19_vkey_minor_only():
    assert vkey("2.2.0") == vkey("2.2") and vkey("2.1") < vkey("2.2")

def test_20_code_is_not_executed(tmp_path):
    marker = tmp_path / "ran.txt"
    code = f"open(r'{marker}', 'w').write('x')\nimport pandas as pd\ndf = pd.DataFrame()\ndf.append(1)"
    check_code(code, "2.2")
    assert not marker.exists()
