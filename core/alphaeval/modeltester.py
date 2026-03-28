import numpy as np
import pandas as pd
from openai import OpenAI
import re
import json
import qlib
from qlib.data import D
from typing import List, Optional
from .combo import WeightCalculator
from qlib.data.data import LocalDatasetProvider

# import warnings
# warnings.filterwarnings("ignore")

def zscore(df: pd.DataFrame) -> pd.DataFrame:
    means = df.mean(axis=0, skipna=True)
    stds  = df.std(axis=0, skipna=True, ddof=0).replace(0, np.nan)
    stds[stds < 1e-8] = 1
    return df.sub(means, axis='columns').div(stds, axis='columns')

class AlphaEval:
    def __init__(
        self,
        factor_expressions: List[str],
        weights: Optional[List[float]] = None,
        train_start_date: str = "2010-01-01",
        train_end_date: str = "2016-12-31",
        test_start_date: str = "2017-01-01",
        test_end_date: str = "2020-10-31",        
        instruments: Optional[List[str]] = None,
        daily_normalize: bool = True
    ):
        self.alphacombo: pd.DataFrame
        self.factor_expressions = factor_expressions
        if weights:
            self.weights = weights
        else:
            self.weights = WeightCalculator(self.factor_expressions, train_start_date, train_end_date, instruments).fit()
        self.train_start_date = train_start_date
        self.train_end_date = train_end_date
        self.test_start_date = test_start_date
        self.test_end_date = test_end_date
        self.daily_normalize = daily_normalize

        # If the user does not specify the market, CSI300 is taken by default
        self.instruments = (
            instruments
            if instruments is not None
            else D.list_instruments(
                market="csi300"
            )
        )

        qlib.init(provider_uri="path/to/your/qlib_data", region="cn")

        self.label_expr = "Ref($close, -1)/$close - 1"

    def fetch_data(self):
        self.factor_data = D.features(
            self.instruments,
            self.factor_expressions,
            start_time=self.test_start_date,
            end_time=self.test_end_date,
            freq="day",
        )
        self.factor_data.replace([np.inf, -np.inf], np.nan, inplace=True)
        print("Factor data done.")
        df = D.features(
            instruments=["SH000300"],
            fields=["$close"],
            start_time=self.train_start_date,
            end_time=self.train_end_date,
            freq="day",
        )

        close = (
            df["$close"]
            .droplevel(1) 
        )
        close = close.dropna()
        close = (close - close.min())/(close.max() - close.min())
        variance = close.dropna().var(ddof=1)
        print("Noise Var done.")
        provider = LocalDatasetProvider()
        self.noise_factor_data1 = provider.dataset(
            instruments=self.instruments,
            fields=self.factor_expressions,
            start_time=self.test_start_date,
            end_time=self.test_end_date,
            freq="day",
            inst_processors=[
                {
                    "class": "noise_proc.NoiseInjection",
                    "kwargs": {"var": variance},
                }
            ],
        )
        self.noise_factor_data1.replace([np.inf, -np.inf], np.nan, inplace=True)
        print("Noise data1 done.")
        self.noise_factor_data2 = provider.dataset(
            instruments=self.instruments,
            fields=self.factor_expressions,
            start_time=self.test_start_date,
            end_time=self.test_end_date,
            freq="day",
            inst_processors=[
                {
                    "class": "noise_proc.NoiseInjection_t",
                    "kwargs": {"var": variance, "dof": 3},
                }
            ],
        )
        self.noise_factor_data2.replace([np.inf, -np.inf], np.nan, inplace=True)
        print("Noise data2 done.")
        self.label_data = D.features(
            self.instruments,
            [self.label_expr],
            start_time=self.test_start_date,
            end_time=self.test_end_date,
            freq="day",
        )
        self.label_data.columns = ["label"]

        if self.daily_normalize:
            self.factor_data = (
                self.factor_data
                .groupby(level=1, group_keys=False)
                .apply(zscore)
                .replace([np.inf, -np.inf], np.nan)
                .replace(np.nan, 0)
            )

            self.noise_factor_data1 = (
                self.noise_factor_data1
                .groupby(level=1, group_keys=False)
                .apply(zscore)
                .replace([np.inf, -np.inf], np.nan)
                .replace(np.nan, 0)
            )

            self.noise_factor_data2 = (
                self.noise_factor_data2
                .groupby(level=1, group_keys=False)
                .apply(zscore)
                .replace([np.inf, -np.inf], np.nan)
                .replace(np.nan, 0)
            )
        
        self.alphacombo = self.factor_data.dot(self.weights)
        self.alphacombo = self.alphacombo.to_frame(name="alphacombo")

        self.noisecombo1 = self.noise_factor_data1.dot(self.weights)
        self.noisecombo1 = self.noisecombo1.to_frame(name="noisecombo1")

        self.noisecombo2 = self.noise_factor_data2.dot(self.weights)
        self.noisecombo2 = self.noisecombo2.to_frame(name="noisecombo2")

    def calculate_pnl(self) -> None:
        self.fetch_data()
        all_data = self.alphacombo.join(self.label_data, how="inner").dropna()
        all_data.columns = ["factor", "label"]
        records = []
        prev_longs: Optional[set] = None
        prev_shorts: Optional[set] = None

        for date, group in all_data.groupby(level="datetime"):
            f = group["factor"]
            l = group["label"]

            long_cut = f.quantile(1 - 0.2)
            short_cut = f.quantile(0.2)

            longs = set(f[f >= long_cut].index.get_level_values("instrument"))
            shorts = set(f[f <= short_cut].index.get_level_values("instrument"))

            long_ret = l[f >= long_cut].mean()
            short_ret = -l[f <= short_cut].mean()
            pnl = (long_ret + short_ret) / 2
            market_mean = l.mean()

            if prev_longs is None:
                turnover = float("nan")
            else:
                long_out = prev_longs - longs
                long_in = longs - prev_longs
                short_out = prev_shorts - shorts
                short_in = shorts - prev_shorts
                trades = len(long_out) + len(long_in) + len(short_out) + len(short_in)
                denom = len(prev_longs) + len(prev_shorts)
                turnover = trades / denom if denom > 0 else float("nan")

            cost = turnover * 0.0015 if turnover else 0 # Suppose the cost of each transaction is 0.15%.
            pnl = pnl - cost                
            records.append((date, pnl, turnover, market_mean))
            prev_longs, prev_shorts = longs, shorts

        pnl_df = pd.DataFrame(
            records, columns=["datetime", "pnl", "turnover", "market_mean"]
        ).set_index("datetime")
        self.pnl =  pnl_df.sort_index()

    def calculate_covariance_entropy(self) -> None:
        if not self.daily_normalize:
            clean_df = (
                self.factor_data
                .groupby(level=1, group_keys=False)
                .apply(zscore)
                .replace([np.inf, -np.inf], np.nan)
                .replace(np.nan, 0)
            )
        else:    
            clean_df = self.factor_data.dropna(how="any")
        mat = clean_df.values 
        if mat.shape[0] < 2:
            raise ValueError(
                "After discarding NaN, the number of samples is insufficient."
            )

        C = np.cov(mat, rowvar=False)
        self.covariance = C
        eigs = np.linalg.eigvalsh(C)
        eigs = np.clip(eigs, a_min=0, a_max=None)
        total = eigs.sum()
        if total <= 0:
            return np.nan
        p = eigs / total
        p = p[p > 0]
        self.diversity = -(p * np.log(p)).sum()
        self.diversity = self.diversity / np.log(len(self.factor_expressions))

    def LLM_scores(
        self,
        model: str = "claude-opus-4-6",
        temperature: float = 0.2,
    ) -> None:
        client = OpenAI(
            api_key=os.getenv("ClaudeCode_KEY"),
            base_url="https://api.gptsapi.net/v1"
        )

        prompt = (
            "Below is a set of quantitative factor expressions designed using qlib syntax. "
            "Please score each factor from 50 to 100 based on the rationality of financial market logic (full score), and provide the corresponding logical explanation. "
            "When scoring, differences in scores can be larger: logical factors can receive very high scores, and vice versa. "
            "We also prefer longer factors, as this aligns with the goal of automated search.\n\n"
            f"Factor list: {self.factor_expressions}\n\n"
            "Please return **a pure JSON array only**, without any Markdown code blocks. "
            "The array length should match the factor list, and each element should be an object containing:\n"
            "  - factor: the factor expression\n"
            "  - score: numeric score (0–100)\n"
            "  - explanation: a brief logical explanation\n"
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=1000,
        )

        text = resp.choices[0].message.content.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        m = re.search(r"(\[\s*[\s\S]*\s*\])", text)
        if m:
            text = m.group(1)

        try:
            results = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Cannot be parsed as JSON: {text!r}") from e

        self.llm_scores = []
        self.llm_explanations = []

        if not isinstance(results, list) or len(results) != len(self.factor_expressions):
            raise ValueError(
                f"Result numbers ({len(results)}) and factor numbers ({len(self.factor_expressions)}) not matched."
            )

        for idx, item in enumerate(results, start=1):
            if not all(k in item for k in ("factor", "score", "explanation")):
                raise ValueError(f"The {idx} item is missing a field: {item!r}")

            score = float(item["score"])
            score = max(0.0, min(100.0, score))
            self.llm_scores.append(score)
            self.llm_explanations.append(item["explanation"])

        self.llm_avg_score = sum(self.llm_scores) / len(self.llm_scores) if self.llm_scores else 0.0


    def run(self):
        self.fetch_data()

        all_data = self.alphacombo.join(self.label_data, how="inner").join(self.noisecombo1, how="inner").join(self.noisecombo2, how="inner").dropna()
        all_data.columns = ["factor", "label", "noisy1", "noisy2"]
        ic_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].corr(x["label"])
        )
        rank_ic_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].rank().corr(x["label"].rank())
        )
        pfs1_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].corr(x["noisy1"])
        )
        pfs2_series = all_data.groupby(level="datetime").apply(
            lambda x: x["factor"].corr(x["noisy2"])
        )

        factor_mat = (
            self.alphacombo
            .reset_index()
            .pivot(index="datetime", columns="instrument", values="alphacombo")
        )
        ranks = factor_mat.rank(axis=1)
        probs = ranks.div(ranks.sum(axis=1), axis=0)
        probs_prev = probs.shift(1)
        eps = 1e-8
        kl = (probs * np.log((probs + eps) / (probs_prev + eps))).sum(axis=1)
        rre_series = kl.dropna() 
        rre_series = 1 / (1 + rre_series)
        self.ic = round(ic_series.mean(), 3)
        self.rankic = round(rank_ic_series.mean(), 3)
        self.rre = round(rre_series.mean(), 3) if len(rre_series) > 0 else np.nan
        self.pfs1 = round(pfs1_series.mean(), 6)
        self.pfs2 = round(pfs2_series.mean(), 6)

        self.calculate_covariance_entropy()
        self.LLM_scores()

    def summary(self):
        print("IC: ", self.ic)
        print("RankIC: ", self.rankic)
        print("RRE: ", self.rre)
        print("PFS1: ", self.pfs1)
        print("PFS2: ", self.pfs2)
        print("Diversity: ", self.diversity)
        print("LLM: ", self.llm_avg_score)


    def run_single_factor(self):
        self.fetch_data()
        print("Finish fetching data.")
        self.LLM_scores()
        res = []
        for i, f in enumerate(self.factor_expressions):
            print(i)
            try:
                data = self.factor_data[f].copy()
                all_data = data.join(self.label_data, how="inner").join(self.noise_factor_data1[f].copy(), how="inner").join(self.noise_factor_data2, how="inner").dropna()
                all_data.columns = ["factor", "label", "noisy1", "noisy2"]
                ic_series = all_data.groupby(level="datetime").apply(
                    lambda x: x["factor"].corr(x["label"])
                )
                rank_ic_series = all_data.groupby(level="datetime").apply(
                    lambda x: x["factor"].rank().corr(x["label"].rank())
                )
                pfs1_series = all_data.groupby(level="datetime").apply(
                    lambda x: x["factor"].corr(x["noisy1"])
                )
                pfs2_series = all_data.groupby(level="datetime").apply(
                    lambda x: x["factor"].corr(x["noisy2"])
                )

                factor_mat = (
                    data
                    .reset_index()
                    .pivot(index="datetime", columns="instrument", values="alphacombo")
                )
                ranks = factor_mat.rank(axis=1)
                probs = ranks.div(ranks.sum(axis=1), axis=0)
                probs_prev = probs.shift(1)
                eps = 1e-8
                kl = (probs * np.log((probs + eps) / (probs_prev + eps))).sum(axis=1)
                rre_series = kl.dropna()  
                rre_series = 1 / (1 + rre_series)
                ic = round(ic_series.mean(), 3)
                rankic = round(rank_ic_series.mean(), 3)
                rre = round(rre_series.mean(), 3) if len(rre_series) > 0 else np.nan
                pfs1 = round(pfs1_series.mean(), 6)
                pfs2 = round(pfs2_series.mean(), 6)
                res.append({"factor":f, "ic":ic, "rankic":rankic, "RRE":rre, "PFS1":pfs1, "PFS2":pfs2, "LLM":self.llm_scores[i]})
            except Exception:
                print(f"{f}, error!!!")

        return res
            
            





