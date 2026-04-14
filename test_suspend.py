from textual.app import App, ComposeResult
from textual.widgets import Button

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield Button("Suspend")

    async def on_button_pressed(self):
        with self.suspend():
            print("Suspended!")

if __name__ == "__main__":
    TestApp().run()
