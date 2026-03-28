import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
import qlib
from qlib.data import D
from typing import List, Optional

# import warnings
# warnings.filterwarnings("ignore")


class WeightCalculator:
    def __init__(
        self,
        factor_expressions: List[str],
        start_date: str,
        end_date: str,
        instruments: Optional[List[str]] = None,
    ):
        self.factor_expressions = factor_expressions
        self.start_date = start_date
        self.end_date = end_date

        self.instruments = (
            instruments
            if instruments is not None
            else D.list_instruments(
                market="csi300", start_time=start_date, end_time=end_date
            )
        )

        qlib.init(provider_uri="path/to/your/qlib_data", region="cn")

        self.label_expr = "Ref($close, -1)/$close - 1"

        self.w_opt: np.ndarray = None
        self.ic_train_single: dict[str, float] = {}
        self.ic_test_single:  dict[str, float] = {}
        self.ic_train_comb:    float = None
        self.ic_test_comb:     float = None


    def fetch_data(self, start_time: str, end_time: str):
        fdf = D.features(
            self.instruments,
            self.factor_expressions,
            start_time=start_time, end_time=end_time, freq="day"
        )
        fdf.replace([np.inf, -np.inf], np.nan, inplace=True)
        ldf = D.features(
            self.instruments,
            [self.label_expr],
            start_time=start_time, end_time=end_time, freq="day"
        )
        ldf.columns = ["label"]

        def zscore(df: pd.DataFrame) -> pd.DataFrame:
            means = df.mean(axis=0, skipna=True)
            stds = df.std(axis=0, skipna=True, ddof=0)
            stds[stds < 1e-8] = 1
            return df.sub(means, axis='columns').div(stds, axis='columns')

        fdf = (
            fdf
            .groupby(level=1, group_keys=False)
            .apply(zscore)
            .replace([np.inf, -np.inf], np.nan)
            .replace(np.nan, 0)
        )

        
        return fdf, ldf

    def compute_mean_ic(self, X: pd.DataFrame, y: pd.DataFrame, weights: np.ndarray) -> float:
        alpha = X.dot(weights)
        alpha_df = alpha.to_frame(name="alpha")
        all_data = alpha_df.join(y, how="inner").dropna()
        all_data.columns = ["factor", "label"]
        ic_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].corr(x["label"])
        )
        
        try:
            if ic_series.isna().mean() > 0.5:
                return 0.0
        except Exception:
            return 0.0
        
        ic = ic_series.dropna().mean()
        ic = 0.0 if (not isinstance(ic, float) or np.isnan(ic)) else ic
        return ic

    def train_optimal_weights(self, X: pd.DataFrame, y: pd.DataFrame, maxiter: int = 1):
        def obj(u: np.ndarray) -> float:
            w = u / np.sum(np.abs(u))
            return -1 * self.compute_mean_ic(X, y, w)
        bounds = [(-1, 1)] * X.shape[1]
        result = differential_evolution(obj, bounds, maxiter=maxiter, popsize=20, tol=1e-6, polish=False, disp=True)
        u_opt = result.x
        w_opt = u_opt / np.sum(np.abs(u_opt))
        return w_opt

    def fit(self):  
        print("Start calculating linear weights.")
        X_train, y_train = self.fetch_data(self.start_date, self.end_date)
        self.w_opt = self.train_optimal_weights(X_train, y_train)
        print("Finish calculating linear weights.")        

        return self.w_opt