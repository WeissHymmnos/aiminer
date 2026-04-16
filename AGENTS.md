# Repository Guidelines

## Project Structure & Module Organization
Top-level entry points are `manager.py` for multi-agent runs, `main.py` for single-agent execution, and `tui.py` for the Textual UI. Core runtime logic lives in `agents/`, `workflow/`, `core/`, and `schemas/`. Strategy execution and structured strategy configs are implemented in `core/strategy.py` and `core/manual_runner.py`. Automated checks are primarily under `tests/`, while several legacy integration scripts remain outside the default pytest suite. Data, templates, and local vector/wiki stores are kept in `data/`. The Rust-backed Polars extension is isolated in `polars_plugins/`.

## Build, Test, and Development Commands
Create the environment with `conda env create -f environment.yml && conda activate aiminer`, then install Python deps via `pip install -r requirements.txt`. Run the main swarm locally with `python manager.py --iterations 5 --mode ricequant --parallel`. Use `python main.py --iterations 3` for single-agent debugging, and `python tui.py` for the interactive workstation. Build the Rust plugin with `cd polars_plugins && maturin build --release`, or use `docker-compose up --build -d` to build the local stack.

## Coding Style & Naming Conventions
Follow the existing style: 4-space indentation in Python, snake_case for modules/functions/files, and PascalCase for classes such as `AlphaResearcher` and `RiceQuantEval`. Keep new modules focused and colocate them with the relevant subsystem (`agents/`, `core/alphaeval/`, etc.). Rust code in `polars_plugins/src/lib.rs` should follow standard `rustfmt` conventions. No repo-wide formatter config is checked in, so match surrounding code closely and keep imports and comments minimal.

## Testing Guidelines
Default pytest runs are now split by scope: `tests/unit`, `tests/integration`, and `tests/external`. Use `python -m pytest` for the default local-safe suite; `pytest.ini` excludes `external` tests unless explicitly requested. Good targeted commands are `python -m pytest tests/unit -q` and `python -m pytest tests/integration/test_polars_ops_extensive.py -v`. Place new tests under `tests/<scope>/test_<feature>.py`. Move ad hoc or account-dependent checks out of default pytest collection and keep them under `scripts/legacy_tests/` or `tests/external/`.

## Commit & Pull Request Guidelines
Recent history mixes short summaries with conventional prefixes like `fix:` and `chore:`. Prefer concise, imperative commit subjects, optionally using prefixes when they add meaning, for example `fix: guard simulated backtests`. PRs should state the behavior change, list any required env vars or data prerequisites, link related issues, and include screenshots or terminal output when changing `tui.py`, strategy workflows, or Docker behavior.

## Security & Configuration Tips
Store secrets in `.env`; do not commit API keys, RiceQuant credentials, or generated database artifacts. Large local outputs belong under `data/`, `results/`, or `logs/`, and should stay out of reviews unless they are necessary fixtures.
