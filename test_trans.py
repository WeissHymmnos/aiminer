from textual.app import App, ComposeResult
from textual.widgets import Label

class TestApp(App):
    CSS = """
    Screen { background: transparent; }
    Label { background: transparent; }
    """
    def compose(self) -> ComposeResult:
        yield Label("If this is transparent, you can see your terminal background.")

if __name__ == "__main__":
    TestApp().run()
