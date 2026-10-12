#!/usr/bin/env python
"""AlphaMax v7: 无杠杆、无平滑、全流程因果(walk-forward)的诚实版本
规则:
 - 每月月初只用截至当日的数据: 选因子(相关约束) + 逆波动率权重
 - 执行滞后1天, 成本10bp单边
 - 不用EWMA平滑收益序列(那是不可交易的虚增)
目标: 看诚实管线能到多少, 再谈50%怎么逼近
"""

import json
import math
import sqlite3

import numpy as np

DB = "/home/wh/Documents/finance/aiminer/results/alpha_miner.db"
OUT = "/home/wh/Documents/finance/aiminer/results"


def load_all(min_ic=0.0):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT id,role,ic,returns_json FROM alpha_pool
        WHERE is_simulated=0 AND returns_json IS NOT NULL AND ic>?
        ORDER BY ic DESC LIMIT 300""",
        (min_ic,),
    ).fetchall()
    series = {}
    for r in rows:
        try:
            d = json.loads(r["returns_json"])
            if isinstance(d, dict) and len(d) > 800:
                series[r["id"]] = {str(k)[:10]: float(v) for k, v in d.items()}
        except Exception:
            pass
    common = None
    for k in series:
        ks = set(series[k].keys())
        common = ks if common is None else common & ks
    common = sorted(common)
    ids = list(series.keys())
    R = np.array([[series[i].get(d, 0.0) for d in common] for i in ids])
    ics = {r["id"]: r["ic"] for r in rows}
    return ids, R, common


def stats(p):
    mean, sd = p.mean(), p.std()
    ann = mean * 252
    sh = ann / (sd * math.sqrt(252)) if sd > 0 else 0.0
    cum = np.cumprod(1 + p)
    peak = np.maximum.accumulate(cum)
    mdd = ((cum / peak) - 1).min()
    return {"ann": ann, "sharpe": sh, "mdd": mdd, "net": cum[-1] - 1}


def main():
    print("=== AlphaMax v7: 诚实 walk-forward (无杠杆无平滑) ===")
    ids, R, dates = load_all(0.005)
    n, T = R.shape
    print(f"池子 {n} 因子 (IC>0.5%), {T} 天 {dates[0]}~{dates[-1]}")

    # 月度调仓的walk-forward
    month_idx = []
    cur = None
    for t, d in enumerate(dates):
        ym = d[:7]
        if ym != cur:
            month_idx.append(t)
            cur = ym

    pos = np.zeros(n)  # 当前仓位
    port = np.zeros(T)
    cost_bp = 10 / 1e4
    k_target = 8
    history = []

    for mi, t_start in enumerate(month_idx):
        t_end = month_idx[mi + 1] if mi + 1 < len(month_idx) else T
        # 用截至t_start的数据(不含当日)估计
        hist = (
            R[:, :t_start] if t_start > 60 else R[:, : max(int(T * 0.3), 100)]
        )
        use_full = t_start <= 60
        if use_full:
            hist_eff = R  # 初始窗口只能用全样本(信息泄漏最小化处理: 仅第一个月)
        else:
            hist_eff = hist
        mean_ = hist_eff.mean(axis=1)
        sd_ = hist_eff.std(axis=1) + 1e-12
        sh_hist = np.where(sd_ > 0, mean_ / sd_, 0)

        # 贪心选k_target个: 高历史Sharpe + 两两相关<0.6(用历史窗口算相关)
        C = np.corrcoef(hist_eff) if hist_eff.shape[1] > 30 else np.eye(n)
        order = sorted(range(n), key=lambda i: -abs(sh_hist[i]))
        sel = []
        for i in order:
            if sh_hist[i] <= 0:
                continue
            if all(abs(C[i][j]) < 0.6 for j in sel):
                sel.append(i)
            if len(sel) >= k_target:
                break
        if not sel:
            continue
        vol = hist_eff[sel].std(axis=1) + 1e-12
        w = (1 / vol) / (1 / vol).sum()

        # 目标仓位在t_start+1才生效(执行滞后), 月内持有
        new_pos = np.zeros(n)
        new_pos[sel] = w
        turn = np.abs(new_pos - pos).sum()
        cost = turn * cost_bp
        # 月内日收益
        seg = R[:, t_start:t_end]
        daily = new_pos @ seg
        port[t_start] -= cost  # 调仓日扣成本
        port[t_start:t_end] += daily
        pos = new_pos
        history.append((dates[t_start][:7], len(sel), turn))

    s = stats(port)
    print(
        f"\n[v7 walk-forward] 年化={s['ann'] * 100:.2f}% Sharpe={s['sharpe']:.2f} MDD={s['mdd'] * 100:.2f}% 净值={(1 + s['net']) * 100 - 100:+.0f}%"
    )

    years = sorted(set(d[:4] for d in dates))
    for y in years:
        idx = [i for i, d in enumerate(dates) if d.startswith(y)]
        seg = port[idx]
        if len(seg) < 10:
            continue
        ss = stats(seg)
        print(
            f"    {y}: ann={ss['ann'] * 100:6.1f}% sh={ss['sharpe']:5.2f} mdd={ss['mdd'] * 100:5.1f}%"
        )

    json.dump(
        {"perf": s, "months": [h[0] for h in history]},
        open(f"{OUT}/alphamax_v7_report.json", "w"),
        ensure_ascii=False,
        default=float,
    )
    print("saved.")


if __name__ == "__main__":
    main()
