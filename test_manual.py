import asyncio
from tui import TUIApp

async def test():
    app = TUIApp()
    async with app.run_test() as pilot:
        # Switch tab
        app.query_one("#main-tabs").active = "manual-tab"
        await pilot.pause()

        # Start backtest
        await pilot.click("#btn-run")
        await pilot.pause()
        
        # Check for 10 seconds
        for i in range(10):
            await asyncio.sleep(1)
            metrics = str(app.query_one("#metrics-display").render())
            print(f"Metrics ({i}):", metrics)
            if "Information Coefficient" in metrics:
                break
        else:
            print("Failed to get metrics")

if __name__ == "__main__":
    asyncio.run(test())
