# Selected Quantitative Finance Academic Papers & Theories

## 1. "101 Formulaic Alphas" (Kakushadze, 2015)
**Authors:** Zura Kakushadze
**Summary:** This paper presents 101 real-world quantitative trading alpha factors used in production at WorldQuant. The factors are expressed in a declarative programming language using operators like `rank`, `correlation`, `ts_max`, `ts_argmin`, `delay`, and `delta`. The core finding is that complex, non-linear interactions between price, volume, and cross-sectional ranks yield significant predictive power.
**Key Insights for Agent:**
- Mean-reversion in price is heavily conditional on volume. E.g., `Rank(Corr(Rank(Volume), Rank(Close), 5))` is a powerful momentum/reversion indicator.
- Cross-sectional ranking (`Rank()`) neutralizes market-wide movements, allowing factors to remain robust across different market regimes.
- Delay operators (`Ref(X, d)`) are essential for computing rolling differences (`Delta(X, d) = X - Ref(X, d)`).

## 2. "Guotai Junan 191 Alpha Factors" (GTJA Quantitative Research)
**Authors:** Guotai Junan Securities
**Summary:** A comprehensive report detailing 191 technical and volume-price alpha factors specifically designed for the Chinese A-share market. These factors lean heavily on high-frequency style patterns aggregated to daily bars.
**Key Insights for Agent:**
- Volume-weighted average price (VWAP) is often superior to Close price for short-term trend calculation.
- Asymmetry in price movements: The difference between High-Open vs Open-Low is a strong proxy for intraday buying/selling pressure.
- `(Close - Low) / (High - Low)` is used extensively to gauge closing strength.

## 3. "Machine Learning for Stock Prediction" (Gu, Kelly, Xiu, 2020)
**Authors:** Shihao Gu, Bryan Kelly, Dacheng Xiu
**Summary:** Evaluates various ML methods (from linear regression to Neural Networks and Random Forests) on predicting stock returns using 94 stock characteristics. The paper proves that non-linear models significantly outperform linear models.
**Key Insights for Agent:**
- Momentum and liquidity are the most important predictive features across all models.
- Deep learning architectures capture complex interactions that simple linear alphas miss.
- When generating alphas, combining price momentum with liquidity (volume) metrics is highly effective.

## 4. "Deep Alpha: A New Paradigm for Factor Mining" 
**Summary:** Proposes using genetic algorithms and reinforcement learning to automatically search the vast mathematical space of possible factors. 
**Key Insights for Agent:**
- Automated factor mining should avoid "overfitting" by ensuring expressions are logically sound (e.g., comparing apples to apples: `Price / Price`, not `Price + Volume`).
- Rank Information Coefficient (Rank IC) is a more robust evaluation metric than Pearson IC because it ignores outliers in returns.

## 5. "Market Microstructure and High-Frequency Data" (O'Hara, 1995)
**Summary:** Discusses how the mechanics of trading affect price formation. 
**Key Insights for Agent:**
- Order flow imbalance directly impacts price. Daily volume change `Delta(Volume, 1)` coupled with `Sign(Delta(Close, 1))` approximates net buying pressure over a daily horizon.
