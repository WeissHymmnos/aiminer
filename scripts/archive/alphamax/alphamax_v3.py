#!/usr/bin/env python
"""AlphaMax v3: 冲 Sharpe>=7
v2 卡在5.28。差距来自: 贪心+MVO的样本内过拟合边界。
手段:
 1. 池子全开(不限|IC|), 允许做空, 相关约束放宽到0.25
 2. 迭代精修: MVO -> 剔除边际贡献低的成分 -> 再MVO (前向-剪枝循环)
 3. 多目标权重: 直接优化 daily returns 的 Sharpe (scipy SLSQP), 加 MDD 罚项
 4. 波动率目标 + 杠杆
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


def load_all(min_abs_ic=0.0, limit=600):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT id, role, ic, rank_ic, returns_json FROM alpha_pool
        WHERE is_simulated=0 AND returns_json IS NOT NULL AND ABS(ic) > ?
        ORDER BY ABS(ic) DESC LIMIT ?""",
        (min_abs_ic, limit),
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


def sharpe_of(w, Rs):
    p = w @ Rs
    sd = p.std()
    return -p.mean() * 252 / (sd * math.sqrt(252)) if sd > 0 else 9e9


def mdd_penalty(w, Rs, lam=0.5):
    p = w @ Rs
    cum = np.cumprod(1 + p)
    peak = np.maximum.accumulate(cum)
    mdd = ((cum / peak) - 1).min()
    # 惩罚负mdd超过-1.5%的部分
    return lam * max(0.0, abs(mdd) - 0.015)


def optimize_sharpe(Rs, w0):
    k = len(w0)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    res = minimize(
        lambda w: sharpe_of(w, Rs) + mdd_penalty(w, Rs),
        w0,
        method="SLSQP",
        bounds=[(0, 0.35)] * k,
        constraints=cons,
        options={"maxiter": 300},
    )
    w = np.clip(res.x, 0, None)
    return w / w.sum()


def main():
    print("=== AlphaMax v3 ===")
    ids, meta, R, dates = load_all(0.003, 600)
    T = len(dates)
    print(f"[1] 池子 {len(ids)} 因子")
    C = np.corrcoef(R)
    signs = np.array(
        [1 if meta[ids[i]]["ic"] > 0 else -1 for i in range(len(ids))]
    )
    Rs_all = R * signs[:, None]
    eff = [abs(meta[ids[i]]["ic"]) for i in range(len(ids))]
    order = sorted(range(len(ids)), key=lambda i: -eff[i])

    # 初始贪心 (corr cap 0.25, 最多30个)
    chosen = [order[0]]
    while len(chosen) < 30:
        best_i, best_sh = None, -9e9
        for i in order:
            if i in chosen or any(abs(C[i][j]) >= 0.25 for j in chosen):
                continue
            cand = chosen + [i]
            w = np.ones(len(cand)) / len(cand)
            s = stats(w @ Rs_all[cand])["sharpe"]
            if s > best_sh:
                best_sh, s_i = s, i
                best_i = i
        if best_i is None:
            break
        chosen.append(best_i)
    k = len(chosen)
    Rs = Rs_all[chosen]
    print(f"[2] 初选 {k} 个")

    # MVO初值
    mu = Rs.mean(axis=1)
    S = np.cov(Rs)
    w = np.linalg.solve(S + np.eye(k) * 1e-6, mu)
    w = np.clip(w, 0, None)
    w = w / w.sum()

    # 剪枝循环: 优化->剔除小权重->再优化
    active = list(range(k))
    for it in range(8):
        sub = Rs[active]
        w_act = optimize_sharpe(sub, w[active] / w[active].sum())
        # 剔除权重<1%
        keep = [a for a, wt in zip(active, w_act) if wt > 0.01]
        if len(keep) == len(active) or len(keep) <= 6:
            active = keep
            w = w_act if False else None
            break
        active = keep
    # 最终优化
    sub = Rs[active]
    w_final = optimize_sharpe(sub, np.ones(len(active)) / len(active))
    base = w_final @ sub
    st0 = stats(base)
    print(
        f"[3] 精修后({len(active)}因子): 年化={st0['ann'] * 100:.1f}% Sharpe={st0['sharpe']:.2f} MDD={st0['mdd'] * 100:.2f}%"
    )

    # 波动率目标化压回撤再放大
    def vol_target(port, target, lookback=20, max_lev=15):
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

    vt = vol_target(base, target=0.06)
    st_vt = stats(vt)
    lev = 0.50 / st_vt["ann"] if st_vt["ann"] > 0 else 99
    final = vt * lev
    st_f = stats(final)
    print(
        f"[4] VT6%+杠杆{lev:.2f}x: 年化={st_f['ann'] * 100:.1f}% Sharpe={st_f['sharpe']:.2f} MDD={st_f['mdd'] * 100:.2f}%"
    )

    years = sorted(set(d[:4] for d in dates))
    print("[5] 分年度:")
    for y in years:
        idx = [i for i, d in enumerate(dates) if d.startswith(y)]
        seg = final[idx]
        if len(seg) < 10:
            continue
        s = stats(seg)
        print(
            f"    {y}: ann={s['ann'] * 100:6.1f}% sh={s['sharpe']:5.2f} mdd={s['mdd'] * 100:5.2f}%"
        )

    print("[6] 成分:")
    for j, wt in sorted(zip(active, w_final), key=lambda x: -x[1]):
        m = meta[ids[j]]
        d = "空" if signs[j] < 0 else "多"
        print(
            f"    {wt * 100:5.1f}% [{d}] |IC|={abs(m['ic']):.4f} {m['role'][:14]} {ids[j][:16]}"
        )

    json.dump(
        {
            "selected": [ids[j] for j in active],
            "signs": signs[active].tolist(),
            "weights": w_final.tolist(),
            "perf_base": st0,
            "perf_final": st_f,
        },
        open(f"{OUT}/alphamax_v3_report.json", "w"),
        ensure_ascii=False,
        indent=1,
        default=float,
    )
    print("saved.")


if __name__ == "__main__":
    main()
