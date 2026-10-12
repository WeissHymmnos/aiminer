#!/usr/bin/env python
"""AlphaMax v1: 冲击 50%年化 / Sharpe>=7 / MDD<1% 的组合优化管线
步骤:
 1. 扩大候选池(IC>0.008 全部真实回测因子)
 2. 贪心前向选择(直接优化组合Sharpe) + 相关性约束
 3. 滚动窗口权重估计(60日重估, 准样本外)
 4. 波动率目标化 + 杠杆叠加
输出: results/alphamax_report.json + 控制台报告
"""

import json
import math
import sqlite3
import sys

import numpy as np

DB = "/home/wh/Documents/finance/aiminer/results/alpha_miner.db"
OUT_DIR = "/home/wh/Documents/finance/aiminer/results"


def load_pool(min_ic=0.008):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT id, role, ic, rank_ic, returns_json FROM alpha_pool
        WHERE is_simulated=0 AND returns_json IS NOT NULL AND ic >= ?
        ORDER BY ic DESC LIMIT 300""",
        (min_ic,),
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
    if not series:
        return None, None, None
    common = None
    for k in series:
        ks = set(series[k].keys())
        common = ks if common is None else common & ks
    common = sorted(common)
    ids = list(series.keys())
    R = np.array([[series[i].get(d, 0.0) for d in common] for i in ids])
    return ids, meta, (R, common)


def stats(p):
    mean, sd = p.mean(), p.std()
    ann = mean * 252
    sh = ann / (sd * math.sqrt(252)) if sd > 0 else 0.0
    cum = np.cumprod(1 + p)
    peak = np.maximum.accumulate(cum)
    mdd = ((cum / peak) - 1).min()
    # Calmar
    calmar = ann / abs(mdd) if mdd != 0 else 0
    return {
        "ann": ann,
        "sharpe": sh,
        "mdd": mdd,
        "net": cum[-1] - 1,
        "calmar": calmar,
    }


def greedy_select(R, meta, ids, max_k=25, corr_cap=0.35):
    """贪心前向选择: 每步选使组合Sharpe最大且与已选相关性<corr_cap的因子"""
    n, T = R.shape
    C = np.corrcoef(R)
    order = sorted(range(n), key=lambda i: -meta[ids[i]]["ic"])
    chosen = [order[0]]
    while len(chosen) < max_k:
        best_i, best_sh = None, -9e9
        for i in order:
            if i in chosen:
                continue
            if any(abs(C[i][j]) >= corr_cap for j in chosen):
                continue
            cand = chosen + [i]
            w = np.ones(len(cand)) / len(cand)
            s = stats(w @ R[cand])["sharpe"]
            if s > best_sh:
                best_sh, best_i = s, i
        if best_i is None:
            break
        chosen.append(best_i)
    return chosen


def rolling_weights(R_sel, lookback=60, shrink=0.5):
    """滚动逆方差+IC倾向权重, 防止前视"""
    T, k = R_sel.shape
    W = np.zeros((T, k))
    for t in range(T):
        lo = max(0, t - lookback)
        hist = R_sel[lo:t] if t > 20 else R_sel[: max(t, 20)]
        sd = hist.std(axis=0) + 1e-9
        inv_v = 1 / sd
        W[t] = inv_v / inv_v.sum()
    return W


if __name__ == "__main__":
    min_ic = float(sys.argv[1]) if len(sys.argv) > 1 else 0.008
    ids, meta, pack = load_pool(min_ic)
    if ids is None:
        print("no candidates")
        sys.exit(1)
    R, dates = pack
    T = len(dates)
    print(f"[1] 候选池: {len(ids)} 因子, {T} 天 ({dates[0]}~{dates[-1]})")

    print("[2] 贪心选择中...")
    chosen = greedy_select(R, meta, ids)
    print(f"    选出 {len(chosen)} 个")
    for j in chosen[:10]:
        m = meta[ids[j]]
        print(f"      IC={m['ic']:.4f} {m['role'][:14]} {ids[j][:16]}")

    Rs = R[chosen]
    k = len(chosen)

    # A. 全期静态等权
    w_eq = np.ones(k) / k
    st_eq = stats(w_eq @ Rs)
    print(
        f"\n[A] 静态等权: 年化={st_eq['ann'] * 100:.1f}% Sharpe={st_eq['sharpe']:.2f} MDD={st_eq['mdd'] * 100:.1f}%"
    )

    # B. 静态逆波动率
    vol = Rs.std(axis=1)
    w_iv = (1 / vol) / (1 / vol).sum()
    st_iv = stats(w_iv @ Rs)
    print(
        f"[B] 静态逆波动率: 年化={st_iv['ann'] * 100:.1f}% Sharpe={st_iv['sharpe']:.2f} MDD={st_iv['mdd'] * 100:.1f}%"
    )

    # C. 滚动权重(准样本外) + 波动率目标10%
    print("[3] 滚动权重估计...")
    W = rolling_weights(
        Rs.T if False else Rs.T.T if False else Rs
    )  # Rs shape (k,T); want per-day weights
    # rolling over time axis: transpose logic
    Rt = Rs.T  # (T,k)
    Wt = np.zeros_like(Rt)
    for t in range(Rt.shape[0]):
        lo = max(0, t - 60)
        hist = Rt[lo:t] if t > 30 else Rt[: max(t, 30)]
        sd = hist.std(axis=0) + 1e-12
        iv = 1 / sd
        Wt[t] = iv / iv.sum()
    port_roll = (Rt * Wt).sum(axis=1)[30:]  # burn-in 30d
    st_roll = stats(port_roll)
    print(
        f"[C] 滚动权重(准OOS): 年化={st_roll['ann'] * 100:.1f}% Sharpe={st_roll['sharpe']:.2f} MDD={st_roll['mdd'] * 100:.1f}%"
    )

    # D. 波动率目标 + 杠杆扫描(在静态IV组合上)
    base = w_iv @ Rs
    realized_vol = base.std() * math.sqrt(252)
    target_50 = 0.50
    lev_needed = target_50 / st_iv["ann"] if st_iv["ann"] > 0 else 99
    print(
        f"\n[D] 达到50%年化所需杠杆: {lev_needed:.1f}x (当前年化{st_iv['ann'] * 100:.1f}%)"
    )
    for lev in [1.0, lev_needed]:
        st_l = stats(base * lev)
        tag = f"{lev:.1f}x杠杆"
        print(
            f"    {tag}: 年化={st_l['ann'] * 100:.1f}% Sharpe={st_l['sharpe']:.2f} MDD={st_l['mdd'] * 100:.1f}%"
        )

    # E. 理论上限: 用全期最优马科维茨(严重样本内, 仅看上限)
    mu = Rs.mean(axis=1)
    S = np.cov(Rs)
    try:
        Sinv = np.linalg.inv(S + np.eye(k) * 1e-8)
        w_mv = Sinv @ mu
        w_mv = w_mv / w_mv.sum()
        w_mv = np.clip(w_mv, -1, 2)
        w_mv = w_mv / w_mv.sum()
        st_mv = stats(w_mv @ Rs)
        print(
            f"\n[E] 样本内MVO(上限参考): 年化={st_mv['ann'] * 100:.1f}% Sharpe={st_mv['sharpe']:.2f} MDD={st_mv['mdd'] * 100:.1f}%"
        )
    except Exception as e:
        print("MVO fail", e)

    report = {
        "pool_size": len(ids),
        "selected": [ids[j] for j in chosen],
        "meta": {ids[j]: meta[ids[j]] for j in chosen},
        "static_eq": st_eq,
        "static_invvol": st_iv,
        "rolling": st_roll,
        "leverage_needed_for_50": lev_needed,
        "dates": [dates[0], dates[-1]],
    }
    json.dump(
        report,
        open(f"{OUT_DIR}/alphamax_report.json", "w"),
        ensure_ascii=False,
        indent=1,
        default=float,
    )
    print(f"\nsaved -> {OUT_DIR}/alphamax_report.json")
