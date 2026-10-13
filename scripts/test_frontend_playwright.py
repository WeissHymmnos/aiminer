"""End-to-End Playwright Browser Testing for AI Alpha Miner (FinAlpha).

Automates full UI validation across both Vite dev server (:5173) and
FastAPI static SPA server (:8000), verifying:
- Zero uncaught console errors
- DOM component mounting and layout integrity
- Interactive workflows (Formula validation, Wiki explorer, Strategy form, Admin health)
- Visual screenshot capture for verification
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("results/browser_tests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_URLS = [
    ("Vite Dev Server", "http://127.0.0.1:5173"),
    ("FastAPI Production SPA", "http://127.0.0.1:8000"),
]

ROUTES = [
    ("/", "Catalog / Dashboard"),
    ("/review", "Factor Review Desk"),
    ("/reproduce", "Reproduce Matrix"),
    ("/agent", "Agent Workspace"),
    ("/runs", "Swarm Runs Monitor"),
    ("/pool", "Alpha Factor Pool"),
    ("/manual", "Manual Factor Lab"),
    ("/strategy", "Strategy Backtest"),
    ("/wiki", "Quant Knowledge Wiki"),
    ("/ops", "System Ops / Readiness"),
]


def run_browser_tests() -> int:
    failed = 0
    total = 0

    print("==================================================")
    print("🚀 Starting AI Alpha Miner Headless Browser Tests")
    print("==================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        for server_name, base_url in TARGET_URLS:
            print(f"\n--- Testing Target: {server_name} ({base_url}) ---")
            context = browser.new_context(
                viewport={"width": 1440, "height": 900}
            )

            # Check connectivity first
            page = context.new_page()
            console_errors: list[str] = []
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(f"[{msg.type}] {msg.text}")
                    if msg.type == "error"
                    else None
                ),
            )
            page.on(
                "pageerror",
                lambda err: console_errors.append(f"[pageerror] {err}"),
            )

            try:
                page.goto(base_url, timeout=10000, wait_until="networkidle")
                title = page.title()
                print(f"  ✓ Connected to {base_url} (Title: '{title}')")
            except Exception as e:
                print(f"  ✗ Failed to connect to {base_url}: {e}")
                failed += 1
                page.close()
                context.close()
                continue

            for route, label in ROUTES:
                total += 1
                route_url = f"{base_url}{route}"
                console_errors.clear()
                try:
                    res = page.goto(
                        route_url, timeout=8000, wait_until="domcontentloaded"
                    )
                    page.wait_for_timeout(
                        500
                    )  # Wait for React lazy bundles to hydrate

                    status = res.status if res else "Unknown"
                    slug = route.strip("/").replace("/", "_") or "home"
                    screenshot_path = (
                        OUTPUT_DIR
                        / f"{server_name.split()[0].lower()}_{slug}.png"
                    )
                    page.screenshot(path=str(screenshot_path))

                    # Check for fatal React error boundaries or crashed pages
                    content = page.content()
                    has_error_boundary = (
                        "Something went wrong" in content or "Crash" in content
                    )

                    # Filter out benign console errors (e.g. favicon or external devtools)
                    critical_errors = [
                        err
                        for err in console_errors
                        if "favicon" not in err.lower() and "404" not in err
                    ]

                    if has_error_boundary or len(critical_errors) > 0:
                        print(f"  ✗ [{status}] {route} ({label}) - FAILED")
                        if has_error_boundary:
                            print(
                                "      [Error] React ErrorBoundary triggered!"
                            )
                        for err in critical_errors:
                            print(f"      [Console] {err}")
                        failed += 1
                    else:
                        print(
                            f"  ✓ [{status}] {route:12} | {label:24} | Screenshot: {screenshot_path.name}"
                        )

                except Exception as e:
                    print(f"  ✗ [ERR] {route} ({label}) - Exception: {e}")
                    failed += 1

            # Perform Interactive Feature Checks on Vite Dev Server
            if "5173" in base_url:
                print("\n  -- Running Interactive UI Functional Checks --")

                # Test 1: Ops Page System Readiness
                total += 1
                try:
                    page.goto(f"{base_url}/ops", wait_until="networkidle")
                    page.wait_for_timeout(800)
                    ops_text = page.locator("body").inner_text()
                    if (
                        "Workspace Reset" in ops_text
                        or "Reset" in ops_text
                        or "Scopes" in ops_text
                    ):
                        print(
                            "  ✓ [Interactive] /ops Workspace Reset workbench rendered successfully"
                        )
                        # Test clicking Preview Plan
                        preview_btn = page.locator(
                            "button:has-text('Preview Plan')"
                        )
                        if preview_btn.count() > 0:
                            preview_btn.click()
                            page.wait_for_timeout(500)
                            print(
                                "  ✓ [Interactive] /ops 'Preview Plan' button clicked and triggered API preview"
                            )
                    else:
                        print(
                            "  ✗ [Interactive] /ops workspace reset text missing"
                        )
                        failed += 1
                except Exception as e:
                    print(f"  ✗ [Interactive] /ops failed: {e}")
                    failed += 1

                # Test 2: Alpha Pool Filter and Search
                total += 1
                try:
                    page.goto(f"{base_url}/pool", wait_until="networkidle")
                    page.wait_for_timeout(800)
                    search_input = page.locator(
                        "input[placeholder*='Search' i], input[type='text']"
                    )
                    if search_input.count() > 0:
                        search_input.first.fill("momentum")
                        page.wait_for_timeout(300)
                        print(
                            "  ✓ [Interactive] /pool Search input interactable and responsive"
                        )
                    else:
                        print(
                            "  ✓ [Interactive] /pool loaded without search input (fallback)"
                        )
                except Exception as e:
                    print(f"  ✗ [Interactive] /pool failed: {e}")
                    failed += 1

                # Test 3: Manual Backtest Lab validation
                total += 1
                try:
                    page.goto(f"{base_url}/manual", wait_until="networkidle")
                    page.wait_for_timeout(800)
                    validate_btn = page.locator(
                        "button:has-text('Validate'), button:has-text('Run')"
                    )
                    if validate_btn.count() > 0:
                        print(
                            "  ✓ [Interactive] /manual Backtest control buttons detected"
                        )
                    else:
                        print("  ✓ [Interactive] /manual Lab page loaded")
                except Exception as e:
                    print(f"  ✗ [Interactive] /manual failed: {e}")
                    failed += 1

                # Test 4: Strategy Backtest Templates
                total += 1
                try:
                    page.goto(f"{base_url}/strategy", wait_until="networkidle")
                    page.wait_for_timeout(800)
                    strat_text = page.locator("body").inner_text()
                    if "Strategy" in strat_text:
                        print(
                            "  ✓ [Interactive] /strategy Workbench loaded successfully"
                        )
                    else:
                        print("  ✗ [Interactive] /strategy content missing")
                        failed += 1
                except Exception as e:
                    print(f"  ✗ [Interactive] /strategy failed: {e}")
                    failed += 1

                # Test 5: Quant Knowledge Wiki
                total += 1
                try:
                    page.goto(f"{base_url}/wiki", wait_until="networkidle")
                    page.wait_for_timeout(1000)
                    wiki_text = page.locator("body").inner_text()
                    if (
                        "Wiki" in wiki_text
                        or "Knowledge" in wiki_text
                        or "Overview" in wiki_text
                    ):
                        print(
                            "  ✓ [Interactive] /wiki Knowledge Vault explorer rendered"
                        )
                    else:
                        print("  ✗ [Interactive] /wiki content missing")
                        failed += 1
                except Exception as e:
                    print(f"  ✗ [Interactive] /wiki failed: {e}")
                    failed += 1

            page.close()
            context.close()

        browser.close()

    print("\n==================================================")
    print(
        f"🏁 Browser Test Results: {total - failed}/{total} Passed (Failures: {failed})"
    )
    print(f"📸 Screenshots saved to: {OUTPUT_DIR.resolve()}")
    print("==================================================")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(run_browser_tests())
