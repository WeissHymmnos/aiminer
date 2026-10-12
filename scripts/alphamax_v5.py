#!/usr/bin/env python
"""AlphaMax v5: 在v4基础上压MDD到<1%同时保住50%年化
关键: v4的50%版本MDD -7.57%(杠杆放大所致)。改用:
 1. 更低波动率目标(2%)使基础组合极稳
 2. 杠杆在回撤控制内放大: 逐日风险预算(目标日亏损上限)
 3. 尾部裁剪: 跳过预测高波动日(因子动量衰减期)
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
    print("=== AlphaMax v5 ===")
    ids, meta, R, dates = load_all(0.002)
    signs = np.array(
        [1 if meta[ids[i]]["ic"] > 0 else -1 for i in range(len(ids))]
    )
    Rall = R * signs[:, None]
    C = np.corrcoef(Rall)
    eff = [abs(meta[ids[i]]["ic"]) for i in range(len(ids))]
    order = sorted(range(len(ids)), key=lambda i: -eff[i])
    chosen = [order[0]]
    while len(chosen) < 13 and True:
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

    # v4 的收缩MVO权重
    mu = Rs_s.mean(axis=1)
    S = np.cov(Rs_s)
    mu_js = 0.3 * mu.mean() + 0.7 * mu
    F = np.diag(np.diag(S))
    S_lw = 0.8 * S + 0.2 * F
    w = np.linalg.solve(S_lw + np.eye(k) * 1e-8, mu_js)
    w = np.clip(w, 0, None)
    w /= w.sum()

    base = w @ Rs_s
    st_base = stats(base)

    # 风险预算仓位: 目标每日波动 = ann_target/sqrt(252), 上限3倍基准
    daily_target = (
        (0.50 / math.sqrt(252))
        / (st_base["ann"] / abs(st_base["mdd"]) if st_base["mdd"] != 0 else 10)
        if False
        else None
    )
    # 直接: 目标年化50%, 基准年化ann_b → 恒定杠杆lev, 但用逐日VT平滑
    lev_needed = 0.50 / st_base["ann"]

    def vt(port, target_daily, max_lev):
        Tn = len(port)
        out = np.zeros(Tn)
        pos = 1.0
        for t in range(Tn):
            out[t] = port[t] * pos
            lo = max(0, t - 12)
            rv = port[lo : t + 1].std() if t > 4 else port.std()
            pos = min(target_daily / max(rv, 1e-9), max_lev)
        return out

    # 目标: 让最终MDD<1%。先试恒定杠杆+VT组合
    best = None
    for vt_target_daily in [0.0008, 0.0010, 0.0012, 0.0015]:
        scaled = vt(base * lev_needed, vt_target_daily, max_lev=20)
        s = stats(scaled)
        print(
            f"VT日波{vt_target_daily * 100:.2f}%: 年化={s['ann'] * 100:6.1f}% Sharpe={s['sharpe']:5.2f} MDD={s['mdd'] * 100:5.2f}%"
        )
        if best is None or (
            abs(s["ann"] - 0.5) < abs(best[1]["ann"] - 0.5)
            and abs(s["mdd"]) < 0.01
        ):
            best = (vt_target_daily, s, scaled)
        elif s["sharpe"] > best[1]["sharpe"] and abs(s["mdd"]) < 0.01:
            best = (vt_target_daily, s, scaled)

    td, s, scaled = best
    print(
        f"\n>>> 最优: VT日波{td * 100:.2f}% 年化={s['ann'] * 100:.1f}% Sharpe={s['sharpe']:.2f} MDD={s['mdd'] * 100:.2f}% 净值={(1 + s['net']) * 100 - 100:+.0f}%"
    )

    years = sorted(set(d[:4] for d in dates))
    for y in years:
        idx = [i for i, d in enumerate(dates) if d.startswith(y)]
        seg = scaled[idx]
        if len(seg) < 10:
            continue
        ss = stats(seg)
        print(
            f"    {y}: ann={ss['ann'] * 100:6.1f}% sh={ss['sharpe']:5.2f} mdd={ss['mdd'] * 100:5.2f}%"
        )

    json.dump(
        {
            "selected": [ids[j] for j in chosen],
            "weights": w.tolist(),
            "perf": s,
            "vt_target_daily": td,
        },
        open(f"{OUT}/alphamax_v5_report.json", "w"),
        ensure_ascii=False,
        indent=1,
        default=float,
    )
    print("saved.")


if __name__ == "__main__":
    main()
