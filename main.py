
import os
import traceback

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


def inspect_files():
    base = os.path.dirname(os.path.abspath(__file__))
    lines = [
        "APP DIRECTORY:",
        base,
        "",
        "FILES IN APP DIRECTORY:",
    ]

    try:
        lines.extend(sorted(os.listdir(base)))
    except Exception as exc:
        lines.append("Could not list directory: " + str(exc))

    lines.extend(["", "ENGINE FILE SEARCH:"])

    found = []
    try:
        for root, dirs, files in os.walk(base):
            dirs[:] = [
                name for name in dirs
                if name not in (".git", "__pycache__")
            ]
            if "Number_Game_V2_fixed.py" in files:
                found.append(
                    os.path.join(root, "Number_Game_V2_fixed.py")
                )
    except Exception as exc:
        lines.append("Search failed: " + str(exc))

    lines.extend(found if found else ["ENGINE FILE NOT FOUND"])
    return "\n".join(lines)


class DiagnosticApp(App):
    def build(self):
        label = Label(
            text=self.report,
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        label.bind(
            width=lambda widget, width: setattr(
                widget, "text_size", (width - 30, None)
            )
        )
        label.bind(
            texture_size=lambda widget, size: setattr(
                widget, "height", size[1] + 30
            )
        )

        scroll = ScrollView()
        scroll.add_widget(label)
        return scroll


if __name__ == "__main__":
    report = inspect_files()

    try:
        import Number_Game_V2_Integrated_GUI
        Number_Game_V2_Integrated_GUI.NumberGameApp().run()
    except Exception:
        report += "\n\nSTARTUP ERROR:\n" + traceback.format_exc()
        DiagnosticApp.report = report
        DiagnosticApp().run()

 
