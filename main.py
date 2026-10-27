
import traceback

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


class StartupErrorApp(App):
    def build(self):
        scroll = ScrollView()
        label = Label(
            text=self.error_text,
            size_hint_y=None,
            halign="left",
            valign="top",
            padding=(20, 20),
        )

        label.bind(
            width=lambda widget, width: setattr(
                widget, "text_size", (width - 40, None)
            )
        )
        label.bind(
            texture_size=lambda widget, size: setattr(
                widget, "height", size[1] + 40
            )
        )

        scroll.add_widget(label)
        return scroll


if __name__ == "__main__":
    try:
        import Number_Game_V2_Integrated_GUI as game

        game.NumberGameApp().run()

    except Exception:
        StartupErrorApp.error_text = (
            "GAME STARTUP ERROR\n\n"
            + traceback.format_exc()
        )
        StartupErrorApp().run()
 
