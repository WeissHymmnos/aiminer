# noise_proc.py
import numpy as np
import pandas as pd
from qlib.data.dataset.processor import Processor

class NoiseInjection(Processor):
    def __init__(self, var: float = 0.001):
        super().__init__()
        self.sigma = np.sqrt(var)

    def __call__(self, df: pd.DataFrame, instrument=None) -> pd.DataFrame:
        # instrument kwarg is ignored
        noise = np.random.normal(0, self.sigma, size=df.shape)
        return df * (1.0 + noise)
    
class NoiseInjection_t(Processor):
    def __init__(self, var: float = 0.001, dof: int = 3):
        super().__init__()
        self.sigma = np.sqrt(var)
        self.dof = dof

    def __call__(self, df: pd.DataFrame, instrument=None) -> pd.DataFrame:
        # instrument kwarg is ignored
        t_raw = np.random.standard_t(self.dof, size=df.shape)
        t_noise = t_raw * self.sigma * np.sqrt((self.dof - 2) / self.dof)        
        return df * (1.0 + t_noise)