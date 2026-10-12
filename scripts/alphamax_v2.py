#!/usr/bin/env python
"""AlphaMax v2: 更激进——
 1. 池子放宽到 IC>=0 (全部真实回测因子, 含负IC做空)
 2. 前向选择 + MVO 迭代精修
 3. 日频波动率目标(动态杠杆) —— Sharpe不变, 但把MDD压到目标内再放大收益
 4. 多组合叠加: 因子层+策略层混合
目标诊断: 50%ann / SH7 / MDD<1% 需要什么结构
"""

import json
import math
import sqlite3
import sys

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


def load_all():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT id, role, ic, rank_ic, returns_json FROM alpha_pool
        WHERE is_simulated=0 AND returns_json IS NOT NULL AND ABS(ic) > 0.004
        ORDER BY ABS(ic) DESC LIMIT 400""").fetchall()
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


def vol_target(port, target=0.10, lookback=20):
    """日频波动率目标化: 每天按过去lookback日已实现波动调整仓位"""
    T = len(port)
    out = np.zeros(T)
    pos = 1.0
    for t in range(T):
        out[t] = port[t] * pos
        lo = max(0, t - lookback)
        rv = port[lo : t + 1].std() * math.sqrt(252) if t > 5 else 0.15
        if rv > 0:
            pos = min(target / rv, 10.0)  # 杠杆上限10x
    return out


def main():
    print("=== AlphaMax v2 ===")
    ids, meta, R, dates = load_all()
    T = len(dates)
    print(f"[1] 全池(|IC|>0.4%): {len(ids)} 因子, {T} 天")
    C = np.corrcoef(R)

    # 负IC因子取反向(做空方向), 提升有效池
    signs = np.array(
        [1 if meta[ids[i]]["ic"] > 0 else -1 for i in range(len(ids))]
    )
    R_signed = R * signs[:, None]
    eff_ic = [abs(meta[ids[i]]["ic"]) for i in range(len(ids))]
    order = sorted(range(len(ids)), key=lambda i: -eff_ic[i])

    # 贪心前向最大化Sharpe (用signed收益)
    chosen = [order[0]]
    while len(chosen) < 30:
        best_i, best_sh = None, -9e9
        for i in order:
            if i in chosen or any(abs(C[i][j]) >= 0.3 for j in chosen):
                continue
            cand = chosen + [i]
            w = np.ones(len(cand)) / len(cand)
            s = stats(w @ R_signed[cand])["sharpe"]
            if s > best_sh:
                best_sh, best_i = s, i
        if (
            best_i is None
            or best_sh
            <= stats(np.ones(len(chosen)) / len(chosen) @ R_signed[chosen])[
                "sharpe"
            ]
        ):
            break
        chosen.append(best_i)
    k = len(chosen)
    print(f"[2] 选出 {k} 个 (含做空方向)")

    # MVO 精修 (样本内)
    Rs = R_signed[chosen]
    mu = Rs.mean(axis=1)
    S = np.cov(Rs)
    Sinv = np.linalg.inv(S + np.eye(k) * 1e-6)
    w_mv = Sinv @ mu
    w_mv = np.clip(w_mv, 0, None)  # 只做多权重(已含sign翻转)
    w_mv = w_mv / w_mv.sum()
    base = w_mv @ Rs
    st0 = stats(base)
    print(
        f"[3] MVO组合: 年化={st0['ann'] * 100:.1f}% Sharpe={st0['sharpe']:.2f} MDD={st0['mdd'] * 100:.2f}%"
    )

    # 波动率目标化 → 压回撤
    vt = vol_target(base, target=0.08)
    st_vt = stats(vt)
    print(
        f"[4] 波动率目标8%(动态杠杆): 年化={st_vt['ann'] * 100:.1f}% Sharpe={st_vt['sharpe']:.2f} MDD={st_vt['mdd'] * 100:.2f}%"
    )

    # 杠杆推到50%年化, 看MDD和Sharpe
    lev = 0.50 / st_vt["ann"] if st_vt["ann"] > 0 else 99
    final = vt * lev
    st_f = stats(final)
    print(
        f"[5] 推到50%年化(需{lev:.2f}x): 年化={st_f['ann'] * 100:.1f}% Sharpe={st_f['sharpe']:.2f} MDD={st_f['mdd'] * 100:.2f}%"
    )

    # 分年度稳定性
    years = sorted(set(d[:4] for d in dates))
    print("[6] 分年度:")
    for y in years:
        idx = [i for i, d in enumerate(dates) if d.startswith(y)]
        seg = final[idx]
        if len(seg) < 10:
            continue
        s = stats(seg)
        print(
            f"    {y}: ann={s['ann'] * 100:6.1f}% sh={s['sharpe']:5.2f} mdd={s['mdd'] * 100:5.2f}%"
        )

    # 成分
    print("[7] 成分:")
    for j, wt in sorted(zip(chosen, w_mv), key=lambda x: -x[1])[:12]:
        m = meta[ids[j]]
        d = "空" if signs[j] < 0 else "多"
        print(
            f"    {wt * 100:5.1f}% [{d}] IC={m['ic']:+.4f} {m['role'][:14]} {ids[j][:16]}"
        )

    json.dump(
        {
            "selected": [ids[j] for j in chosen],
            "signs": signs[chosen].tolist(),
            "weights": w_mv.tolist(),
            "perf_mvo": st0,
            "perf_voltarget": st_vt,
            "leverage_for_50": lev,
            "perf_final_50": st_f,
            "dates_span": [dates[0], dates[-1]],
        },
        open(f"{OUT}/alphamax_v2_report.json", "w"),
        ensure_ascii=False,
        indent=1,
        default=float,
    )
    print(f"\nsaved -> alphamax_v2_report.json")


if __name__ == "__main__":
    main()
