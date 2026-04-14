from textual.app import App, ComposeResult
from textual.widgets import Label

class TestApp(App):
    CSS = "Screen { background: transparent; }"
    def __init__(self):
        super().__init__(ansi_color=True)
    def compose(self) -> ComposeResult:
        yield Label("Test ANSI")

if __name__ == "__main__":
    TestApp().run()
