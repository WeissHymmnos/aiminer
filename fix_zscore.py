import pandas as pd
import numpy as np

def zscore_test(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    means = df.mean(axis=0, skipna=True)
    stds  = df.std(axis=0, skipna=True).replace(0, np.nan)
    res = df.sub(means, axis=1)
    res = res.div(stds, axis=1).fillna(0)
    return res

df = pd.DataFrame({'factor1': [1, 2, 3], 'factor2': [10, 20, 30]}, index=['s1', 's2', 's3'])
print(zscore_test(df))
