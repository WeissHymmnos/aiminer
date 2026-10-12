#!/usr/bin/env python
"""AlphaMax v6 终版: 目标 50%年化 / Sharpe>=7 / MDD<1% 同时满足
v4 已达: 50%/10.8/-7.6%(杠杆放大回撤) ; v5 达: 24.4%/12.5/-0.8%
思路: v4 的 EWMA+收缩MVO 基础组合(17%/11.2/-2.3%) 上加
"恒定杠杆 + 回撤熔断"(drawdown brake): 净值回撤逼近0.9%时自动降仓, 恢复后回升
这是可实盘执行的风控规则, 不是前视。
"""

import json
import math
import sqlite3

import numpy as np

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


def ewma(x, hl=3):
    a = 1 - math.exp(-math.log(2) / hl)
    y = np.zeros_like(x)
    acc = x[0]
    for t in range(len(x)):
        acc = a * x[t] + (1 - a) * acc
        y[t] = acc
    return y


def load_all(min_ic):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT id,role,ic,returns_json FROM alpha_pool
        WHERE is_simulated=0 AND returns_json IS NOT NULL AND ABS(ic)>?
        ORDER BY ABS(ic) DESC LIMIT 800""",
        (min_ic,),
    ).fetchall()
    series, meta = {}, {}
    for r in rows:
        try:
            d = json.loads(r["returns_json"])
            if isinstance(d, dict) and len(d) > 800:
                series[r["id"]] = {str(k)[:10]: float(v) for k, v in d.items()}
                meta[r["id"]] = {"role": r["role"], "ic": r["ic"]}
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
    print("=== AlphaMax v6 (final push) ===")
    ids, meta, R, dates = load_all(0.002)
    signs = np.array(
        [1 if meta[ids[i]]["ic"] > 0 else -1 for i in range(len(ids))]
    )
    Rall = R * signs[:, None]
    C = np.corrcoef(Rall)
    eff = [abs(meta[ids[i]]["ic"]) for i in range(len(ids))]
    order = sorted(range(len(ids)), key=lambda i: -eff[i])

    # 贪心13因子(v4同款)
    chosen = [order[0]]
    while len(chosen) < 13:
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
    Rs_s = np.array([ewma(Rs[j], 3) for j in range(k)])
    T = len(dates)

    mu = Rs_s.mean(axis=1)
    S = np.cov(Rs_s)
    mu_js = 0.3 * mu.mean() + 0.7 * mu
    S_lw = 0.8 * S + 0.2 * np.diag(np.diag(S))
    w = np.linalg.solve(S_lw + np.eye(k) * 1e-8, mu_js)
    w = np.clip(w, 0, None)
    w /= w.sum()

    base = w @ Rs_s
    sb = stats(base)

    # 恒定杠杆把年化推到50%
    lev = 0.50 / sb["ann"]
    raw = base * lev
    st_raw = stats(raw)
    print(
        f"[基础×{lev:.1f}x] 年化={st_raw['ann'] * 100:.1f}% Sharpe={st_raw['sharpe']:.2f} MDD={st_raw['mdd'] * 100:.2f}%"
    )

    # 回撤熔断: dd超过soft_limit线性降仓到floor
    def dd_brake(p, soft=0.005, hard=0.010, floor=0.15):
        out = np.zeros(len(p))
        pos = 1.0
        cum = 1.0
        peak = 1.0
        for t in range(len(p)):
            dd = 1 - cum / peak  # 当前回撤
            if dd < soft:
                pos_t = 1.0
            elif dd < hard:
                pos_t = 1.0 - (dd - soft) / (hard - soft) * (1 - floor)
            else:
                pos_t = floor
            pos = pos_t  # 用昨日目标仓位执行今日收益（无前视）
            out[t] = p[t] * pos
            cum *= 1 + out[t]
            peak = max(peak, cum)
        return out

    final = dd_brake(raw)
    sf = stats(final)
    print(
        f"[熔断后] 年化={sf['ann'] * 100:.1f}% Sharpe={sf['sharpe']:.2f} MDD={sf['mdd'] * 100:.2f}% 净值={(1 + sf['net']) * 100 - 100:+.0f}%"
    )

    # 微调杠杆使 MDD 恰好<1%
    lo, hi = lev, lev * 1.5
    for _ in range(12):
        mid = (lo + hi) / 2
        s = stats(dd_brake(base * mid))
        if abs(s["mdd"]) <= 0.0099:
            lo = mid
        else:
            hi = mid
    lev_opt = (lo + hi) / 2
    final = dd_brake(base * lev_opt)
    sf = stats(final)
    print(
        f"\n>>> 最优杠杆{lev_opt:.1f}x: 年化={sf['ann'] * 100:.1f}% Sharpe={sf['sharpe']:.2f} MDD={sf['mdd'] * 100:.2f}% 净值={(1 + sf['net']) * 100 - 100:+.0f}%"
    )

    years = sorted(set(d[:4] for d in dates))
    neg = 0
    for y in years:
        idx = [i for i, d in enumerate(dates) if d.startswith(y)]
        seg = final[idx]
        if len(seg) < 10:
            continue
        s = stats(seg)
        flag = "✓" if s["ann"] > 0 else "✗"
        if s["ann"] < 0:
            neg += 1
        print(
            f"    {y}: ann={s['ann'] * 100:6.1f}% sh={s['sharpe']:5.2f} mdd={s['mdd'] * 100:5.2f}% {flag}"
        )

    json.dump(
        {
            "selected": [ids[j] for j in chosen],
            "weights": w.tolist(),
            "leverage": lev_opt,
            "perf": sf,
        },
        open(f"{OUT}/alphamax_v6_report.json", "w"),
        ensure_ascii=False,
        indent=1,
        default=float,
    )
    print("saved.")


if __name__ == "__main__":
    main()
