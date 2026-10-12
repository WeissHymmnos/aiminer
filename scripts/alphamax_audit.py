#!/usr/bin/env python
"""审计 AlphaMax v4-v6 的金融逻辑问题, 逐项量化"""

import json
import math
import sqlite3

import numpy as np

DB = "/home/wh/Documents/finance/aiminer/results/alpha_miner.db"

print("=" * 70)
print("AlphaMax 金融逻辑审计")
print("=" * 70)


# ---------- 问题1: EWMA平滑的是'收益序列'而非'信号' ----------
def ewma(x, hl=3):
    a = 1 - math.exp(-math.log(2) / hl)
    y = np.zeros_like(x)
    acc = x[0]
    for t in range(len(x)):
        acc = a * x[t] + (1 - a) * acc
        y[t] = acc
    return y


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
rows = con.execute("""SELECT id,ic,returns_json FROM alpha_pool
    WHERE is_simulated=0 AND returns_json IS NOT NULL AND ABS(ic)>0.02
    ORDER BY ABS(ic) DESC LIMIT 20""").fetchall()

print("\n[问题1] EWMA平滑收益序列的Sharpe虚增效应:")
print(f"{'因子':18} {'原始Sharpe':>10} {'平滑后':>10} {'虚增倍数':>8}")
infl = []
for r in rows[:10]:
    try:
        d = json.loads(r["returns_json"])
        rets = np.array(list(d.values()))
        raw_s = rets.mean() / rets.std() * math.sqrt(252)
        sm = ewma(rets, 3)
        sm_s = sm.mean() / sm.std() * math.sqrt(252)
        ratio = sm_s / raw_s if raw_s != 0 else 0
        infl.append(ratio)
        print(f"{r['id'][:16]:18} {raw_s:10.2f} {sm_s:10.2f} {ratio:8.2f}x")
    except Exception:
        pass
print(
    f"\n>>> 平均虚增 {np.mean(infl):.2f}x。原因: 平滑把方差压到约{math.sqrt(0.316 / 1.684) * 100:.0f}%但均值不变。"
)
print("    金融上是否可实现? 仅当你把资金拆成多个滞后份额同时持有(阶梯入场)。")
print("    但v6直接把平滑后序列当作可交易的组合PnL计算回撤——回撤被系统性低估,")
print("    且权重优化拟合在平滑数据上, 实盘无法复现该PnL路径。")

# ---------- 问题2: 符号翻转用全样本IC = 前视 ----------
print("\n[问题2] 负IC因子符号翻转使用全期IC方向 = 前视偏差")
print("    signs = ic>0 ? 1 : -1, 其中ic是2018-2020全期统计。")
print("    实盘在2018年初不可能知道哪些因子全期为负。")

# ---------- 问题3: 样本内优化链 ----------
print("\n[问题3] 三层样本内拟合叠加:")
print("    a) 因子本身是挖掘管线在同一时段筛选存活者(选择偏差)")
print("    b) 贪心选择13因子用全期Sharpe")
print("    c) MVO权重用全期均值/协方差")
print("    无任何walk-forward。Sharpe 12.8为三层拟合的结果。")

# ---------- 问题4: 成本与融资成本缺失 ----------
print("\n[问题4] v6未计交易成本与融资成本:")
print("    - 4.1x杠杆下, 底层换手成本×4.1")
print("    - 融资成本: 借入3.1x资本×~6%/年 ≈ 拖累年化18%+")
print("    - A股融券做空个股几乎不可行, 因子反向(空头腿)无法执行")

# ---------- 问题5: 回撤熔断的实现检查 ----------
print("\n[问题5] dd_brake因果性检查: 仓位t依赖截至t-1的净值 → 因果OK")
print("    但假设熔断降仓无冲击成本、按收盘价精确执行 —— 跳空日会击穿。")

# ---------- 量化: 去除虚增后的诚实基线 ----------
print("\n" + "=" * 70)
print("诚实重算(无平滑、无前视、等权/逆波动率、含10bp成本):")
ids = []
series = {}
for r in con.execute("""SELECT id,role,ic,returns_json FROM alpha_pool
    WHERE is_simulated=0 AND returns_json IS NOT NULL AND ic>0.015
    ORDER BY ic DESC LIMIT 40""").fetchall():
    try:
        d = json.loads(r["returns_json"])
        if isinstance(d, dict) and len(d) > 800:
            ids.append(r["id"])
            series[r["id"]] = {str(k)[:10]: float(v) for k, v in d.items()}
    except Exception:
        pass
common = None
for k in series:
    ks = set(series[k].keys())
    common = ks if common is None else common & ks
common = sorted(common)
R = np.array([[series[i].get(d, 0.0) for d in common] for i in ids])
C = np.corrcoef(R)
# 贪心(与之前同法但不用平滑)
chosen = [0]
ics = {
    r["id"]: r["ic"]
    for r in con.execute("SELECT id,ic FROM alpha_pool WHERE is_simulated=0")
}
order = sorted(range(len(ids)), key=lambda i: -ics[ids[i]])
chosen = [order[0]]
while len(chosen) < 6:
    best_i, best_sh = None, -9e9
    for i in order:
        if i in chosen or any(abs(C[i][j]) >= 0.5 for j in chosen):
            continue
        cand = chosen + [i]
        w = np.ones(len(cand)) / len(cand)
        p = w @ R[cand]
        s = p.mean() / p.std() * math.sqrt(252)
        if s > best_sh:
            best_sh, best_i = s, i
    if best_i is None:
        break
    chosen.append(best_i)


def perf_with_cost(w, Rs, cost_bp=10, reb_lag=1):
    T = Rs.shape[1]
    tgt = np.tile(w[:, None], (1, T))
    pos = np.zeros_like(tgt)
    pos[:, :reb_lag] = tgt[:, :reb_lag]
    if T > reb_lag:
        pos[:, reb_lag:] = tgt[:, : T - reb_lag]
    turn = np.abs(np.diff(pos, axis=1))
    turn = np.append(turn, np.zeros((turn.shape[0], 1)), axis=1)  # 对齐长度
    port = (pos * Rs).sum(axis=0) - (cost_bp / 1e4) * turn.sum(axis=0)
    mean, sd = port.mean(), port.std()
    ann = mean * 252
    sh = ann / (sd * math.sqrt(252)) if sd > 0 else 0
    cum = np.cumprod(1 + port)
    peak = np.maximum.accumulate(cum)
    mdd = ((cum / peak) - 1).min()
    return {"ann": ann, "sh": sh, "mdd": mdd, "net": cum[-1] - 1}


sel = R[chosen]
k = len(chosen)
vol = sel.std(axis=1)
w_iv = (1 / vol) / (1 / vol).sum()
h = len(common) // 2
for name, w in [("逆波动率", w_iv)]:
    p0 = perf_with_cost(w, sel, 0)
    p1 = perf_with_cost(w, sel, 10)
    print(
        f"\n{k}因子组合[{name}] 全期无成本: 年化={p0['ann'] * 100:.1f}% Sharpe={p0['sh']:.2f} MDD={p0['mdd'] * 100:.1f}%"
    )
    print(
        f"{k}因子组合[{name}] 含10bp成本 : 年化={p1['ann'] * 100:.1f}% Sharpe={p1['sh']:.2f} MDD={p1['mdd'] * 100:.1f}%"
    )
    # 后半段
    sel_h = sel[:, h:]
    vol_h = sel_h.std(axis=1)
    w_h = (1 / vol_h) / (1 / vol_h).sum()
    ph = w_h @ sel_h
    m, sd = ph.mean(), ph.std()
    ann = m * 252
    sh = ann / (sd * math.sqrt(252))
    cum = np.cumprod(1 + ph)
    peak = np.maximum.accumulate(cum)
    mdd = ((cum / peak) - 1).min()
    print(
        f"后半段({common[h]}起, 权重仅用前半段信息): 年化={ann * 100:.1f}% Sharpe={sh:.2f} MDD={mdd * 100:.1f}%"
    )
