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
                        
                        yield Label("Engine (pandas/polars):")
                        yield Input(value="polars", id="swarm-engine")
                        
                        yield Label("LLM Provider:")
                        yield Input(value="kimi", id="swarm-provider")
                        
                        yield Label("LLM Model:")
                        yield Input(value="kimi-k2-turbo-preview", id="swarm-model")
                        
                        yield Label("Embedding Provider:")
                        yield Input(value="openai", id="swarm-embed")
                        
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
                    with Horizontal(id="manual-buttons"):
                        yield Button("Edit Code (e)", id="btn-edit", variant="primary")
                        yield Button("Run Backtest (r)", id="btn-run", variant="success")
                
                with Horizontal(id="manual-bottom-box"):
                    with VerticalScroll(classes="box", id="metrics-container"):
                        yield Label("Metrics", classes="title")
                        yield Static("Run a backtest to see metrics here.", id="metrics-display")

                    yield PlotextPlot(id="manual-chart")

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
        self.load_factors()

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
                
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value
        if not row_key:
            return
            
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
        
        # Plot returns
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

    async def action_edit_code(self) -> None:
        if self.query_one(TabbedContent).active == "manual-tab":
            await self._open_editor()

    async def action_run_backtest(self) -> None:
        if self.query_one(TabbedContent).active == "manual-tab":
            await self._run_backtester()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-edit":
            await self._open_editor()
        elif event.button.id == "btn-run":
            await self._run_backtester()
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

    async def _run_backtester(self) -> None:
        btn = self.query_one("#btn-run", Button)
        btn.disabled = True
        btn.label = "Running..."
        self.query_one("#metrics-display", Static).update("Running backtest... Please wait.")
        
        start_date = self.query_one("#manual-start", Input).value or "2017-01-01"
        end_date = self.query_one("#manual-end", Input).value or "2020-10-31"

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
                skip_validation=False
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
        engine = self.query_one("#swarm-engine", Input).value
        provider = self.query_one("#swarm-provider", Input).value
        model = self.query_one("#swarm-model", Input).value
        embed = self.query_one("#swarm-embed", Input).value
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
            "evaluation_engine": engine,
            "llm_provider": provider,
            "llm_model": model,
            "embedding_provider": embed,
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
