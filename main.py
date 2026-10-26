
from kivy.app import App
from kivy.uix.label import Label


class StartupTestApp(App):
    def build(self):
        return Label(
            text=(
                "KIVY STARTUP TEST\n\n"
                "If you can read this,\n"
                "basic Kivy is running!"
            ),
            halign="center",
            valign="middle",
        )


if __name__ == "__main__":
    StartupTestApp().run()
