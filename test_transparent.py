from textual.app import App, ComposeResult
from textual.widgets import Label

class TransparentApp(App):
    CSS = """
    Screen {
        background: transparent;
    }
    """
    def compose(self) -> ComposeResult:
        yield Label("Is the background transparent?")

if __name__ == "__main__":
    TransparentApp().run()
