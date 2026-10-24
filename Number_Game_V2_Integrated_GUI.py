# SYSTEM 11 — NUMBER GAME V2: INTEGRATED GAME + ANIMATED GUI
# Save this file in the SAME folder as the working V2 main.py and JSON files.
# Run this file to use the graphical interface.
# The original main.py and existing JSON data are not replaced.

import os
import math
import wave
import struct
import importlib.util
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.metrics import dp, sp
from kivy.animation import Animation
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.utils import get_color_from_hex


# SYSTEM 11A — LOAD THE EXISTING ENGINE, DON'T REBUILD ITS BRAIN
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_PATH = os.path.join(BASE_DIR, "Number_Game_V2_fixed.py")

if not os.path.exists(ENGINE_PATH):
    raise FileNotFoundError(
        "Could not find main.py. Put this GUI file in the Number_Game_V2 folder "
        "beside main.py and the three existing JSON files."
    )

_spec = importlib.util.spec_from_file_location("number_game_v2_engine", ENGINE_PATH)
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)


# SYSTEM 11B — THEME
BG = get_color_from_hex("#070B16")
PANEL = get_color_from_hex("#10182B")
PANEL_2 = get_color_from_hex("#172440")
CYAN = get_color_from_hex("#4DE8FF")
BLUE = get_color_from_hex("#6284FF")
PURPLE = get_color_from_hex("#B36BFF")
PINK = get_color_from_hex("#FF69C8")
WHITE = get_color_from_hex("#F4F7FF")
MUTED = get_color_from_hex("#9AA9C6")
GREEN = get_color_from_hex("#5EF0B0")
ORANGE = get_color_from_hex("#FFC36D")


def make_tone_file(path, notes, sample_rate=22050):
    """Create a tiny free WAV effect from tones; no downloads or paid assets."""
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    samples = []
    for frequency, duration, volume in notes:
        count = int(sample_rate * duration)
        for i in range(count):
            envelope = min(1.0, i / max(1, int(sample_rate * .012)))
            envelope *= min(1.0, (count - i) / max(1, int(sample_rate * .025)))
            value = math.sin(2 * math.pi * frequency * i / sample_rate)
            samples.append(int(32767 * volume * envelope * value))
        # A little silence between notes makes the effect clearer.
        samples.extend([0] * int(sample_rate * .025))
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, s))) for s in samples))


class SoundFX:
    """Generates and plays short UI/game sounds. Silently degrades if audio is unavailable."""
    def __init__(self):
        self.sounds = {}
        sound_dir = os.path.join(BASE_DIR, "number_game_sounds")
        patterns = {
            "tap": [(760, .045, .16)],
            "transition": [(420, .055, .13), (620, .065, .12)],
            "hint": [(520, .055, .13)],
            "round_win": [(660, .09, .20), (880, .12, .20), (1120, .16, .18)],
            "round_loss": [(480, .11, .18), (350, .14, .16)],
            "match_win": [(660, .10, .20), (830, .10, .20), (990, .10, .20), (1320, .23, .20)],
            "match_loss": [(440, .12, .18), (370, .12, .17), (294, .22, .16)],
        }
        for name, notes in patterns.items():
            try:
                path = os.path.join(sound_dir, name + ".wav")
                make_tone_file(path, notes)
                sound = SoundLoader.load(path)
                if sound:
                    sound.volume = .65 if name in ("tap", "hint", "transition") else .8
                    self.sounds[name] = sound
            except Exception:
                # GUI remains fully usable if this Android audio backend can't load WAV.
                pass

    def play(self, name):
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.stop()
                sound.play()
            except Exception:
                pass


def rounded_background(widget, color=PANEL, radius=18, line_color=None):
    with widget.canvas.before:
        Color(*color)
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
        outline = None
        if line_color:
            Color(*line_color)
            outline = Line(
                rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, dp(radius)),
                width=1.05,
            )
    def update(*_):
        shape.pos, shape.size = widget.pos, widget.size
        if outline:
            outline.rounded_rectangle = (
                widget.x, widget.y, widget.width, widget.height, dp(radius)
            )
    widget.bind(pos=update, size=update)
    return shape


class Backdrop(Widget):
    """Lightweight animated background: drifting neon orbs and star twinkles."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phase = 0
        self.stars = []
        with self.canvas:
            Color(*BG)
            self.base = Rectangle(pos=self.pos, size=self.size)
            Color(.16, .22, .70, .16)
            self.orb_a = Ellipse(pos=(0, 0), size=(dp(280), dp(280)))
            Color(.52, .10, .72, .12)
            self.orb_b = Ellipse(pos=(0, 0), size=(dp(240), dp(240)))
            Color(.05, .75, .95, .10)
            self.orb_c = Ellipse(pos=(0, 0), size=(dp(170), dp(170)))
            Color(.24, .43, .8, .08)
            self.grid = [Line(points=[0, 0, 0, 0], width=.6) for _ in range(9)]
            import random
            for _ in range(18):
                px, py = random.random(), random.random()
                size = dp(random.random() * 2 + 1)
                alpha = random.random() * .28 + .08
                c = Color(.55, .83, 1, alpha)
                dot = Ellipse(pos=(0, 0), size=(size, size))
                self.stars.append((dot, c, px, py, size, random.random() * 6.28, alpha))
        self.bind(pos=self.update_layout, size=self.update_layout)
        self.update_layout()
        self.event = Clock.schedule_interval(self.animate, 1 / 30)

    def update_layout(self, *_):
        x, y = self.pos
        w, h = self.size
        self.base.pos, self.base.size = self.pos, self.size
        self.orb_a.pos = (x + w * .44, y + h * .62)
        self.orb_b.pos = (x - dp(95), y + h * .18)
        self.orb_c.pos = (x + w * .70, y + h * .08)
        for i, line in enumerate(self.grid):
            yy = y + h * (.10 + i * .075)
            line.points = [x, yy, x + w, yy]
        for dot, color, px, py, size, phase, alpha in self.stars:
            dot.pos = (x + px * w, y + py * h)

    def animate(self, dt):
        if not self.get_parent_window():
            return
        self.phase += dt
        self.orb_a.pos = (
            self.x + self.width * .44 + dp(10) * math.sin(self.phase * .4),
            self.y + self.height * .62 + dp(14) * math.cos(self.phase * .32),
        )
        self.orb_b.pos = (
            self.x - dp(95) + dp(9) * math.cos(self.phase * .3),
            self.y + self.height * .18 + dp(10) * math.sin(self.phase * .34),
        )
        self.orb_c.pos = (
            self.x + self.width * .70 + dp(8) * math.sin(self.phase * .37),
            self.y + self.height * .08 + dp(8) * math.cos(self.phase * .31),
        )
        for dot, color, px, py, size, phase, alpha in self.stars:
            dot.pos = (self.x + px * self.width, self.y + py * self.height)
            color.a = alpha * (.4 + .6 * (.5 + .5 * math.sin(self.phase * 1.7 + phase)))


class AppLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", WHITE)
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(size=self.sync_text)
        self.sync_text()

    def sync_text(self, *_):
        self.text_size = (self.width, self.height)


class NeonButton(Button):
    def __init__(self, title, accent=CYAN, subtitle=None, **kwargs):
        self.accent = accent
        text = f"[b][size=15sp]{title}[/size][/b]"
        if subtitle:
            text += f"\n[size=11sp][color=#A8B5D1]{subtitle}[/color][/size]"
        kwargs.setdefault("text", text)
        kwargs.setdefault("markup", True)
        kwargs.setdefault("color", WHITE)
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(64 if subtitle else 52))
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("border", (0, 0, 0, 0))
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.phase = 0
        with self.canvas.before:
            self.fill_color = Color(*PANEL_2)
            self.shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])
            self.edge_color = Color(accent[0], accent[1], accent[2], .72)
            self.edge = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(15)), width=1.2)
        self.bind(pos=self.paint, size=self.paint, state=self.state_changed)
        self.pulse_event = Clock.schedule_interval(self.pulse, 1 / 24)

    def paint(self, *_):
        self.shape.pos, self.shape.size = self.pos, self.size
        self.edge.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(15))

    def pulse(self, dt):
        if self.get_parent_window() and self.state != "down":
            self.phase += dt
            self.edge_color.a = .55 + .22 * (.5 + .5 * math.sin(self.phase * 1.6))

    def state_changed(self, *_):
        if self.state == "down":
            self.fill_color.rgba = (
                self.accent[0] * .25, self.accent[1] * .25,
                self.accent[2] * .25, 1
            )
            self.edge_color.a = 1
            self.opacity = .86
            Animation(opacity=1, duration=.13, t="out_quad").start(self)
        else:
            self.fill_color.rgba = PANEL_2
            self.opacity = 1

    def on_parent(self, *_):
        if self.parent is None and hasattr(self, "pulse_event"):
            self.pulse_event.cancel()


class Panel(BoxLayout):
    def __init__(self, accent=CYAN, **kwargs):
        super().__init__(orientation="vertical", padding=dp(15), spacing=dp(8), **kwargs)
        with self.canvas.before:
            Color(*PANEL)
            self.shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
            Color(accent[0], accent[1], accent[2], .68)
            self.edge = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(18)), width=1)
        self.bind(pos=self.paint, size=self.paint)

    def paint(self, *_):
        self.shape.pos, self.shape.size = self.pos, self.size
        self.edge.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(18))


def make_scroll_column():
    scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
    column = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(18), dp(16), dp(18), dp(18)], size_hint_y=None)
    column.bind(minimum_height=column.setter("height"))
    scroll.add_widget(column)
    return scroll, column


class NumberGameApp(App):
    title = "Number Game V2"

    def build(self):
        engine.configure_storage(self.user_data_dir)
        Window.clearcolor = BG
        self.sfx = SoundFX()
        self.profiles = engine.load_profiles()
        if self.profiles is None:
            self.profiles = []
            self.data_error = "The profile database could not be read. Check your existing JSON file before continuing."
        else:
            self.data_error = None
        self.active_profile = self.profiles[0] if self.profiles else None
        self.match = None
        self.last_feedback = ""
        self.selected_mode = "single"
        self.selected_match_type = "quick"
        self.selected_difficulty = "2"
        self.rounds_value = "5"
        self.target_value = "300"
        self.multi_ids = set()
        self.manager = ScreenManager(transition=FadeTransition(duration=.22))
        for screen in (
            LoginScreen(name="login"),
            HomeScreen(name="home"),
            SetupScreen(name="setup"),
            GameScreen(name="game"),
            ResultsScreen(name="results"),
            HistoryScreen(name="history"),
            ProfileScreen(name="profile"),
        ):
            screen.app = self
            self.manager.add_widget(screen)
        # Always show profile selection first when opening the integrated app.
        # This avoids silently choosing the first profile on a shared phone.
        self.manager.current = "login"
        return self.manager

    def go(self, screen, sound=True):
        if sound:
            self.sfx.play("transition")
        same_screen = self.manager.current == screen
        self.manager.current = screen
        target = self.manager.get_screen(screen)
        target.opacity = 0
        Animation(opacity=1, duration=.22, t="out_quad").start(target)
        # Kivy doesn't emit on_enter when navigating to the already-active screen.
        # Refresh it explicitly so attempts, hints, and the current player update.
        if same_screen and hasattr(target, "refresh"):
            Clock.schedule_once(lambda _dt: target.refresh(), 0)

    def popup(self, title, message, accent=CYAN, buttons=None):
        self.sfx.play("transition")
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with content.canvas.before:
            Color(*PANEL)
            shape = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(18)])
            Color(accent[0], accent[1], accent[2], .7)
            edge = Line(rounded_rectangle=(content.x, content.y, content.width, content.height, dp(18)), width=1)
        def paint(*_):
            shape.pos, shape.size = content.pos, content.size
            edge.rounded_rectangle = (content.x, content.y, content.width, content.height, dp(18))
        content.bind(pos=paint, size=paint)
        heading = AppLabel(text=title, color=accent, bold=True, font_size=sp(18), size_hint_y=None, height=dp(32))
        body = AppLabel(text=message, font_size=sp(14))
        content.add_widget(heading)
        content.add_widget(body)
        action_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        popup = Popup(title="", content=content, size_hint=(.9, None), height=dp(270), separator_height=0, background_color=(0, 0, 0, 0), auto_dismiss=False)
        if buttons:
            for label, callback in buttons:
                btn = NeonButton(label, accent=accent, height=dp(46))
                btn.bind(on_release=lambda _b, cb=callback: (popup.dismiss(), cb()))
                action_row.add_widget(btn)
        else:
            btn = NeonButton("GOT IT", accent=accent, height=dp(46))
            btn.bind(on_release=popup.dismiss)
            action_row.add_widget(btn)
        content.add_widget(action_row)
        popup.open()
        popup.opacity = 0
        Animation(opacity=1, duration=.18).start(popup)
        return popup

    def create_profile(self, name):
        name = name.strip()
        if not name:
            self.popup("NAME REQUIRED", "Enter a player name to create a profile.", ORANGE)
            return False
        if len(name) > 30:
            self.popup("NAME TOO LONG", "Player names must be 30 characters or fewer.", ORANGE)
            return False
        profile = {
            "player_id": engine.generate_player_id(self.profiles),
            "display_name": name,
            "created_at": engine.current_timestamp(),
        }
        updated = self.profiles + [profile]
        if not engine.save_profiles(updated):
            self.popup("SAVE FAILED", "The profile was not added. Your existing profile data was preserved.", PINK)
            return False
        self.profiles = updated
        self.active_profile = profile
        self.go("home")
        self.popup("PROFILE CREATED", f"Welcome, {name}!\nPermanent ID: {profile['player_id']}", GREEN)
        return True

    def open_create_profile_popup(self):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        rounded_background(content, PANEL, 18, CYAN)
        content.add_widget(AppLabel(text="CREATE PLAYER PROFILE", color=CYAN, bold=True, size_hint_y=None, height=dp(34)))
        field = TextInput(hint_text="Player display name", multiline=False, size_hint_y=None, height=dp(48), foreground_color=WHITE, cursor_color=CYAN, background_color=PANEL_2, padding=[dp(12), dp(12)])
        content.add_widget(field)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        popup = Popup(title="", content=content, size_hint=(.9, None), height=dp(205), separator_height=0, background_color=(0,0,0,0))
        cancel = NeonButton("CANCEL", accent=MUTED, height=dp(46))
        create = NeonButton("CREATE", accent=GREEN, height=dp(46))
        cancel.bind(on_release=popup.dismiss)
        create.bind(on_release=lambda *_: (popup.dismiss(), self.create_profile(field.text)))
        row.add_widget(cancel)
        row.add_widget(create)
        content.add_widget(row)
        popup.open()

    def start_new_match(self):
        if not self.active_profile:
            self.go("login")
            return
        if os.path.exists(engine.SAVE_FILE):
            self.popup(
                "SAVED MATCH EXISTS",
                "Starting a new match would replace the current save. Continue only if you are sure.",
                ORANGE,
                buttons=[
                    ("CANCEL", lambda: None),
                    ("REPLACE SAVE", self._create_match_from_setup),
                ],
            )
        else:
            self._create_match_from_setup()

    def _create_match_from_setup(self):
        mode = self.selected_mode
        if mode == "single":
            participants = [engine.make_participant(self.active_profile)]
        else:
            chosen = [p for p in self.profiles if p["player_id"] in self.multi_ids]
            if self.active_profile["player_id"] not in self.multi_ids:
                chosen.insert(0, self.active_profile)
            unique = []
            seen = set()
            for profile in chosen:
                if profile["player_id"] not in seen:
                    unique.append(profile)
                    seen.add(profile["player_id"])
            if len(unique) < 2:
                self.popup("ADD PLAYERS", "Multiplayer needs at least 2 different profiles. Select another profile below.", ORANGE)
                return
            if len(unique) > 20:
                self.popup("TOO MANY PLAYERS", "A match supports up to 20 players.", ORANGE)
                return
            participants = [engine.make_participant(p) for p in unique]

        if self.selected_match_type == "quick":
            match_type, rounds_target, target_score = "quick", 5, None
        elif self.selected_match_type == "custom":
            if not self.rounds_value.isdigit() or not 1 <= int(self.rounds_value) <= 1000:
                self.popup("INVALID ROUND COUNT", "Choose between 1 and 1000 rounds.", ORANGE)
                return
            match_type, rounds_target, target_score = "custom", int(self.rounds_value), None
        elif self.selected_match_type == "endless":
            match_type, rounds_target, target_score = "endless", None, None
        else:
            if not self.target_value.isdigit() or not 1 <= int(self.target_value) <= 1000000:
                self.popup("INVALID TARGET", "Choose a target score from 1 to 1,000,000.", ORANGE)
                return
            match_type, rounds_target, target_score = "target", None, int(self.target_value)

        difficulty = engine.DIFFICULTIES[self.selected_difficulty].copy()
        self.match = {
            "match_id": engine.new_id("M"),
            "mode": mode,
            "match_type": match_type,
            "rounds_target": rounds_target,
            "target_score": target_score,
            "difficulty": difficulty,
            "range_max": difficulty["maximum"],
            "max_attempts": difficulty["attempts"],
            "multiplier": difficulty["multiplier"],
            "players": participants,
            "round_number": 1,
            "rounds_completed": 0,
            "round_secret": None,
            "current_player_index": 0,
            "current_attempts": 0,
            "round_history": [],
            "round_scores": {},
            "phase": "between_rounds",
            "end_reason": None,
            "created_at": engine.current_timestamp(),
        }
        if not engine.save_match(self.match):
            self.popup("SAVE FAILED", "The match could not be saved, so it has not started.", PINK)
            return
        engine.start_round(self.match)
        self.last_feedback = ""
        self.go("game")

    def resume_match(self):
        match = engine.load_saved_match()
        if match is None:
            self.popup("NO SAVED MATCH", "No valid saved match was found.", ORANGE)
            return
        if match.get("phase") == "finished":
            self.match = match
            self.finish_current_match(match.get("end_reason") or "finished")
            return
        self.match = match
        if self.match.get("phase") == "between_rounds":
            self.go("results")
        else:
            self.go("game")

    def begin_current_turn(self):
        match = self.match
        if not match:
            return None
        players = match["players"]
        idx = match.get("current_player_index", 0)
        if not (isinstance(idx, int) and 0 <= idx < len(players) and players[idx].get("round_status") == "playing"):
            idx = engine.next_pending_player(match)
            if idx is None:
                return None
            match["current_player_index"] = idx
            match["current_attempts"] = 0
            players[idx]["round_status"] = "playing"
            engine.save_match(match, quiet=True)
        return players[idx]

    def submit_guess(self, raw):
        match = self.match
        if not match:
            return
        raw = raw.strip()
        if not raw.isdigit():
            self.popup("NUMBER REQUIRED", "Enter a whole number in the allowed range.", ORANGE)
            return
        guess = int(raw)
        if not 1 <= guess <= match["range_max"]:
            self.popup("OUT OF RANGE", f"Enter a number from 1 to {match['range_max']}.", ORANGE)
            return
        player = self.begin_current_turn()
        if player is None:
            self.complete_current_round()
            return
        match["current_attempts"] = int(match.get("current_attempts", 0)) + 1
        used = match["current_attempts"]

        if guess == match["round_secret"]:
            points = int(engine.BASE_SCORES.get(used, 0) * match["multiplier"])
            player["score"] += points
            player["round_score"] = points
            player["round_status"] = "won"
            match["current_attempts"] = 0
            self.last_feedback = f"CORRECT! +{points} POINTS"
            engine.save_match(match, quiet=True)
            self.sfx.play("round_win")
            self.popup("ROUND WIN!", f"{player['name']} guessed correctly!\nAttempts used: {used}\nPoints earned: +{points}", GREEN)
            self.advance_turn_or_round()
            return

        if guess < match["round_secret"]:
            self.last_feedback = f"{guess} IS TOO LOW — GUESS HIGHER"
        else:
            self.last_feedback = f"{guess} IS TOO HIGH — GUESS LOWER"
        self.sfx.play("hint")

        if used >= match["max_attempts"]:
            player["round_status"] = "failed"
            player["round_score"] = 0
            match["current_attempts"] = 0
            engine.save_match(match, quiet=True)
            self.last_feedback = f"ROUND LOST — SECRET NUMBER: {match['round_secret']}"
            self.sfx.play("round_loss")
            self.popup("ROUND LOST", f"No attempts left.\nThe secret number was {match['round_secret']}.", ORANGE)
            self.advance_turn_or_round()
            return

        if not engine.save_match(match, quiet=True):
            self.popup("SAVE WARNING", "This guess could not be saved. Avoid closing the app until storage works.", PINK)
        self.go("game", sound=False)

    def advance_turn_or_round(self):
        match = self.match
        # Finish every active player's turn before checking match end conditions.
        # This preserves the original engine's target-score and round-history timing.
        idx = engine.next_pending_player(match)
        if idx is not None:
            match["current_player_index"] = idx
            match["current_attempts"] = 0
            engine.save_match(match, quiet=True)
            self.go("game", sound=False)
        else:
            self.complete_current_round()

    def complete_current_round(self):
        if not self.match:
            return
        engine.complete_round(self.match)
        reason = engine.match_end_reason(self.match)
        if reason:
            self.finish_current_match(reason)
        else:
            self.go("results")

    def finish_current_match(self, reason):
        match = self.match
        if not match:
            return
        winners = engine.calculate_winner_ids(match, reason)
        winner_names = [p["name"] for p in match["players"] if p["player_id"] in winners]
        if not winners:
            title, sound, accent = "MATCH OVER", "match_loss", ORANGE
            message = f"{reason.title()}.\nNo winner this time."
        elif len(winners) > 1:
            title, sound, accent = "IT'S A TIE!", "match_win", PURPLE
            message = "Tied players:\n" + "\n".join(winner_names)
        else:
            title, sound, accent = "MATCH VICTORY!", "match_win", GREEN
            message = f"Champion: {winner_names[0]}\nFinal score: {max(p['score'] for p in match['players'] if p['player_id'] in winners)}"
        saved = engine.finish_match(match, reason)
        if not saved:
            self.popup("SAVE NEEDS ATTENTION", "The match could not be fully recorded. The engine preserved the finished save so you can retry safely.", PINK)
            self.go("results", sound=False)
            return
        self.sfx.play(sound)
        self.popup(title, message, accent, buttons=[
            ("MATCH RESULTS", lambda: self.go("results", sound=False)),
            ("HOME", lambda: self.go("home")),
        ])

    def quit_current_player(self):
        match = self.match
        if not match:
            return
        player = self.begin_current_turn()
        if player is None:
            return
        player["status"] = "quit"
        player["round_status"] = "quit"
        match["current_attempts"] = 0
        engine.save_match(match, quiet=True)
        self.sfx.play("round_loss")
        # Keep the original engine's order: finish remaining turns, record the
        # round, then evaluate forfeit/all-quit conditions.
        self.advance_turn_or_round()

    def next_round(self):
        if not self.match:
            return
        self.match["round_number"] += 1
        engine.start_round(self.match)
        self.last_feedback = ""
        self.go("game")

    def rematch(self):
        if not self.match:
            return
        engine.reset_match(self.match)
        if engine.save_match(self.match, quiet=True):
            engine.start_round(self.match)
            self.last_feedback = ""
            self.go("game")
        else:
            self.popup("SAVE FAILED", "The rematch could not be saved.", PINK)

    def save_and_home(self):
        if self.match and engine.save_match(self.match, quiet=True):
            self.popup("PROGRESS SAVED", "Your match is saved. You can resume it from the home screen.", GREEN, buttons=[
                ("HOME", lambda: self.go("home", sound=False))
            ])
        else:
            self.popup("SAVE FAILED", "The match could not be saved. Please stay here and try again.", PINK)

    def open_history(self):
        self.go("history")

    def get_history(self):
        return engine.load_history()

    def rename_active_profile(self, name):
        name = name.strip()
        if not name or len(name) > 30:
            self.popup("INVALID NAME", "Enter a name between 1 and 30 characters.", ORANGE)
            return
        updated = [dict(p) for p in self.profiles]
        for p in updated:
            if p["player_id"] == self.active_profile["player_id"]:
                p["display_name"] = name
        if engine.save_profiles(updated):
            self.profiles = updated
            self.active_profile = next(p for p in self.profiles if p["player_id"] == self.active_profile["player_id"])
            self.popup("PROFILE UPDATED", "Your permanent player ID has not changed.", GREEN)
            self.go("profile", sound=False)
        else:
            self.popup("SAVE FAILED", "The previous profile was kept.", PINK)


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.body = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
        self.add_widget(self.body)
        self.bind(on_enter=self.refresh)

    def refresh(self, *_):
        self.body.clear_widgets()
        self.body.add_widget(Widget(size_hint_y=.2))
        self.body.add_widget(AppLabel(text="NUMBER GAME / V2", color=CYAN, bold=True, font_size=sp(12), size_hint_y=None, height=dp(28)))
        self.body.add_widget(AppLabel(text="CHOOSE YOUR PLAYER", bold=True, font_size=sp(28), size_hint_y=None, height=dp(58)))
        self.body.add_widget(AppLabel(text="Your permanent ID keeps your career records together.", color=MUTED, size_hint_y=None, height=dp(48)))
        scroll, col = make_scroll_column()
        for profile in self.app.profiles:
            b = NeonButton(profile["display_name"], accent=CYAN, subtitle=profile["player_id"], height=dp(62))
            b.bind(on_release=lambda _b, p=profile: self.select_profile(p))
            col.add_widget(b)
        self.body.add_widget(scroll)
        create = NeonButton("+ CREATE NEW PLAYER", accent=GREEN)
        create.bind(on_release=lambda *_: self.app.open_create_profile_popup())
        self.body.add_widget(create)

    def select_profile(self, profile):
        self.app.active_profile = profile
        self.app.go("home")


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        scroll, self.col = make_scroll_column()
        self.add_widget(scroll)
        self.bind(on_enter=self.refresh)

    def refresh(self, *_):
        self.col.clear_widgets()
        hero = Panel(accent=CYAN, size_hint_y=None, height=dp(190))
        hero.add_widget(AppLabel(text="✦  NUMBER GAME / V2", color=CYAN, bold=True, font_size=sp(11), size_hint_y=None, height=dp(22)))
        hero.add_widget(AppLabel(text="THINK FAST.\nGUESS SMART.", bold=True, font_size=sp(30), size_hint_y=None, height=dp(80)))
        hero.add_widget(AppLabel(text="Every guess is a move. Every round is a battle.", color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(24)))
        hero.add_widget(AppLabel(text=f"PLAYER  {self.app.active_profile['display_name']}  •  ENGINE ONLINE", color=GREEN, bold=True, font_size=sp(10), size_hint_y=None, height=dp(22)))
        self.col.add_widget(hero)
        self.col.add_widget(AppLabel(text=f"PERMANENT ID  {self.app.active_profile['player_id']}", color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(26)))
        buttons = [
            ("NEW MATCH", "Choose mode, rules and difficulty", CYAN, self.open_setup),
            ("CONTINUE MATCH", "Resume the saved match", PURPLE, self.app.resume_match),
            ("MATCH HISTORY", "Completed matches and scores", GREEN, self.app.open_history),
            ("PLAYER PROFILE", "Player ID and profile settings", BLUE, lambda: self.app.go("profile")),
            ("SWITCH PLAYER", "Select another saved profile", PINK, lambda: self.app.go("login")),
        ]
        for title, sub, color, callback in buttons:
            b = NeonButton(title, accent=color, subtitle=sub, height=dp(64))
            b.bind(on_release=lambda _b, cb=callback: self._tap(cb))
            self.col.add_widget(b)
        self.col.add_widget(AppLabel(text="MOTION UI  •  LOCAL SAVE  •  CAREER TRACKING", color=MUTED, font_size=sp(9), halign="center", size_hint_y=None, height=dp(28)))

    def _tap(self, callback):
        self.app.sfx.play("tap")
        callback()

    def open_setup(self):
        self.app.go("setup")


class SetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        scroll, self.col = make_scroll_column()
        self.add_widget(scroll)
        self.rounds_input = TextInput(text="5", multiline=False, input_filter="int", hint_text="Number of rounds", size_hint_y=None, height=dp(44), foreground_color=WHITE, cursor_color=CYAN, background_color=PANEL_2, padding=[dp(12), dp(10)])
        self.target_input = TextInput(text="300", multiline=False, input_filter="int", hint_text="Target score", size_hint_y=None, height=dp(44), foreground_color=WHITE, cursor_color=CYAN, background_color=PANEL_2, padding=[dp(12), dp(10)])
        self.bind(on_enter=self.refresh)

    def add_heading(self, text):
        self.col.add_widget(AppLabel(text=text, color=CYAN, bold=True, font_size=sp(12), size_hint_y=None, height=dp(28)))

    def make_choice_row(self, options, selected, callback):
        cols = 2 if len(options) > 3 else len(options)
        rows = (len(options) + cols - 1) // cols
        row = GridLayout(cols=cols, spacing=dp(7), size_hint_y=None, height=dp(54 * rows + 7 * (rows - 1)))
        for value, label, accent in options:
            b = NeonButton(label, accent=accent, height=dp(52))
            b.bind(on_release=lambda _b, v=value: callback(v))
            row.add_widget(b)
        self.col.add_widget(row)

    def refresh(self, *_):
        self.col.clear_widgets()
        self.col.add_widget(AppLabel(text="NEW MATCH", font_size=sp(28), bold=True, size_hint_y=None, height=dp(48)))
        self.add_heading("1  /  MODE")
        self.make_choice_row([("single", "SINGLE", CYAN), ("multi", "MULTIPLAYER", PURPLE)], self.app.selected_mode, self.set_mode)
        self.add_heading("2  /  MATCH TYPE")
        self.make_choice_row([("quick", "QUICK · 5", CYAN), ("custom", "CUSTOM", BLUE), ("endless", "ENDLESS", PURPLE), ("target", "TARGET", GREEN)], self.app.selected_match_type, self.set_type)
        self.col.add_widget(AppLabel(text="Custom rounds / target score (used only for selected type)", color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(28)))
        self.col.add_widget(self.rounds_input)
        self.col.add_widget(self.target_input)
        self.add_heading("3  /  DIFFICULTY")
        self.make_choice_row([("1", "EASY\n1–50", GREEN), ("2", "MEDIUM\n1–100", CYAN), ("3", "HARD\n1–200", PINK)], self.app.selected_difficulty, self.set_difficulty)
        self.add_heading("4  /  MULTIPLAYER PLAYERS")
        self.col.add_widget(AppLabel(text="Your profile is included automatically. Tap other profiles to add/remove them.", color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(40)))
        for profile in self.app.profiles:
            if profile["player_id"] == self.app.active_profile["player_id"]:
                continue
            chosen = profile["player_id"] in self.app.multi_ids
            b = NeonButton(("✓  " if chosen else "+  ") + profile["display_name"], accent=GREEN if chosen else BLUE, subtitle=profile["player_id"], height=dp(58))
            b.bind(on_release=lambda _b, p=profile: self.toggle_player(p))
            self.col.add_widget(b)
        start = NeonButton("START MATCH  →", accent=GREEN, height=dp(58))
        start.bind(on_release=lambda *_: self.start())
        back = NeonButton("← BACK HOME", accent=MUTED, height=dp(50))
        back.bind(on_release=lambda *_: self.app.go("home"))
        self.col.add_widget(start)
        self.col.add_widget(back)

    def set_mode(self, value):
        self.app.sfx.play("tap")
        self.app.selected_mode = value
        self.refresh()

    def set_type(self, value):
        self.app.sfx.play("tap")
        self.app.selected_match_type = value
        self.refresh()

    def set_difficulty(self, value):
        self.app.sfx.play("tap")
        self.app.selected_difficulty = value
        self.refresh()

    def toggle_player(self, profile):
        pid = profile["player_id"]
        if pid in self.app.multi_ids:
            self.app.multi_ids.remove(pid)
        else:
            self.app.multi_ids.add(pid)
        self.app.sfx.play("tap")
        self.refresh()

    def start(self):
        self.app.rounds_value = self.rounds_input.text.strip()
        self.app.target_value = self.target_input.text.strip()
        self.app.sfx.play("tap")
        self.app.start_new_match()


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        scroll, self.col = make_scroll_column()
        self.add_widget(scroll)
        self.guess_input = TextInput(
            hint_text="Enter your guess", multiline=False, input_filter="int",
            size_hint_y=None, height=dp(58), font_size=sp(23),
            foreground_color=WHITE, cursor_color=CYAN,
            background_color=PANEL_2, padding=[dp(16), dp(13)],
        )
        self.guess_input.bind(on_text_validate=lambda *_: self.submit())
        self.bind(on_enter=self.refresh)

    def refresh(self, *_):
        self.col.clear_widgets()
        match = self.app.match
        if not match:
            self.app.go("home", sound=False)
            return
        player = self.app.begin_current_turn()
        if player is None:
            self.app.complete_current_round()
            return
        self.col.add_widget(AppLabel(text=f"ROUND {match['round_number']}  /  {match['difficulty']['name'].upper()}", color=CYAN, bold=True, font_size=sp(11), size_hint_y=None, height=dp(26)))
        self.col.add_widget(AppLabel(text="GUESS THE NUMBER", bold=True, font_size=sp(27), size_hint_y=None, height=dp(48)))
        card = Panel(accent=CYAN, size_hint_y=None, height=dp(130))
        card.add_widget(AppLabel(text=f"CURRENT PLAYER  •  {player['name']}", color=CYAN, bold=True, font_size=sp(12), size_hint_y=None, height=dp(24)))
        card.add_widget(AppLabel(text=f"1  —  {match['range_max']}", bold=True, font_size=sp(31), halign="center", size_hint_y=None, height=dp(45)))
        card.add_widget(AppLabel(text=f"ATTEMPTS LEFT  {match['max_attempts'] - match.get('current_attempts', 0)}     •     SCORE  {player['score']}", color=MUTED, font_size=sp(11), halign="center", size_hint_y=None, height=dp(26)))
        self.col.add_widget(card)
        self.col.add_widget(self.guess_input)
        submit = NeonButton("LOCK IN GUESS  →", accent=CYAN, height=dp(58))
        submit.bind(on_release=lambda *_: self.submit())
        self.col.add_widget(submit)
        feedback = self.app.last_feedback or "Choose carefully. Valid guesses are saved as you play."
        feedback_panel = Panel(accent=PURPLE, size_hint_y=None, height=dp(78))
        feedback_panel.add_widget(AppLabel(text="GAME FEEDBACK", color=PURPLE, bold=True, font_size=sp(10), size_hint_y=None, height=dp(20)))
        feedback_panel.add_widget(AppLabel(text=feedback, font_size=sp(12)))
        self.col.add_widget(feedback_panel)
        self.col.add_widget(AppLabel(text="LEADERBOARD", color=MUTED, bold=True, font_size=sp(11), size_hint_y=None, height=dp(24)))
        ordered = sorted(match["players"], key=lambda p: p["score"], reverse=True)
        for rank, p in enumerate(ordered, 1):
            self.col.add_widget(AppLabel(text=f"{rank}. {p['name']}     {p['score']} pts     {p['status'].upper()}", font_size=sp(12), size_hint_y=None, height=dp(26)))
        row = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(52))
        save = NeonButton("SAVE & HOME", accent=BLUE, height=dp(50))
        save.bind(on_release=lambda *_: self.app.save_and_home())
        quit_btn = NeonButton("QUIT TURN", accent=PINK, height=dp(50))
        quit_btn.bind(on_release=lambda *_: self.app.popup("LEAVE MATCH?", "This player will forfeit the current match.", PINK, buttons=[
            ("CANCEL", lambda: None),
            ("CONFIRM", self.app.quit_current_player),
        ]))
        row.add_widget(save)
        row.add_widget(quit_btn)
        self.col.add_widget(row)
        self.guess_input.text = ""

    def submit(self):
        raw = self.guess_input.text
        self.guess_input.text = ""
        self.app.sfx.play("tap")
        self.app.submit_guess(raw)


class ResultsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        scroll, self.col = make_scroll_column()
        self.add_widget(scroll)
        self.bind(on_enter=self.refresh)

    def refresh(self, *_):
        self.col.clear_widgets()
        match = self.app.match
        if not match:
            self.app.go("home", sound=False)
            return
        reason = engine.match_end_reason(match)
        finished = match.get("phase") == "finished" or bool(reason)
        self.col.add_widget(AppLabel(text="MATCH COMPLETE" if finished else f"ROUND {match['rounds_completed']} RESULTS", color=GREEN if finished else CYAN, bold=True, font_size=sp(12), size_hint_y=None, height=dp(28)))
        self.col.add_widget(AppLabel(text="FINAL STANDINGS" if finished else "ROUND STANDINGS", font_size=sp(28), bold=True, size_hint_y=None, height=dp(48)))
        card = Panel(accent=GREEN if finished else CYAN, size_hint_y=None, height=dp(100))
        card.add_widget(AppLabel(text=f"ROUNDS COMPLETED  {match['rounds_completed']}", color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(24)))
        card.add_widget(AppLabel(text=f"MATCH TYPE  {match['match_type'].upper()}   •   {match['difficulty']['name'].upper()}", bold=True, font_size=sp(13), size_hint_y=None, height=dp(30)))
        self.col.add_widget(card)
        for rank, p in enumerate(sorted(match["players"], key=lambda p: p["score"], reverse=True), 1):
            panel = Panel(accent=GREEN if rank == 1 else BLUE, size_hint_y=None, height=dp(72))
            panel.add_widget(AppLabel(text=f"{rank}.  {p['name']}", bold=True, font_size=sp(15), size_hint_y=None, height=dp(30)))
            panel.add_widget(AppLabel(text=f"{p['score']} POINTS   •   THIS ROUND +{p.get('round_score', 0)}   •   {p['status'].upper()}", color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(24)))
            self.col.add_widget(panel)
        if not finished:
            next_btn = NeonButton("NEXT ROUND  →", accent=GREEN, height=dp(56))
            next_btn.bind(on_release=lambda *_: self.app.next_round())
            self.col.add_widget(next_btn)
        rematch = NeonButton("REMATCH", accent=PURPLE, height=dp(52))
        rematch.bind(on_release=lambda *_: self.app.rematch())
        self.col.add_widget(rematch)
        if not finished:
            finish = NeonButton("FINISH MATCH", accent=ORANGE, height=dp(52))
            finish.bind(on_release=lambda *_: self.app.finish_current_match("finished by player"))
            self.col.add_widget(finish)
        save = NeonButton("SAVE & HOME", accent=BLUE, height=dp(50))
        save.bind(on_release=lambda *_: self.app.save_and_home())
        self.col.add_widget(save)
        home = NeonButton("HOME", accent=MUTED, height=dp(48))
        home.bind(on_release=lambda *_: self.app.go("home"))
        self.col.add_widget(home)


class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        scroll, self.col = make_scroll_column()
        self.add_widget(scroll)
        self.bind(on_enter=self.refresh)

    def refresh(self, *_):
        self.col.clear_widgets()
        self.col.add_widget(AppLabel(text="MATCH HISTORY", font_size=sp(28), bold=True, size_hint_y=None, height=dp(48)))
        history = self.app.get_history()
        if history is None:
            self.col.add_widget(AppLabel(text="History file could not be read. It has not been changed.", color=PINK, size_hint_y=None, height=dp(60)))
        else:
            matches = list(reversed(history.get("matches", [])))
            if not matches:
                self.col.add_widget(AppLabel(text="No completed matches yet. Finish a match to start your career record.", color=MUTED, size_hint_y=None, height=dp(70)))
            for item in matches[:100]:
                panel = Panel(accent=PURPLE, size_hint_y=None, height=dp(125))
                panel.add_widget(AppLabel(text=f"{item.get('match_id', 'MATCH')}  •  {item.get('difficulty', '?')}", color=CYAN, bold=True, font_size=sp(12), size_hint_y=None, height=dp(24)))
                panel.add_widget(AppLabel(text=f"{item.get('mode', '?').upper()} / {item.get('match_type', '?').upper()}  •  ROUNDS {item.get('rounds_completed', 0)}", color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(24)))
                for p in sorted(item.get("players", []), key=lambda p: p.get("score", 0), reverse=True):
                    panel.add_widget(AppLabel(text=f"{p.get('name', '?')} — {p.get('score', 0)} pts", font_size=sp(12), size_hint_y=None, height=dp(22)))
                self.col.add_widget(panel)
        back = NeonButton("← BACK HOME", accent=MUTED, height=dp(50))
        back.bind(on_release=lambda *_: self.app.go("home"))
        self.col.add_widget(back)


class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.col = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
        self.add_widget(self.col)
        self.bind(on_enter=self.refresh)

    def refresh(self, *_):
        self.col.clear_widgets()
        p = self.app.active_profile
        self.col.add_widget(AppLabel(text="PLAYER PROFILE", font_size=sp(28), bold=True, size_hint_y=None, height=dp(48)))
        panel = Panel(accent=BLUE, size_hint_y=None, height=dp(150))
        panel.add_widget(AppLabel(text=p["display_name"], color=CYAN, bold=True, font_size=sp(22), size_hint_y=None, height=dp(38)))
        panel.add_widget(AppLabel(text=f"PERMANENT ID\n{p['player_id']}", font_size=sp(15), size_hint_y=None, height=dp(54)))
        panel.add_widget(AppLabel(text=f"CREATED  {p.get('created_at', 'Unknown')}", color=MUTED, font_size=sp(10), size_hint_y=None, height=dp(22)))
        self.col.add_widget(panel)
        name_input = TextInput(text=p["display_name"], multiline=False, hint_text="New display name", size_hint_y=None, height=dp(48), foreground_color=WHITE, cursor_color=CYAN, background_color=PANEL_2, padding=[dp(12), dp(12)])
        self.col.add_widget(name_input)
        rename = NeonButton("UPDATE DISPLAY NAME", accent=BLUE)
        rename.bind(on_release=lambda *_: self.app.rename_active_profile(name_input.text))
        self.col.add_widget(rename)
        self.col.add_widget(Widget(size_hint_y=1))
        back = NeonButton("← BACK HOME", accent=MUTED)
        back.bind(on_release=lambda *_: self.app.go("home"))
        self.col.add_widget(back)


if __name__ == "__main__":
    NumberGameApp().run()
