import asyncio
import json
import os

# Disable default loguru stderr logging to prevent TUI corruption by child processes
os.environ["LOGURU_AUTOINIT"] = "False"

import sqlite3
import subprocess
import tempfile
import time
import multiprocessing
import threading
import traceback
from datetime import datetime
from pathlib import Path
import psutil

from loguru import logger
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Checkbox,
)
from textual_plotext import PlotextPlot

# Import core backend directly to make TUI standalone
from core import manual_runner
from core.strategy import StrategyConfig, strategy_templates
from manager import PortfolioManager


def _db_connect(path: str):
    """WAL-enabled read connection — won't block swarm writes."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def run_manager_process(kwargs, log_queue, parallel):
    try:
        # Custom sink for loguru in this process
        def tui_sink(message):
            rec = message.record
            log_queue.put({
                "level": rec["level"].name,
                "message": rec["message"],
                "role": rec.get("extra", {}).get("role", "System")
            })
        
        logger.remove()
        logger.add(tui_sink, level="INFO")
        
        manager = PortfolioManager(**kwargs)
        manager.dispatch_tasks(log_queue=log_queue)
        manager.run_swarm(parallel=parallel)
        
        log_queue.put({"level": "SUCCESS", "message": "Swarm execution completed!", "role": "System"})
    except Exception as e:
        log_queue.put({"level": "ERROR", "message": f"Swarm Error: {e}", "role": "System"})
        log_queue.put({"level": "ERROR", "message": traceback.format_exc(), "role": "System"})
    finally:
        log_queue.put(None)


class TUIApp(App):
    CSS_PATH = "tui.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("e", "edit_code", "Edit code (Nvim)"),
        ("r", "run_backtest", "Run Backtest"),
        ("j", "vim_down", "Down"),
        ("k", "vim_up", "Up"),
        ("h", "vim_left", "Left"),
        ("l", "vim_right", "Right"),
    ]

    def __init__(self, manager_ctx=None):
        super().__init__()
        self.db_path = "results/alpha_miner.db"
        self.current_expression = "Rank(Delta($close, 5))"
        self.strategy_defaults = strategy_templates()
        self.current_strategy_json = json.dumps(
            self.strategy_defaults["cs_top_bottom"].model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        self.swarm_running = False
        self.swarm_process = None
        self.manager_ctx = manager_ctx or multiprocessing.Manager()

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="swarm-tab", id="main-tabs"):
            with TabPane("Auto Miner (Swarm)", id="swarm-tab"):
                with Horizontal():
                    with VerticalScroll(classes="box", id="swarm-config"):
                        yield Label("Swarm Configuration", classes="title")
                        
                        yield Label("Iterations:")
                        yield Input(value="30", id="swarm-iter")
                        
                        yield Label("Mode (ricequant/qlib):")
                        yield Input(value="ricequant", id="swarm-mode")

                        yield Label("Data Backend:")
                        yield Input(value="ricequant", id="swarm-backend")
                        
                        yield Label("Engine (pandas/polars):")
                        yield Input(value="polars", id="swarm-engine")
                        
                        yield Label("LLM Provider:")
                        yield Input(value="kimi", id="swarm-provider")
                        
                        yield Label("LLM Model:")
                        yield Input(value="kimi-k2-turbo-preview", id="swarm-model")

                        yield Label("LLM Base URL:")
                        yield Input(value="", id="swarm-base-url")
                        
                        yield Label("Embedding Provider:")
                        yield Input(value="openai", id="swarm-embed")

                        yield Label("Market Mode:")
                        yield Input(value="single", id="swarm-market-mode")

                        yield Label("Market Profile:")
                        yield Input(value="cn_stock", id="swarm-market-profile")

                        yield Label("Market Profiles:")
                        yield Input(value="cn_stock,us_stock,futures", id="swarm-market-profiles")

                        yield Label("Local Data Path:")
                        yield Input(value="", id="swarm-local-data-path")

                        yield Label("Local Data Layout:")
                        yield Input(value="auto", id="swarm-local-data-layout")
                        
                        yield Label("Market Start:")
                        yield Input(value="2015-01-01", id="swarm-start")
                        
                        yield Label("Market End:")
                        yield Input(value="2020-12-01", id="swarm-end")
                        
                        yield Checkbox("Parallel Execution", value=True, id="swarm-parallel")
                        
                        yield Label("Roles (One per line):")
                        default_roles = (
                            "专注Hurst指数与分形维度的动量专家\n"
                            "利用高频量价相关性挖掘的量价专家\n"
                            "基于宏观周期切换的行业中性专家\n"
                            "基于隐马尔可夫模型状态识别的市场环境专家\n"
                            "专注非线性因子合成与交叉验证的机器学习专家\n"
                            "利用订单流不平衡捕获微观趋势的盘口专家\n"
                            "基于协整关系与误差修正模型的统计套利专家\n"
                            "监测收益率肥尾风险与动态对冲的风险管理专家\n"
                            "专注财报超预期与公告事件驱动的文本挖掘专家\n"
                            "利用复杂网络与知识图谱挖掘产业链关联的图计算专家"
                        )
                        yield TextArea(text=default_roles, id="swarm-roles")
                        
                        with Horizontal(id="swarm-buttons"):
                            yield Button("Start Swarm", id="btn-swarm-start", variant="success")
                            yield Button("Stop Swarm", id="btn-swarm-stop", variant="error", disabled=True)
                    
                    with Vertical(classes="box", id="swarm-logs-container"):
                        yield Label("Swarm Logs", classes="title")
                        yield RichLog(id="swarm-logs", markup=True, highlight=True)

            with TabPane("Alpha Pool", id="pool-tab"):
                with Horizontal():
                    yield DataTable(id="factors-table", classes="box")
                    with VerticalScroll(classes="box", id="pool-details-container"):
                        yield Label("Factor Details", classes="title")
                        yield Markdown("", id="factor-details")
                        yield PlotextPlot(id="pool-chart")

            with TabPane("Manual Backtester", id="manual-tab"):
                with Vertical(classes="box", id="manual-top-box"):
                    yield Label("Current Expression (Press 'e' to edit in nvim):", classes="title")
                    yield Static(self.current_expression, id="expression-display")
                    with Horizontal(id="manual-date-row"):
                        yield Label("Start:")
                        yield Input(value="2017-01-01", id="manual-start")
                        yield Label("End:")
                        yield Input(value="2020-10-31", id="manual-end")
                    yield Label("Data Backend:")
                    yield Input(value="ricequant", id="manual-backend")
                    yield Label("Market Mode:")
                    yield Input(value="single", id="manual-market-mode")
                    yield Label("Market Profile:")
                    yield Input(value="cn_stock", id="manual-market-profile")
                    yield Label("Market Profiles:")
                    yield Input(value="cn_stock", id="manual-market-profiles")
                    yield Label("Local Data Path:")
                    yield Input(value="", id="manual-local-data-path")
                    yield Label("Local Data Layout:")
                    yield Input(value="auto", id="manual-local-data-layout")
                    with Horizontal(id="manual-buttons"):
                        yield Button("Edit Code (e)", id="btn-edit", variant="primary")
                        yield Button("Run Backtest (r)", id="btn-run", variant="success")
                
                with Horizontal(id="manual-bottom-box"):
                    with VerticalScroll(classes="box", id="metrics-container"):
                        yield Label("Metrics", classes="title")
                        yield Static("Run a backtest to see metrics here.", id="metrics-display")

                    yield PlotextPlot(id="manual-chart")

            with TabPane("Strategy Backtester", id="strategy-tab"):
                with Horizontal():
                    with VerticalScroll(classes="box", id="strategy-config-box"):
                        yield Label("Strategy Templates", classes="title")
                        yield Label("Template Key:")
                        yield Input(value="cs_top_bottom", id="strategy-template")
                        yield Label("Strategy Mode:")
                        yield Input(value="cross_sectional", id="strategy-mode")
                        yield Label("Direction:")
                        yield Input(value="long_short", id="strategy-direction")
                        yield Label("Selection Rule:")
                        yield Input(value="top_bottom_n", id="strategy-rule")
                        yield Label("Rebalance Frequency:")
                        yield Input(value="daily", id="strategy-rebalance")
                        yield Label("Top N:")
                        yield Input(value="20", id="strategy-top-n")
                        yield Label("Bottom N:")
                        yield Input(value="20", id="strategy-bottom-n")
                        yield Label("Long Threshold:")
                        yield Input(value="0.75", id="strategy-long-threshold")
                        yield Label("Short Threshold:")
                        yield Input(value="0.25", id="strategy-short-threshold")
                        yield Label("Exit Threshold:")
                        yield Input(value="0.50", id="strategy-exit-threshold")
                        yield Label("Max Positions:")
                        yield Input(value="40", id="strategy-max-positions")
                        yield Label("Max Weight / Position:")
                        yield Input(value="0.05", id="strategy-max-weight")
                        yield Label("Min Holding Days:")
                        yield Input(value="2", id="strategy-min-holding")
                        yield Label("Commission Bps:")
                        yield Input(value="5", id="strategy-commission")
                        yield Label("Slippage Bps:")
                        yield Input(value="5", id="strategy-slippage")
                        yield Label("Market:")
                        yield Input(value="000300.XSHG", id="strategy-market")
                        yield Label("Data Backend:")
                        yield Input(value="ricequant", id="strategy-backend")
                        yield Label("Market Mode:")
                        yield Input(value="single", id="strategy-market-mode")
                        yield Label("Market Profile:")
                        yield Input(value="cn_stock", id="strategy-market-profile")
                        yield Label("Market Profiles:")
                        yield Input(value="cn_stock", id="strategy-market-profiles")
                        yield Label("Local Data Path:")
                        yield Input(value="", id="strategy-local-data-path")
                        yield Label("Local Data Layout:")
                        yield Input(value="auto", id="strategy-local-data-layout")
                        yield Label("Start:")
                        yield Input(value="2017-01-01", id="strategy-start")
                        yield Label("End:")
                        yield Input(value="2020-10-31", id="strategy-end")
                        yield Label("Engine:")
                        yield Input(value="polars", id="strategy-engine")
                        with Horizontal(id="strategy-buttons"):
                            yield Button("Load Template", id="btn-strategy-template", variant="primary")
                            yield Button("Sync JSON", id="btn-strategy-sync", variant="default")
                            yield Button("Run Strategy", id="btn-strategy-run", variant="success")

                    with Vertical(classes="box", id="strategy-right-box"):
                        yield Label("Strategy JSON (Advanced Mode)", classes="title")
                        yield TextArea(text=self.current_strategy_json, id="strategy-json")
                        yield Static("Run a strategy backtest to see metrics here.", id="strategy-metrics-display")
                        yield PlotextPlot(id="strategy-chart")

            with TabPane("Strategy Results", id="strategy-results-tab"):
                with Horizontal():
                    yield DataTable(id="strategies-table", classes="box")
                    with VerticalScroll(classes="box", id="strategy-details-container"):
                        yield Label("Strategy Details", classes="title")
                        yield Markdown("", id="strategy-details")
                        yield PlotextPlot(id="strategy-results-chart")

        yield Footer()

    def action_vim_down(self) -> None:
        focused = self.focused
        if isinstance(focused, DataTable):
            focused.action_cursor_down()
        elif isinstance(focused, RichLog):
            focused.scroll_down()
        elif isinstance(focused, VerticalScroll):
            focused.scroll_down()
        elif isinstance(focused, TextArea):
            focused.action_cursor_down()

    def action_vim_up(self) -> None:
        focused = self.focused
        if isinstance(focused, DataTable):
            focused.action_cursor_up()
        elif isinstance(focused, RichLog):
            focused.scroll_up()
        elif isinstance(focused, VerticalScroll):
            focused.scroll_up()
        elif isinstance(focused, TextArea):
            focused.action_cursor_up()

    def action_vim_left(self) -> None:
        if isinstance(self.focused, (Input, TextArea)):
            return
        self.query_one("Tabs").action_previous_tab()

    def action_vim_right(self) -> None:
        if isinstance(self.focused, (Input, TextArea)):
            return
        self.query_one("Tabs").action_next_tab()

    @staticmethod
    def _compute_cumulative(returns: dict | list) -> list:
        """Convert a returns dict {date: ret} or list of rets to cumulative returns."""
        if isinstance(returns, dict):
            values = [returns[d] for d in sorted(returns.keys())]
        else:
            values = returns
        cum, cr = [], 1.0
        for r in values:
            cr *= 1.0 + float(r)
            cum.append(cr)
        return cum

    def on_mount(self) -> None:
        table = self.query_one("#factors-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("ID", "Hypothesis", "IC", "Effective")
        strategy_table = self.query_one("#strategies-table", DataTable)
        strategy_table.cursor_type = "row"
        strategy_table.add_columns("ID", "Label", "Mode", "Sharpe", "MaxDD")
        self.load_factors()
        self.load_strategies()

    def load_factors(self) -> None:
        if not os.path.exists(self.db_path):
            return
        
        table = self.query_one("#factors-table", DataTable)
        table.clear()
        
        with _db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, hypothesis, ic, is_effective FROM alpha_pool ORDER BY timestamp DESC"
            )
            rows = cursor.fetchall()
            
            for row in rows:
                d = dict(row)
                fid = d.get("id", "N/A")
                hyp = d.get("hypothesis", "")
                if hyp and len(hyp) > 40:
                    hyp = hyp[:37] + "..."
                ic_val = d.get("ic")
                ic_val = float(ic_val) if ic_val is not None else 0.0
                ic_str = f"{ic_val:.4f}"
                eff = "✓" if d.get("is_effective") else "✗"
                table.add_row(fid, hyp, ic_str, eff, key=fid)

    def load_strategies(self) -> None:
        table = self.query_one("#strategies-table", DataTable)
        table.clear()
        if not os.path.exists(self.db_path):
            return
        with _db_connect(self.db_path) as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT strategy_id, label, strategy_mode, metrics_json
                    FROM strategy_backtests
                    ORDER BY ran_at DESC
                    """
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        for row in rows:
            data = dict(row)
            metrics = json.loads(data.get("metrics_json") or "{}")
            table.add_row(
                data.get("strategy_id", "N/A"),
                data.get("label") or "Unnamed Strategy",
                data.get("strategy_mode") or "N/A",
                f"{float(metrics.get('sharpe') or 0.0):.4f}",
                f"{float(metrics.get('max_drawdown') or 0.0):.4f}",
                key=data.get("strategy_id", "N/A"),
            )
                
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value
        if not row_key:
            return

        if event.data_table.id == "factors-table":
            with _db_connect(self.db_path) as conn:
                row = conn.execute("SELECT * FROM alpha_pool WHERE id=?", (row_key,)).fetchone()

            if not row:
                return

            d = dict(row)
            metrics = json.loads(d.get("metrics_json") or "{}")
            returns = json.loads(d.get("returns_json") or "{}")

            ic_val = metrics.get('information_coefficient')
            if ic_val is None:
                ic_val = d.get('ic')
            ic_val = float(ic_val) if ic_val is not None else 0.0

            rank_ic_val = metrics.get('rank_ic')
            if rank_ic_val is None:
                rank_ic_val = d.get('rank_ic')
            rank_ic_val = float(rank_ic_val) if rank_ic_val is not None else 0.0

            ann_ret_val = float(metrics.get('annualized_return') or 0.0)
            max_dd_val = float(metrics.get('max_drawdown') or 0.0)

            details_md = f"""
**Hypothesis:** {d.get('hypothesis')}

**Code:**
```python
{d.get('code')}
```

**Metrics:**
- **IC:** {ic_val:.4f}
- **Rank IC:** {rank_ic_val:.4f}
- **Annualized Return:** {ann_ret_val:.4f}
- **Max Drawdown:** {max_dd_val:.4f}
        """
            self.query_one("#factor-details", Markdown).update(details_md)

            plt = self.query_one("#pool-chart", PlotextPlot).plt
            plt.clear_figure()
            plt.canvas_color("none")
            plt.axes_color("none")
            plt.ticks_color("white")
            if returns:
                plt.plot(self._compute_cumulative(returns), color="blue", marker="braille")
                plt.title("Cumulative Returns")
            else:
                plt.title("No Returns Data Available")
            self.query_one("#pool-chart", PlotextPlot).refresh()
            return

        if event.data_table.id == "strategies-table":
            with _db_connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM strategy_backtests WHERE strategy_id=?",
                    (row_key,),
                ).fetchone()
            if not row:
                return
            d = dict(row)
            metrics = json.loads(d.get("metrics_json") or "{}")
            returns = json.loads(d.get("daily_returns_json") or "{}")
            cfg = json.loads(d.get("strategy_config_json") or "{}")
            trade = json.loads(d.get("trade_stats_json") or "{}")
            details_md = f"""
**Label:** {d.get('label') or 'Unnamed Strategy'}

**Expression:**
```python
{json.loads(d.get('expression_json') or '{}').get('expression', '')}
```

**Config:**
```json
{json.dumps(cfg, ensure_ascii=False, indent=2)}
```

**Metrics:**
- **Annualized Return:** {float(metrics.get('annualized_return') or 0.0):.4f}
- **Sharpe:** {float(metrics.get('sharpe') or 0.0):.4f}
- **Max Drawdown:** {float(metrics.get('max_drawdown') or 0.0):.4f}
- **Turnover:** {float(metrics.get('turnover') or 0.0):.4f}
- **Cost Drag:** {float(metrics.get('cost_drag') or 0.0):.4f}
- **Avg Holding Period:** {float(metrics.get('average_holding_period') or 0.0):.2f}

**Trade Stats:**
```json
{json.dumps(trade, ensure_ascii=False, indent=2)}
```
            """
            self.query_one("#strategy-details", Markdown).update(details_md)
            plt = self.query_one("#strategy-results-chart", PlotextPlot).plt
            plt.clear_figure()
            plt.canvas_color("none")
            plt.axes_color("none")
            plt.ticks_color("white")
            if returns:
                plt.plot(self._compute_cumulative(returns), color="magenta", marker="braille")
                plt.title("Strategy Cumulative Returns")
            else:
                plt.title("No Strategy Returns Data")
            self.query_one("#strategy-results-chart", PlotextPlot).refresh()
            return

    async def action_edit_code(self) -> None:
        if self.query_one(TabbedContent).active == "manual-tab":
            await self._open_editor()

    async def action_run_backtest(self) -> None:
        if self.query_one(TabbedContent).active == "manual-tab":
            await self._run_backtester()
        elif self.query_one(TabbedContent).active == "strategy-tab":
            await self._run_strategy_backtester()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-edit":
            await self._open_editor()
        elif event.button.id == "btn-run":
            await self._run_backtester()
        elif event.button.id == "btn-strategy-template":
            self._load_strategy_template()
        elif event.button.id == "btn-strategy-sync":
            self._sync_strategy_json()
        elif event.button.id == "btn-strategy-run":
            await self._run_strategy_backtester()
        elif event.button.id == "btn-swarm-start":
            self._start_swarm()
        elif event.button.id == "btn-swarm-stop":
            self._stop_swarm()

    async def _open_editor(self) -> None:
        # Suspend TUI, open nvim
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as tmp:
            tmp.write(self.current_expression)
            tmp_path = tmp.name

        with self.suspend():
            subprocess.run(["nvim", tmp_path])

        # Read back
        with open(tmp_path, 'r') as f:
            new_code = f.read().strip()
            
        os.remove(tmp_path)
        
        if new_code:
            self.current_expression = new_code
            self.query_one("#expression-display", Static).update(self.current_expression)

    def _load_strategy_template(self) -> None:
        template_key = self.query_one("#strategy-template", Input).value.strip() or "cs_top_bottom"
        cfg = self.strategy_defaults.get(template_key)
        if cfg is None:
            self.query_one("#strategy-metrics-display", Static).update(
                f"Unknown template: {template_key}"
            )
            return
        self.query_one("#strategy-mode", Input).value = cfg.strategy_mode
        self.query_one("#strategy-direction", Input).value = cfg.direction
        self.query_one("#strategy-rule", Input).value = cfg.selection_rule
        self.query_one("#strategy-rebalance", Input).value = cfg.rebalance_freq
        self.query_one("#strategy-top-n", Input).value = str(cfg.top_n or "")
        self.query_one("#strategy-bottom-n", Input).value = str(cfg.bottom_n or "")
        self.query_one("#strategy-long-threshold", Input).value = str(cfg.long_threshold or "")
        self.query_one("#strategy-short-threshold", Input).value = str(cfg.short_threshold or "")
        self.query_one("#strategy-exit-threshold", Input).value = str(cfg.exit_threshold or "")
        self.query_one("#strategy-max-positions", Input).value = str(cfg.max_positions or "")
        self.query_one("#strategy-max-weight", Input).value = str(cfg.max_weight_per_position)
        self.query_one("#strategy-min-holding", Input).value = str(cfg.min_holding_days)
        self.query_one("#strategy-commission", Input).value = str(cfg.commission_bps)
        self.query_one("#strategy-slippage", Input).value = str(cfg.slippage_bps)
        self.query_one("#strategy-market", Input).value = cfg.market
        self.query_one("#strategy-start", Input).value = cfg.start_date
        self.query_one("#strategy-end", Input).value = cfg.end_date
        self.query_one("#strategy-engine", Input).value = cfg.engine
        self.current_strategy_json = json.dumps(
            cfg.model_dump(mode="json"), ensure_ascii=False, indent=2
        )
        self.query_one("#strategy-json", TextArea).text = self.current_strategy_json

    def _strategy_config_from_form(self) -> StrategyConfig:
        def _num(value: str, cast=float):
            value = value.strip()
            if not value:
                return None
            return cast(value)

        payload = {
            "label": f"TUI {self.query_one('#strategy-template', Input).value.strip() or 'strategy'}",
            "strategy_mode": self.query_one("#strategy-mode", Input).value.strip(),
            "direction": self.query_one("#strategy-direction", Input).value.strip(),
            "selection_rule": self.query_one("#strategy-rule", Input).value.strip(),
            "rebalance_freq": self.query_one("#strategy-rebalance", Input).value.strip(),
            "top_n": _num(self.query_one("#strategy-top-n", Input).value, int),
            "bottom_n": _num(self.query_one("#strategy-bottom-n", Input).value, int),
            "long_threshold": _num(self.query_one("#strategy-long-threshold", Input).value, float),
            "short_threshold": _num(self.query_one("#strategy-short-threshold", Input).value, float),
            "exit_threshold": _num(self.query_one("#strategy-exit-threshold", Input).value, float),
            "max_positions": _num(self.query_one("#strategy-max-positions", Input).value, int),
            "max_weight_per_position": float(self.query_one("#strategy-max-weight", Input).value or 0.05),
            "min_holding_days": int(self.query_one("#strategy-min-holding", Input).value or 1),
            "commission_bps": float(self.query_one("#strategy-commission", Input).value or 0.0),
            "slippage_bps": float(self.query_one("#strategy-slippage", Input).value or 0.0),
            "market": self.query_one("#strategy-market", Input).value or "000300.XSHG",
            "start_date": self.query_one("#strategy-start", Input).value or "2017-01-01",
            "end_date": self.query_one("#strategy-end", Input).value or "2020-10-31",
            "engine": self.query_one("#strategy-engine", Input).value or "polars",
        }
        return StrategyConfig.model_validate(payload)

    @staticmethod
    def _parse_profiles(text: str) -> list[str]:
        return [item.strip() for item in (text or "").split(",") if item.strip()]

    def _sync_strategy_json(self) -> None:
        cfg = self._strategy_config_from_form()
        self.current_strategy_json = json.dumps(
            cfg.model_dump(mode="json"), ensure_ascii=False, indent=2
        )
        self.query_one("#strategy-json", TextArea).text = self.current_strategy_json

    async def _run_backtester(self) -> None:
        btn = self.query_one("#btn-run", Button)
        btn.disabled = True
        btn.label = "Running..."
        self.query_one("#metrics-display", Static).update("Running backtest... Please wait.")
        
        start_date = self.query_one("#manual-start", Input).value or "2017-01-01"
        end_date = self.query_one("#manual-end", Input).value or "2020-10-31"
        data_backend = self.query_one("#manual-backend", Input).value or "ricequant"
        market_mode = self.query_one("#manual-market-mode", Input).value or "single"
        market_profile = self.query_one("#manual-market-profile", Input).value or "cn_stock"
        market_profiles = self._parse_profiles(
            self.query_one("#manual-market-profiles", Input).value or market_profile
        )
        local_data_path = self.query_one("#manual-local-data-path", Input).value or None
        local_data_layout = self.query_one("#manual-local-data-layout", Input).value or "auto"

        try:
            # Run in worker thread to prevent blocking UI
            result = await asyncio.to_thread(
                manual_runner.run_manual_backtest,
                self.current_expression,
                start_date=start_date,
                end_date=end_date,
                engine="polars",
                market="000300.XSHG",
                daily_normalize=True,
                run_robustness=True,
                label="Manual UI Run",
                skip_validation=False,
                data_backend=data_backend,
                market_profile=market_profile,
                market_mode=market_mode,
                market_profiles=market_profiles,
                local_data_path=local_data_path,
                local_data_layout=local_data_layout,
            )
            
            metrics = result.get("metrics", {})
            returns = result.get("daily_returns", {})
            
            # Update Metrics
            metrics_text = f"""
Information Coefficient: {metrics.get('ic', 0):.4f}
Rank IC: {metrics.get('rank_ic', 0):.4f}
Max Drawdown: {metrics.get('max_drawdown', 0):.4f}
Sharpe Ratio: {metrics.get('sharpe', 0):.4f}
RRE: {(metrics.get('rre') or 0.0):.4f}
"""
            self.query_one("#metrics-display", Static).update(metrics_text)
            
            # Plot
            chart = self.query_one("#manual-chart", PlotextPlot)
            plt = chart.plt
            plt.clear_figure()
            plt.canvas_color("none")
            plt.axes_color("none")
            plt.ticks_color("white")
            if returns:
                plt.plot(self._compute_cumulative(returns), color="green", marker="braille")
                plt.title("Manual Backtest Cumulative Returns")
            else:
                plt.title("No Returns Data")
            chart.refresh()
                
        except Exception as e:
            import traceback
            err_str = traceback.format_exc()
            with open("backtest_error.log", "w") as f:
                f.write(err_str)
            self.query_one("#metrics-display", Static).update(f"Error: {e}\nCheck backtest_error.log")
        finally:
            btn.disabled = False
            btn.label = "Run Backtest (r)"

    async def _run_strategy_backtester(self) -> None:
        btn = self.query_one("#btn-strategy-run", Button)
        btn.disabled = True
        btn.label = "Running..."
        metrics_widget = self.query_one("#strategy-metrics-display", Static)
        metrics_widget.update("Running strategy backtest... Please wait.")
        try:
            json_text = self.query_one("#strategy-json", TextArea).text.strip()
            if json_text:
                strategy_config = StrategyConfig.model_validate_json(json_text)
            else:
                strategy_config = self._strategy_config_from_form()
            result = await asyncio.to_thread(
                manual_runner.run_manual_strategy_backtest,
                self.current_expression,
                strategy_config.model_dump(mode="json"),
                data_backend=self.query_one("#strategy-backend", Input).value or "ricequant",
                market_profile=self.query_one("#strategy-market-profile", Input).value or "cn_stock",
                market_mode=self.query_one("#strategy-market-mode", Input).value or "single",
                market_profiles=self._parse_profiles(
                    self.query_one("#strategy-market-profiles", Input).value
                    or (self.query_one("#strategy-market-profile", Input).value or "cn_stock")
                ),
                local_data_path=self.query_one("#strategy-local-data-path", Input).value or None,
                local_data_layout=self.query_one("#strategy-local-data-layout", Input).value or "auto",
            )
            metrics = result.get("metrics", {})
            returns = result.get("daily_returns", {})
            trade = result.get("trade_stats", {})
            metrics_widget.update(
                "\n".join(
                    [
                        f"Annualized Return: {float(metrics.get('annualized_return') or 0.0):.4f}",
                        f"Sharpe: {float(metrics.get('sharpe') or 0.0):.4f}",
                        f"Max Drawdown: {float(metrics.get('max_drawdown') or 0.0):.4f}",
                        f"Turnover: {float(metrics.get('turnover') or 0.0):.4f}",
                        f"Cost Drag: {float(metrics.get('cost_drag') or 0.0):.4f}",
                        f"Rebalance Days: {trade.get('rebalance_days', 0)}",
                    ]
                )
            )
            chart = self.query_one("#strategy-chart", PlotextPlot)
            plt = chart.plt
            plt.clear_figure()
            plt.canvas_color("none")
            plt.axes_color("none")
            plt.ticks_color("white")
            if returns:
                plt.plot(self._compute_cumulative(returns), color="magenta", marker="braille")
                plt.title("Strategy Cumulative Returns")
            else:
                plt.title("No Strategy Returns")
            chart.refresh()
            self.load_strategies()
        except Exception as e:
            err_str = traceback.format_exc()
            with open("strategy_backtest_error.log", "w") as f:
                f.write(err_str)
            metrics_widget.update(f"Error: {e}\nCheck strategy_backtest_error.log")
        finally:
            btn.disabled = False
            btn.label = "Run Strategy"

    def _start_swarm(self) -> None:
        if self.swarm_running:
            return
            
        self.swarm_running = True
        btn_start = self.query_one("#btn-swarm-start", Button)
        btn_stop = self.query_one("#btn-swarm-stop", Button)
        btn_start.disabled = True
        btn_stop.disabled = False
        
        # Read parameters
        iterations = int(self.query_one("#swarm-iter", Input).value)
        mode = self.query_one("#swarm-mode", Input).value
        backend = self.query_one("#swarm-backend", Input).value
        engine = self.query_one("#swarm-engine", Input).value
        provider = self.query_one("#swarm-provider", Input).value
        model = self.query_one("#swarm-model", Input).value
        base_url = self.query_one("#swarm-base-url", Input).value
        embed = self.query_one("#swarm-embed", Input).value
        market_mode = self.query_one("#swarm-market-mode", Input).value
        market_profile = self.query_one("#swarm-market-profile", Input).value
        market_profiles = self.query_one("#swarm-market-profiles", Input).value
        local_data_path = self.query_one("#swarm-local-data-path", Input).value
        local_data_layout = self.query_one("#swarm-local-data-layout", Input).value
        start = self.query_one("#swarm-start", Input).value
        end = self.query_one("#swarm-end", Input).value
        parallel = self.query_one("#swarm-parallel", Checkbox).value
        
        roles_text = self.query_one("#swarm-roles", TextArea).text
        roles = [r.strip() for r in roles_text.split("\n") if r.strip()]
        
        log_widget = self.query_one("#swarm-logs", RichLog)
        log_widget.clear()
        log_widget.write("[bold green]Starting Swarm...[/bold green]")
        
        kwargs = {
            "roles": roles,
            "max_iterations": iterations,
            "evaluation_mode": mode,
            "data_backend": backend,
            "evaluation_engine": engine,
            "llm_provider": provider,
            "llm_model": model,
            "llm_base_url": base_url or None,
            "embedding_provider": embed,
            "market_mode": market_mode,
            "market_profile": market_profile,
            "market_profiles": market_profiles,
            "local_data_path": local_data_path or None,
            "local_data_layout": local_data_layout or "auto",
            "market_start": start,
            "market_end": end,
        }

        log_queue = self.manager_ctx.Queue()

        def log_listener():
            while True:
                try:
                    record = log_queue.get(timeout=0.5)
                    if record is None:
                        break
                    
                    lvl = record.get("level", "INFO")
                    msg = record.get("message", "")
                    role = record.get("role", "System")
                    
                    color = "white"
                    if lvl == "ERROR": color = "red"
                    elif lvl == "WARNING": color = "yellow"
                    elif lvl == "SUCCESS": color = "green"
                    
                    formatted = f"[[bold {color}]{lvl}[/bold {color}]] [cyan]{role}[/cyan]: {msg}"
                    self.call_from_thread(log_widget.write, formatted)
                    
                    if lvl == "SUCCESS" and msg == "Swarm execution completed!":
                        self.call_from_thread(self.load_factors)
                except Exception:
                    pass

        self.listener_thread = threading.Thread(target=log_listener, daemon=True)
        self.listener_thread.start()

        self.swarm_process = multiprocessing.Process(
            target=run_manager_process, 
            args=(kwargs, log_queue, parallel),
            daemon=False
        )
        self.swarm_process.start()

        # Thread to wait for process completion
        def wait_for_process():
            self.swarm_process.join()
            log_queue.put(None) # stop listener
            self.call_from_thread(self._finish_swarm)

        threading.Thread(target=wait_for_process, daemon=True).start()

    def _stop_swarm(self) -> None:
        if not self.swarm_running:
            return

        log_widget: RichLog | None = None
        try:
            log_widget = self.query_one("#swarm-logs", RichLog)
            log_widget.write("[bold red]Stopping Swarm...[/bold red]")
        except Exception:
            pass

        if self.swarm_process and self.swarm_process.is_alive():
            try:
                parent = psutil.Process(self.swarm_process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
            except Exception as e:
                if log_widget is not None:
                    try:
                        log_widget.write(f"[bold red]Failed to kill process: {e}[/bold red]")
                    except Exception:
                        pass

        self._finish_swarm()

    def _finish_swarm(self) -> None:
        self.swarm_running = False
        self.swarm_process = None
        try:
            btn_start = self.query_one("#btn-swarm-start", Button)
            btn_stop = self.query_one("#btn-swarm-stop", Button)
            btn_start.disabled = False
            btn_stop.disabled = True
        except Exception:
            pass

    def action_quit(self) -> None:
        self._stop_swarm()
        self.exit()


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    manager_ctx = multiprocessing.Manager()
    app = TUIApp(manager_ctx=manager_ctx)
    app.run()
