from textual.app import App, ComposeResult
from textual.widgets import RichLog

class LogApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog()

if __name__ == "__main__":
    pass
