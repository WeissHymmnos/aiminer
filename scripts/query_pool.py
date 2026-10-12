#!/usr/bin/env python3
"""Query AIMiner factor pool and strategy pool for status reports.

Usage:
    cd /home/wh/Documents/finance/aiminer
    python scripts/query_pool.py
"""

import sqlite3

DB_PATH = "results/alpha_miner.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM alpha_pool")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM alpha_pool WHERE is_simulated=0")
    real = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM alpha_pool WHERE is_simulated=0 AND ic > 0.02"
    )
    valid = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM alpha_pool WHERE is_simulated=0 AND ic > 0.05"
    )
    excellent = c.fetchone()[0]

    c.execute(
        "SELECT role_norm, SUM(cnt), ROUND(AVG(avg_ic),4), ROUND(MAX(max_ic),4), SUM(valid) "
        "FROM (SELECT CASE WHEN length(role)>20 THEN '遗传交叉' ELSE role END as role_norm, "
        "COUNT(*) as cnt, AVG(ic) as avg_ic, MAX(ic) as max_ic, "
        "SUM(CASE WHEN ic>0.02 THEN 1 ELSE 0 END) as valid "
        "FROM alpha_pool WHERE is_simulated=0 GROUP BY role_norm) "
        "GROUP BY role_norm ORDER BY MAX(max_ic) DESC"
    )
    roles = c.fetchall()

    c.execute(
        "SELECT id, hypothesis, CASE WHEN length(role)>20 THEN '遗传交叉' ELSE role END, "
        "ROUND(ic,4), ROUND(rank_ic,4), "
        "ROUND(COALESCE(json_extract(metrics_json,'$.sharpe'), json_extract(metrics_json,'$.sharpe_ratio')),2), "
        "ROUND(json_extract(metrics_json,'$.max_drawdown'),2) "
        "FROM alpha_pool WHERE is_simulated=0 ORDER BY CAST(ic AS REAL) DESC LIMIT 10"
    )
    top_factors = c.fetchall()

    c.execute("SELECT COUNT(*) FROM strategy_backtests")
    strat_total = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM strategy_backtests "
        "WHERE CAST(COALESCE(json_extract(metrics_json,'$.sharpe'), "
        "json_extract(metrics_json,'$.sharpe_ratio')) AS REAL) > 0.5"
    )
    strat_good = c.fetchone()[0]

    c.execute(
        "SELECT strategy_id, template_name, "
        "ROUND(CAST(json_extract(metrics_json,'$.annualized_return') AS REAL)*100,1), "
        "ROUND(CAST(COALESCE(json_extract(metrics_json,'$.sharpe'), "
        "json_extract(metrics_json,'$.sharpe_ratio')) AS REAL),2), "
        "ROUND(CAST(json_extract(metrics_json,'$.max_drawdown') AS REAL)*100,1), "
        "ROUND(CAST(json_extract(metrics_json,'$.win_rate') AS REAL)*100,1) "
        "FROM strategy_backtests WHERE template_name IS NOT NULL AND source_factor_id IS NOT NULL "
        "ORDER BY CAST(COALESCE(json_extract(metrics_json,'$.sharpe'), "
        "json_extract(metrics_json,'$.sharpe_ratio')) AS REAL) DESC LIMIT 10"
    )
    top_strats = c.fetchall()

    c.execute("SELECT COUNT(*) FROM portfolio_pool")
    port_total = c.fetchone()[0]

    print("=== 因子池 ===")
    print(
        f"总计: {total} | 真实回测: {real} | 有效(IC>0.02): {valid} | 优秀(IC>0.05): {excellent}"
    )
    print()
    print("=== 各角色贡献 ===")
    for r in roles:
        print(
            f"  {r[0]:12s}  数量={r[1]:3d}  平均IC={r[2]:.4f}  最高IC={r[3]:.4f}  有效={r[4]}"
        )
    print()
    print("=== Top 10 因子 (按IC) ===")
    for f in top_factors:
        hyp = str(f[1])[:50] if f[1] else ""
        print(
            f"  {str(f[0])[:18]:18s}  {str(f[2]):10s}  IC={f[3]:.4f}  RankIC={f[4]:.4f}  Sharpe={f[5]}  MDD={f[6]}  {hyp}"
        )
    print()
    print("=== 策略回测 ===")
    print(f"总计: {strat_total} | Sharpe>0.5: {strat_good}")
    print()
    print("=== Top 10 策略 (按Sharpe) ===")
    for s in top_strats:
        print(
            f"  {str(s[0])[:24]:24s}  {str(s[1])[:18]:18s}  年化={s[2]}%  Sharpe={s[3]}  MDD={s[4]}%  胜率={s[5]}%"
        )
    print()
    print(f"=== 组合 ===")
    print(f"总计: {port_total}")
    conn.close()


if __name__ == "__main__":
    main()
