import importlib, warnings
import pandas as pd

checks = {
 "003 Int64Index": lambda: pd.Int64Index,
 "004 core.indexes.numeric": lambda: importlib.import_module("pandas.core.indexes.numeric"),
 "006 DataFrame.append": lambda: pd.DataFrame.append,
 "007 DataFrame.iteritems": lambda: pd.DataFrame.iteritems,
 "008 Index.is_monotonic": lambda: pd.Index([1, 2]).is_monotonic,
 "010 DataFrame.mad": lambda: pd.DataFrame({"a": [1, 2]}).mad(),
 "012 mode.use_inf_as_null": lambda: pd.get_option("mode.use_inf_as_null"),
 "015 io.json.json_normalize": lambda: importlib.import_module("pandas.io.json").json_normalize,
 "016 Categorical.to_dense": lambda: pd.Categorical([1, 2]).to_dense(),
 "017 ExcelWriter.save": lambda: pd.ExcelWriter.save,
}
print("pandas", pd.__version__)
for name, fn in checks.items():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            fn()
            kinds = sorted({x.category.__name__ for x in w})
            print(f"{name:30s} PRESENT", kinds if kinds else "")
        except Exception as e:
            print(f"{name:30s} MISSING ({type(e).__name__})")
