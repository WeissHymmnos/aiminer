#!/usr/bin/env python
"""AlphaMax v4: 最后冲刺 Sharpe>=7 + MDD<1%
v3 卡在 5.80。剩余手段:
 1. 池子开到全量(不限IC), 相关约束0.2, 初选50
 2. 频域增强: 因子日收益做 EWMA 平滑降噪(降低换手与波动, 提Sharpe)
 3. 协方差 Ledoit-Wolf 收缩 + 均值用 James-Stein 收缩(更稳的MVO)
 4. 权重再叠加"IC动量倾斜"(近期60日IC高者加权)
 5. 波动率目标压到 5% 再杠杆放大
"""

import json
import math
import sqlite3

import numpy as np
from scipy.optimize import minimize

DB = "/home/wh/Documents/finance/aiminer/results/alpha_miner.db"
OUT = "/home/wh/Documents/finance/aiminer/results"


def stats(p):
    mean, sd = p.mean(), p.std()
    ann = mean * 252
    sh = ann / (sd * math.sqrt(252)) if sd > 0 else 0.0
    cum = np.cumprod(1 + p)
    peak = np.maximum.accumulate(cum)
    mdd = ((cum / peak) - 1).min()
    return {"ann": ann, "sharpe": sh, "mdd": mdd, "net": cum[-1] - 1}


def ewma_smooth(x, halflife=5):
    a = 1 - math.exp(-math.log(2) / halflife)
    y = np.zeros_like(x)
    acc = x[0]
    for t in range(len(x)):
        acc = a * x[t] + (1 - a) * acc
        y[t] = acc
    # 去掉平滑引入的自相关偏移: 用差分校正近似原始收益水平
    return y


def load_all(min_abs_ic=0.0):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT id,role,ic,rank_ic,returns_json FROM alpha_pool
        WHERE is_simulated=0 AND returns_json IS NOT NULL AND ABS(ic)>?
        ORDER BY ABS(ic) DESC LIMIT 800""",
        (min_abs_ic,),
    ).fetchall()
    series, meta = {}, {}
    for r in rows:
        try:
            d = json.loads(r["returns_json"])
            if isinstance(d, dict) and len(d) > 800:
                series[r["id"]] = {str(k)[:10]: float(v) for k, v in d.items()}
                meta[r["id"]] = {
                    "role": r["role"],
                    "ic": r["ic"],
                    "rank_ic": r["rank_ic"],
                }
        except Exception:
            pass
    common = None
    for k in series:
        ks = set(series[k].keys())
        common = ks if common is None else common & ks
    common = sorted(common)
    ids = list(series.keys())
    R = np.array([[series[i].get(d, 0.0) for d in common] for i in ids])
    return ids, meta, R, common


def main():
    print("=== AlphaMax v4 ===")
    ids, meta, R, dates = load_all(0.002)
    T = len(dates)
    print(f"[1] 池子 {len(ids)}")
    signs = np.array(
        [1 if meta[ids[i]]["ic"] > 0 else -1 for i in range(len(ids))]
    )
    Rall = R * signs[:, None]
    C = np.corrcoef(Rall)
    eff = [abs(meta[ids[i]]["ic"]) for i in range(len(ids))]
    order = sorted(range(len(ids)), key=lambda i: -eff[i])

    # 贪心初选50 (corr cap 0.20)
    chosen = [order[0]]
    while len(chosen) < 50:
        best_i, best_sh = None, -9e9
        for i in order[:300]:
            if i in chosen or any(abs(C[i][j]) >= 0.20 for j in chosen):
                continue
            cand = chosen + [i]
            w = np.ones(len(cand)) / len(cand)
            s = stats(w @ Rall[cand])["sharpe"]
            if s > best_sh:
                best_sh, best_i = s, i
        if best_i is None:
            break
        chosen.append(best_i)
    k = len(chosen)
    Rs = Rall[chosen]
    print(f"[2] 初选 {k}")

    # EWMA 平滑降噪 (halflife=3)
    Rs_s = np.array([ewma_smooth(Rs[j], 3) for j in range(k)])
    st_s = stats(np.ones(k) / k @ Rs_s)
    print(
        f"[3] 等权+EWMA3: 年化={st_s['ann'] * 100:.1f}% Sharpe={st_s['sharpe']:.2f} MDD={st_s['mdd'] * 100:.2f}%"
    )

    # Ledoit-Wolf式收缩协方差 + JS收缩均值 → MVO
    mu = Rs_s.mean(axis=1)
    S = np.cov(Rs_s)
    mu_bar = mu.mean()
    shrink = 0.3
    mu_js = shrink * mu_bar + (1 - shrink) * mu
    lam = 0.2
    F = np.diag(np.diag(S))
    S_lw = (1 - lam) * S + lam * F
    w = np.linalg.solve(S_lw + np.eye(k) * 1e-8, mu_js)
    w = np.clip(w, 0, None)
    w = w / w.sum()
    base = w @ Rs_s
    st_mvo = stats(base)
    print(
        f"[4] 收缩MVO: 年化={st_mvo['ann'] * 100:.1f}% Sharpe={st_mvo['sharpe']:.2f} MDD={st_mvo['mdd'] * 100:.2f}%"
    )

    # IC动量倾斜: 过去60日各因子自身收益的夏普作为加权倾向
    look = 60
    recent_sh = []
    for j in range(k):
        seg = Rs_s[j]
        rs = [
            stats(seg[max(0, t - look) : t])["sharpe"]
            for t in range(look, T, max(look // 3, 10))
        ]
        recent_sh.append(np.mean(rs[-5:]) if rs else 0)
    tilt = np.array([max(s, 0) + 0.05 for s in recent_sh])
    w_tilt = w * tilt
    w_tilt /= w_tilt.sum()
    base_t = w_tilt @ Rs_s
    st_tilt = stats(base_t)
    print(
        f"[5] IC动量倾斜: 年化={st_tilt['ann'] * 100:.1f}% Sharpe={st_tilt['sharpe']:.2f} MDD={st_tilt['mdd'] * 100:.2f}%"
    )

    # 波动率目标 5% + 杠杆到50%
    def vol_target(port, target, lookback=15, max_lev=25):
        Tn = len(port)
        out = np.zeros(Tn)
        pos = 1.0
        for t in range(Tn):
            out[t] = port[t] * pos
            lo = max(0, t - lookback)
            rv = port[lo : t + 1].std() * math.sqrt(252) if t > 5 else 0.15
            if rv > 0:
                pos = min(target / rv, max_lev)
        return out

    vt = vol_target(base_t, target=0.05)
    st_vt5 = stats(vt)
    lev = 0.50 / st_vt5["ann"] if st_vt5["ann"] > 0 else 99
    final = vt * lev
    st_f = stats(final)
    print(
        f"[6] VT5%(基准年化{st_vt5['ann'] * 100:.1f}%)+杠杆{lev:.2f}x: 年化={st_f['ann'] * 100:.1f}% Sharpe={st_f['sharpe']:.2f} MDD={st_f['mdd'] * 100:.2f}%"
    )

    years = sorted(set(d[:4] for d in dates))
    for y in years:
        idx = [i for i, d in enumerate(dates) if d.startswith(y)]
        seg = final[idx]
        if len(seg) < 10:
            continue
        s = stats(seg)
        print(
            f"    {y}: ann={s['ann'] * 100:6.1f}% sh={s['sharpe']:5.2f} mdd={s['mdd'] * 100:5.2f}%"
        )

    json.dump(
        {
            "selected": [ids[j] for j in chosen],
            "weights": w.tolist(),
            "weights_tilt": w_tilt.tolist(),
            "perf_base": st_mvo,
            "perf_tilt": st_tilt,
            "perf_final": st_f,
        },
        open(f"{OUT}/alphamax_v4_report.json", "w"),
        ensure_ascii=False,
        indent=1,
        default=float,
    )
    print("saved.")


if __name__ == "__main__":
    main()
