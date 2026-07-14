import os
import sqlite3
import json
import argparse
import pandas as pd
from loguru import logger
import uuid
import sys

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiminer.agents.portfolio_agent import PortfolioAgent
from aiminer.core.portfolio import construct_portfolio
from aiminer.core.settings import build_settings

def _serialize_returns(returns) -> dict:
    if returns is None or not hasattr(returns, "items"):
        return {}
    out = {}
    for k, v in returns.items():
        try:
            key = k.isoformat() if hasattr(k, "isoformat") else str(k)
            out[key] = float(v)
        except (TypeError, ValueError):
            continue
    return out

def run_portfolio_for_run(run_id: str = None):
    settings = build_settings()
    db_path = settings.db_path
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if not run_id:
            # Find the most recent run_id that has factors
            cursor.execute("SELECT run_id FROM alpha_pool ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                logger.error("No factors found in the database.")
                return
            run_id = row["run_id"]
            
        logger.info(f"Building portfolio for run_id: {run_id}")
        
        cursor.execute("SELECT id, hypothesis, metrics_json, returns_json FROM alpha_pool WHERE run_id = ?", (run_id,))
        rows = cursor.fetchall()
        
        if not rows:
            logger.error(f"No factors found for run_id: {run_id}")
            return
            
        factors_for_portfolio = []
        returns_dict = {}
        for row in rows:
            fid = row["id"]
            metrics = json.loads(row["metrics_json"] or "{}")
            returns_data = json.loads(row["returns_json"] or "{}")
            
            if not returns_data:
                continue
                
            ret_series = pd.Series(returns_data)
            ret_series.index = pd.to_datetime(ret_series.index, errors="coerce")
            ret_series = ret_series[ret_series.index.notna()].sort_index()
            
            if not ret_series.empty:
                returns_dict[fid] = ret_series
                factors_for_portfolio.append({
                    "id": fid,
                    "hypothesis": row["hypothesis"],
                    "metrics": metrics
                })
                
        if len(returns_dict) < 2:
            logger.error("Need at least 2 factors with returns to construct a portfolio.")
            return
            
        returns_df = pd.DataFrame(returns_dict)
        
        agent = PortfolioAgent()
        decision = agent.select_method(factors_for_portfolio, returns_df)
        
        logger.info(f"LLM decided method: {decision.method}")
        logger.info(f"Rationale: {decision.rationale}")
        
        portfolio_result = construct_portfolio(returns_dict, method=decision.method)
        div_ratio = portfolio_result["diversification_ratio"]
        logger.success(f"Portfolio constructed successfully. Diversification Ratio: {div_ratio:.4f}")
        
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_pool (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                method TEXT,
                rationale TEXT,
                weights_json TEXT,
                returns_json TEXT,
                diversification_ratio REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        pid = f"portfolio_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO portfolio_pool (id, run_id, method, rationale, weights_json, returns_json, diversification_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pid,
            run_id,
            decision.method,
            decision.rationale,
            json.dumps(portfolio_result["weights"], ensure_ascii=False),
            json.dumps(_serialize_returns(portfolio_result["portfolio_returns"]), ensure_ascii=False),
            float(div_ratio)
        ))
        conn.commit()
        logger.info(f"Saved portfolio {pid} to database.")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Factor Portfolio Constructor")
    parser.add_argument("--run-id", type=str, help="Specific run_id to build a portfolio for (defaults to latest)")
    args = parser.parse_args()
    
    run_portfolio_for_run(args.run_id)
