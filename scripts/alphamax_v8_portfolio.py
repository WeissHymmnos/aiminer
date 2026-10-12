#!/usr/bin/env python
"""AlphaMax v8: 每日 walk-forward 组合器 (诚实管线, 无杠杆)
从 alpha_pool 全库自动构建组合:
 - 每月用截至当日的历史数据选因子(历史Sharpe+相关约束)
 - 逆波动率加权, 执行滞后1天, 10bp成本
 - 输出当前应持有的因子与权重 -> results/current_portfolio.json
用法:
  python scripts/alphamax_v8_portfolio.py            # 全期回测
  python scripts/alphamax_v8_portfolio.py --live     # 输出当前持仓
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
    return {
        "ann": ann,
        "sharpe": sh,
        "mdd": ((cum / peak) - 1).min(),
        "net": cum[-1] - 1,
    }


def load(min_ic=0.005):
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
                series[r["id"]] = (
                    {"role": r["role"], "ic": r["ic"]},
                    {str(k)[:10]: float(v) for k, v in d.items()},
                )
        except Exception:
            pass
    common = None
    for k in series:
        ks = set(series[k][1].keys())
        common = ks if common is None else common & ks
    common = sorted(common)
    ids = list(series.keys())
    R = np.array([[series[i][1].get(d, 0.0) for d in common] for i in ids])
    return ids, {k: v[0] for k, v in series.items()}, R, common


def select(hist_R, k_target=8, corr_cap=0.6, min_hist=60):
    n = hist_R.shape[0]
    if hist_R.shape[1] < min_hist:
        return [], None
    mean_ = hist_R.mean(axis=1)
    sd_ = hist_R.std(axis=1) + 1e-12
    sh_h = np.where(sd_ > 0, mean_ / sd_, 0)
    C = np.corrcoef(hist_R)
    order = sorted(range(n), key=lambda i: -abs(sh_h[i]))
    sel = []
    for i in order:
        if sh_h[i] <= 0:
            continue
        if all(abs(C[i][j]) < corr_cap for j in sel):
            sel.append(i)
        if len(sel) >= k_target:
            break
    if not sel:
        return [], None
    vol = hist_R[sel].std(axis=1) + 1e-12
    w = (1 / vol) / (1 / vol).sum()
    return sel, w


def run_walkforward(ids, meta, R, dates, k_target=8, cost_bp=10.0, min_hist=60):
    n, T = R.shape
    month_idx = []
    cur = None
    for t, d in enumerate(dates):
        ym = d[:7]
        if ym != cur:
            month_idx.append(t)
            cur = ym
    port = np.zeros(T)
    pos = np.zeros(n)
    turns = []
    cost = cost_bp / 1e4
    for mi, ts in enumerate(month_idx):
        te = month_idx[mi + 1] if mi + 1 < len(month_idx) else T
        sel, w = select(
            R[:, :ts], k_target, min_hist=min_hist
        )  # 严格因果: 不含当月
        if not sel:
            continue
        new_pos = np.zeros(n)
        new_pos[sel] = w
        turn = np.abs(new_pos - pos).sum()
        turns.append(turn)
        seg = R[:, ts:te]
        port[ts] -= turn * cost
        port[ts:te] += new_pos @ seg
        pos = new_pos
    return port, history_summary(turns)


def history_summary(turns):
    return {
        "avg_monthly_turnover": float(np.mean(turns)) if turns else 0,
        "rebalances": len(turns),
    }


def live(ids, meta, R, dates, k_target=10):
    """输出当前(最后一天之后)应持组合"""
    sel, w = select(R, k_target=k_target)
    out = {
        "as_of": dates[-1],
        "components": [
            {
                "id": ids[j],
                "weight": round(float(w[i]), 4),
                "role": meta[ids[j]]["role"],
                "ic": meta[ids[j]]["ic"],
            }
            for i, j in enumerate(sel)
        ],
        "method": "walk_forward_invvol_corr06",
        "leverage": 1.0,
    }
    json.dump(
        out,
        open(f"{OUT}/current_portfolio.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    return out


if __name__ == "__main__":
    ids, meta, R, dates = load()
    print(f"池子 {len(ids)} 因子, {len(dates)} 天")
    if "--live" in sys.argv:
        out = live(ids, meta, R, dates)
        print(json.dumps(out, ensure_ascii=False, indent=1)[:1500])
    else:
        port, _ = run_walkforward(ids, meta, R, dates)
        s = stats(port)
        print(
            f"[v8 walk-forward] 年化={s['ann'] * 100:.2f}% Sharpe={s['sharpe']:.2f} MDD={s['mdd'] * 100:.2f}% 净值={(1 + s['net']) * 100 - 100:+.0f}%"
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
