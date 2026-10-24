# ============================================================
# NUMBER GAME V2 — CORE RELIABILITY UPDATE
# SYSTEM 1: PLAYER PROFILES AND LOGIN
# SYSTEM 2: GAME ENGINE AND MATCH SETUP
# SYSTEM 3: MULTIPLAYER AND MATCH TYPES
# SYSTEM 4: SAVE, RESUME, AND SAFE FINISHING
# SYSTEM 5: MATCH HISTORY AND CAREER STATISTICS
# ============================================================

import json
import os
import uuid
import random
from datetime import datetime

# ============================================================
# SYSTEM 1A: FILE LOCATIONS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(BASE_DIR, "number_game_profiles.json")
SAVE_FILE = os.path.join(BASE_DIR, "number_game_save.json")
HISTORY_FILE = os.path.join(BASE_DIR, "number_game_history.json")
def configure_storage(data_dir):
    global PROFILE_FILE, SAVE_FILE, HISTORY_FILE

    PROFILE_FILE = os.path.join(data_dir, "number_game_profiles.json")
    SAVE_FILE = os.path.join(data_dir, "number_game_save.json")
    HISTORY_FILE = os.path.join(data_dir, "number_game_history.json")
# ============================================================
# SYSTEM 1B: GENERAL DATABASE FUNCTIONS
# ============================================================

def load_json_file(path, default):
    """Load JSON. Return a copy of the default only when the file is absent."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        print(f"\nDatabase read error for {os.path.basename(path)}: {error}")
        return None


def save_json_file(path, data):
    """Write to a temporary file, then replace the original atomically."""
    temporary_path = path + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
        return True
    except (OSError, TypeError, ValueError) as error:
        print(f"\nSave error for {os.path.basename(path)}: {error}")
        try:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
        except OSError:
            pass
        return False


def save_match(match, quiet=False):
    """Save current match without ever deleting the previous save on failure."""
    success = save_json_file(SAVE_FILE, match)
    if not success and not quiet:
        print("WARNING: Progress could not be saved. Do not clear app data.")
    return success


def current_timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_id(prefix):
    return prefix + "-" + uuid.uuid4().hex[:8].upper()

# ============================================================
# SYSTEM 1C: PLAYER PROFILE DATABASE
# ============================================================

def load_profiles():
    data = load_json_file(PROFILE_FILE, {"version": 1, "profiles": []})
    if data is None:
        return None
    if isinstance(data, list):
        profiles = data
    elif isinstance(data, dict) and isinstance(data.get("profiles"), list):
        profiles = data["profiles"]
    else:
        print("Profile database format is invalid. Existing file was preserved.")
        return None

    valid_profiles = []
    seen_ids = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        player_id = profile.get("player_id")
        display_name = profile.get("display_name")
        if not isinstance(player_id, str) or not player_id.strip():
            continue
        if not isinstance(display_name, str) or not display_name.strip():
            continue
        if player_id in seen_ids:
            print("Warning: duplicate profile ID skipped:", player_id)
            continue
        seen_ids.add(player_id)
        valid_profiles.append(profile)
    return valid_profiles


def save_profiles(profiles):
    return save_json_file(PROFILE_FILE, {"version": 1, "profiles": profiles})


def generate_player_id(profiles):
    existing_ids = {p["player_id"] for p in profiles}
    while True:
        player_id = new_id("P")
        if player_id not in existing_ids:
            return player_id


def create_player(profiles):
    print("\n========== CREATE PLAYER ==========")
    while True:
        name = input("Enter display name (Q to cancel): ").strip()
        if name.casefold() == "q":
            return None
        if not name:
            print("Name cannot be empty.")
        elif len(name) > 30:
            print("Name must be 30 characters or fewer.")
        else:
            break

    profile = {
        "player_id": generate_player_id(profiles),
        "display_name": name,
        "created_at": current_timestamp(),
    }
    updated = profiles + [profile]
    if save_profiles(updated):
        profiles.append(profile)
        print("\nProfile created successfully!")
        print("Name:", profile["display_name"])
        print("Permanent ID:", profile["player_id"])
        return profile
    print("Profile could not be saved; no profile was added in memory.")
    return None


def select_player(profiles, exclude_ids=None):
    exclude_ids = exclude_ids or []
    available = [p for p in profiles if p["player_id"] not in exclude_ids]
    if not available:
        print("No available profiles to select.")
        return None
    print("\n========== SELECT PLAYER ==========")
    for index, profile in enumerate(available, start=1):
        print(f"{index}. {profile['display_name']} | {profile['player_id']}")
    print("0. Cancel")
    while True:
        choice = input("Choose a player number: ").strip()
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(available):
            return available[int(choice) - 1]
        print("Invalid choice. Try again.")


def rename_player(profiles, profile):
    print("\nCurrent name:", profile["display_name"])
    print("Permanent ID:", profile["player_id"])
    while True:
        name = input("Enter new name (Q to cancel): ").strip()
        if name.casefold() == "q":
            return profile
        if not name:
            print("Name cannot be empty.")
        elif len(name) > 30:
            print("Name must be 30 characters or fewer.")
        else:
            break
    updated = [dict(p) for p in profiles]
    for item in updated:
        if item["player_id"] == profile["player_id"]:
            item["display_name"] = name
    if save_profiles(updated):
        profiles[:] = updated
        for item in profiles:
            if item["player_id"] == profile["player_id"]:
                print("Name updated. Permanent ID unchanged.")
                return item
    print("Rename failed; the previous profile was kept.")
    return profile


def view_profile(profile):
    print("\n========== PLAYER PROFILE ==========")
    print("Name:", profile["display_name"])
    print("Player ID:", profile["player_id"])
    print("Created:", profile.get("created_at", "Unknown"))
    print("====================================")

# ============================================================
# SYSTEM 2A: DIFFICULTY AND MATCH SETUP
# ============================================================

DIFFICULTIES = {
    "1": {"name": "Easy", "maximum": 50, "attempts": 7, "multiplier": 1.0},
    "2": {"name": "Medium", "maximum": 100, "attempts": 5, "multiplier": 1.5},
    "3": {"name": "Hard", "maximum": 200, "attempts": 4, "multiplier": 2.0},
}
BASE_SCORES = {1: 100, 2: 80, 3: 60, 4: 40, 5: 20, 6: 10, 7: 5}


def choose_difficulty():
    print("\n========== CHOOSE DIFFICULTY ==========")
    print("1. Easy   | 1-50   | 7 attempts")
    print("2. Medium | 1-100  | 5 attempts")
    print("3. Hard   | 1-200  | 4 attempts")
    while True:
        choice = input("Choose difficulty: ").strip()
        if choice in DIFFICULTIES:
            return DIFFICULTIES[choice].copy()
        print("Enter 1, 2 or 3.")


def ask_positive_integer(prompt, maximum=1000000):
    while True:
        value = input(prompt).strip()
        if value.isdigit() and 1 <= int(value) <= maximum:
            return int(value)
        print(f"Enter a whole number from 1 to {maximum}.")


def choose_match_type():
    print("\n========== MATCH TYPE ==========")
    print("1. Quick Match (5 rounds)")
    print("2. Custom Match")
    print("3. Endless Match")
    print("4. Target Score Match")
    while True:
        choice = input("Choose match type: ").strip()
        if choice == "1":
            return "quick", 5, None
        if choice == "2":
            return "custom", ask_positive_integer("Number of rounds: ", 1000), None
        if choice == "3":
            return "endless", None, None
        if choice == "4":
            return "target", None, ask_positive_integer("Target score: ", 1000000)
        print("Enter 1, 2, 3 or 4.")


def make_participant(profile):
    return {
        "player_id": profile["player_id"],
        "name": profile["display_name"],
        "score": 0,
        "status": "active",
        "round_status": "pending",
        "round_score": 0,
    }


def setup_participants(profiles, active_profile, mode):
    if mode == "single":
        return [make_participant(active_profile)]
    count = ask_positive_integer("Number of players (2-20): ", 20)
    while count < 2:
        print("Multiplayer requires at least 2 players.")
        count = ask_positive_integer("Number of players (2-20): ", 20)
    if count > len(profiles):
        print(f"You need {count} different profiles, but only {len(profiles)} exist.")
        print("Create the missing profiles first.")
        return None
    participants = [make_participant(active_profile)]
    print("\nThe logged-in player is participant 1.")
    while len(participants) < count:
        print(f"\nSelect participant {len(participants) + 1}.")
        selected = select_player(profiles, [p["player_id"] for p in participants])
        if selected is None:
            print("Participant selection cancelled.")
            return None
        participants.append(make_participant(selected))
    return participants


def create_match(profiles, active_profile):
    print("\n========== NEW MATCH ==========")
    print("1. Single Player")
    print("2. Multiplayer")
    while True:
        mode_choice = input("Choose mode: ").strip()
        if mode_choice in ("1", "2"):
            break
        print("Enter 1 or 2.")
    mode = "single" if mode_choice == "1" else "multi"
    participants = setup_participants(profiles, active_profile, mode)
    if not participants:
        return None
    match_type, rounds_target, target_score = choose_match_type()
    difficulty = choose_difficulty()
    return {
        "match_id": new_id("M"), "mode": mode, "match_type": match_type,
        "rounds_target": rounds_target, "target_score": target_score,
        "difficulty": difficulty, "range_max": difficulty["maximum"],
        "max_attempts": difficulty["attempts"], "multiplier": difficulty["multiplier"],
        "players": participants, "round_number": 1, "rounds_completed": 0,
        "round_secret": None, "current_player_index": 0, "current_attempts": 0,
        "round_history": [], "round_scores": {}, "phase": "between_rounds",
        "end_reason": None, "created_at": current_timestamp(),
    }

# ============================================================
# SYSTEM 3A: ROUND ENGINE AND LEADERBOARD
# ============================================================

def show_leaderboard(match):
    print("\n========== LEADERBOARD ==========")
    ordered = sorted(match["players"], key=lambda p: p["score"], reverse=True)
    for place, player in enumerate(ordered, start=1):
        print(f"{place}. {player['name']} | Score: {player['score']} | {player['status'].upper()}")


def start_round(match):
    match["round_secret"] = random.randint(1, match["range_max"])
    match["current_player_index"] = 0
    match["current_attempts"] = 0
    match["round_scores"] = {}
    for player in match["players"]:
        player["round_status"] = "pending" if player["status"] == "active" else "inactive"
        player["round_score"] = 0
    match["phase"] = "playing"
    print("\n" + "=" * 42)
    print(f"ROUND {match['round_number']}")
    print(f"Guess the secret number from 1 to {match['range_max']}.")
    print("Type Q during your turn to quit the match.")
    print("=" * 42)
    # Save the round's secret and starting state before asking for any guess.
    save_match(match)


def next_pending_player(match):
    for index, player in enumerate(match["players"]):
        if player.get("round_status") == "pending":
            return index
    return None


def play_round(match):
    if match.get("phase") != "playing":
        start_round(match)

    while True:
        # If a turn was interrupted, resume the same player with saved attempts.
        index = match.get("current_player_index", 0)
        players = match["players"]
        continuing_turn = (
            isinstance(index, int) and 0 <= index < len(players)
            and players[index].get("round_status") == "playing"
        )
        if not continuing_turn:
            index = next_pending_player(match)
            if index is None:
                break
            match["current_player_index"] = index
            match["current_attempts"] = 0
            players[index]["round_status"] = "playing"
            save_match(match)

        player = players[index]
        attempts = match.get("current_attempts", 0)
        if not isinstance(attempts, int) or attempts < 0:
            attempts = 0
            match["current_attempts"] = 0

        print("\n--------------------------------------")
        print("Player:", player["name"])
        print("Permanent ID:", player["player_id"])
        print("Attempts remaining:", max(0, match["max_attempts"] - attempts))
        if attempts:
            print(f"Resuming this turn: {attempts} valid guess(es) already used.")

        while True:
            raw = input("Your guess: ").strip()
            if raw.casefold() == "q":
                player["status"] = "quit"
                player["round_status"] = "quit"
                match["current_attempts"] = 0
                save_match(match)
                print(player["name"], "has left the match.")
                break
            if not raw.isdigit():
                print("Enter a whole number or Q to quit.")
                continue
            guess = int(raw)
            if not 1 <= guess <= match["range_max"]:
                print(f"Enter a number between 1 and {match['range_max']}.")
                continue

            match["current_attempts"] += 1
            attempts_used = match["current_attempts"]

            if guess == match["round_secret"]:
                base = BASE_SCORES.get(attempts_used, 0)
                points = int(base * match["multiplier"])
                player["score"] += points
                player["round_score"] = points
                player["round_status"] = "won"
                match["current_attempts"] = 0
                # Persist the score and completed turn together.
                save_match(match)
                print("\nCORRECT! 🎉")
                print("Attempts used:", attempts_used)
                print("Points earned:", points)
                print("Total score:", player["score"])
                break

            if guess < match["round_secret"]:
                print("Too low! Guess higher.")
            else:
                print("Too high! Guess lower.")

            if attempts_used >= match["max_attempts"]:
                player["round_status"] = "failed"
                player["round_score"] = 0
                match["current_attempts"] = 0
                save_match(match)
                print("No attempts left!")
                print("The secret number was:", match["round_secret"])
                break

            # Critical reliability fix: save each valid wrong guess immediately.
            if not save_match(match):
                print("WARNING: That guess may not survive an app closure.")
            print("Attempts left:", match["max_attempts"] - attempts_used)

    complete_round(match)


def complete_round(match):
    if match.get("phase") != "playing":
        return
    round_result = {
        "round_number": match["round_number"],
        "secret_number": match["round_secret"],
        "scores": [
            {"player_id": p["player_id"], "name": p["name"],
             "round_score": p["round_score"], "total_score": p["score"],
             "round_status": p["round_status"], "status": p["status"]}
            for p in match["players"]
        ],
    }
    match["round_history"].append(round_result)
    match["rounds_completed"] += 1
    match["phase"] = "between_rounds"
    match["current_attempts"] = 0
    print("\n========== ROUND RESULTS ==========")
    for player in match["players"]:
        print(f"{player['name']}: +{player['round_score']} | Total: {player['score']} | {player['round_status']}")
    show_leaderboard(match)
    save_match(match)

# ============================================================
# SYSTEM 3B: END CONDITIONS AND WINNER LOGIC
# ============================================================

def match_end_reason(match):
    active = [p for p in match["players"] if p.get("status") == "active"]
    if not active:
        return "all players quit"
    if match["mode"] == "multi" and len(active) == 1:
        if any(p.get("status") == "quit" for p in match["players"]):
            return "forfeit"
    if match["match_type"] == "target":
        if any(p["score"] >= match["target_score"] for p in match["players"]):
            return "target score reached"
    if match["match_type"] in ("quick", "custom"):
        if match["rounds_completed"] >= match["rounds_target"]:
            return "rounds completed"
    return None


def calculate_winner_ids(match, reason):
    players = match.get("players", [])
    if reason == "all players quit":
        return []
    if reason == "forfeit":
        remaining = [p for p in players if p.get("status") == "active"]
        return [p["player_id"] for p in remaining]
    if not players:
        return []
    highest = max(p.get("score", 0) for p in players)
    return [p["player_id"] for p in players if p.get("score", 0) == highest]


def finish_match(match, reason):
    """Idempotently finish: save final state, record history once, then remove save."""
    match["end_reason"] = reason
    match["phase"] = "finished"
    # Save the finished state first. If later steps fail, resume can retry safely.
    if not save_match(match):
        print("Final state could not be saved; match was not removed from saves.")
        return False

    history = load_json_file(HISTORY_FILE, {"version": 1, "matches": []})
    if history is None:
        print("Could not read history. Finished match save was preserved for retry.")
        return False
    if isinstance(history, list):
        history = {"version": 1, "matches": history}
    if not isinstance(history, dict) or not isinstance(history.get("matches", []), list):
        print("History file format is invalid. Finished match save was preserved.")
        return False
    matches = history.setdefault("matches", [])
    if not any(isinstance(item, dict) and item.get("match_id") == match["match_id"] for item in matches):
        winners = calculate_winner_ids(match, reason)
        record = {
            "match_id": match["match_id"], "completed_at": current_timestamp(),
            "mode": match["mode"], "match_type": match["match_type"],
            "difficulty": match["difficulty"]["name"],
            "rounds_completed": match["rounds_completed"], "end_reason": reason,
            "players": [
                {"player_id": p["player_id"], "name": p["name"],
                 "score": p["score"], "status": p["status"]}
                for p in match["players"]
            ],
            "winner_ids": winners, "round_history": match["round_history"],
        }
        matches.append(record)
        if not save_json_file(HISTORY_FILE, history):
            print("History could not be saved. Finished match save was preserved for retry.")
            return False

    print("\n========== FINAL RESULTS ==========")
    print("Match ID:", match["match_id"])
    print("Reason:", reason)
    print("Rounds completed:", match["rounds_completed"])
    show_leaderboard(match)
    winner_ids = calculate_winner_ids(match, reason)
    winners = [p for p in match["players"] if p["player_id"] in winner_ids]
    if not winners:
        print("\nNo winner — all players left the match.")
    elif len(winners) == 1:
        print("\nWINNER:", winners[0]["name"])
    else:
        print("\nIT'S A TIE!")
        print("Tied players:", ", ".join(p["name"] for p in winners))

    # History is now safely stored; remove the save only after that succeeds.
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
        print("\nMatch recorded in history.")
    except OSError as error:
        print("Match was recorded, but the finished save remains:", error)
    return True

# ============================================================
# SYSTEM 4: SAVE VALIDATION AND RESUME
# ============================================================

def load_saved_match():
    if not os.path.exists(SAVE_FILE):
        return None
    match = load_json_file(SAVE_FILE, None)
    if not isinstance(match, dict):
        print("Saved match could not be read. File was preserved for inspection.")
        return None
    required = ["match_id", "players", "phase", "round_number", "rounds_completed", "round_history", "difficulty"]
    if not all(key in match for key in required):
        print("Saved match is invalid or incomplete. File was preserved.")
        return None
    if not isinstance(match.get("players"), list) or not match["players"]:
        print("Saved match has no valid player list. File was preserved.")
        return None
    if not isinstance(match.get("difficulty"), dict):
        print("Saved match difficulty is invalid. File was preserved.")
        return None
    # Defaults allow older V2 saves to continue without resetting them.
    match.setdefault("current_player_index", 0)
    match.setdefault("current_attempts", 0)
    match.setdefault("round_scores", {})
    match.setdefault("end_reason", None)
    match.setdefault("range_max", match["difficulty"].get("maximum", 100))
    match.setdefault("max_attempts", match["difficulty"].get("attempts", 5))
    match.setdefault("multiplier", match["difficulty"].get("multiplier", 1.0))
    match.setdefault("mode", "single")
    match.setdefault("match_type", "quick")
    match.setdefault("rounds_target", 5)
    match.setdefault("target_score", None)
    for player in match["players"]:
        if not isinstance(player, dict) or not player.get("player_id"):
            print("Saved match contains an invalid player. File was preserved.")
            return None
        player.setdefault("status", "active")
        player.setdefault("round_status", "pending")
        player.setdefault("round_score", 0)
        player.setdefault("score", 0)
    return match


def resume_match():
    match = load_saved_match()
    if match is None:
        print("\nNo valid saved match was found.")
        return "menu"
    if match.get("phase") == "finished":
        finish_match(match, match.get("end_reason") or "finished")
        return "menu"
    print("\nResuming match:", match["match_id"])
    print("Round:", match["round_number"])
    print("Completed rounds:", match["rounds_completed"])
    return run_match(match)

# ============================================================
# SYSTEM 4B: POST-ROUND MENU AND MATCH LOOP
# ============================================================

def reset_match(match, difficulty=None):
    """Start a genuinely new match while keeping the same participants/type."""
    match["match_id"] = new_id("M")
    if difficulty is not None:
        match["difficulty"] = difficulty
        match["range_max"] = difficulty["maximum"]
        match["max_attempts"] = difficulty["attempts"]
        match["multiplier"] = difficulty["multiplier"]
    match["round_number"] = 1
    match["rounds_completed"] = 0
    match["round_secret"] = None
    match["current_player_index"] = 0
    match["current_attempts"] = 0
    match["round_history"] = []
    match["round_scores"] = {}
    match["end_reason"] = None
    match["created_at"] = current_timestamp()
    match["phase"] = "between_rounds"
    for player in match["players"]:
        player["score"] = 0
        player["status"] = "active"
        player["round_status"] = "pending"
        player["round_score"] = 0


def post_round_menu(match):
    reason = match_end_reason(match)
    if reason:
        finish_match(match, reason)
        return "done"
    print("\n========== MATCH OPTIONS ==========")
    print("1. Continue to next round")
    print("2. Finish match and view final results")
    print("3. Rematch with same players")
    print("4. Change difficulty and start fresh")
    print("5. Save and return to main menu")
    print("6. Save and exit game")
    while True:
        choice = input("Choose an option: ").strip()
        if choice == "1":
            match["round_number"] += 1
            start_round(match)
            return "continue"
        if choice == "2":
            finish_match(match, "finished by player")
            return "done"
        if choice == "3":
            confirm = input("Reset scores and start a new match? (Y/N): ").strip().casefold()
            if confirm == "y":
                reset_match(match)
                start_round(match)
                return "continue"
            continue
        if choice == "4":
            difficulty = choose_difficulty()
            # Do not overwrite the old match unless it was recorded successfully.
            if not finish_match(match, "difficulty changed"):
                print("Could not safely close the old match. Try again after checking storage.")
                return "menu"
            reset_match(match, difficulty)
            start_round(match)
            return "continue"
        if choice == "5":
            if save_match(match):
                print("Progress saved. Returning to main menu.")
                return "menu"
            print("Save failed; please try again before leaving this menu.")
            continue
        if choice == "6":
            if save_match(match):
                print("Progress saved. Exiting.")
                return "exit"
            print("Save failed; please try again before leaving this menu.")
            continue
        print("Invalid choice. Enter 1 to 6.")


def run_match(match):
    while True:
        if match.get("phase") == "playing":
            play_round(match)
        reason = match_end_reason(match)
        if reason:
            finish_match(match, reason)
            return "done"
        action = post_round_menu(match)
        if action == "continue":
            continue
        if action == "menu":
            return "menu"
        if action == "exit":
            return "exit"
        return "done"

# ============================================================
# SYSTEM 5A: MATCH HISTORY
# ============================================================

def load_history():
    history = load_json_file(HISTORY_FILE, {"version": 1, "matches": []})
    if history is None:
        return None
    if isinstance(history, list):
        return {"version": 1, "matches": history}
    if isinstance(history, dict) and isinstance(history.get("matches"), list):
        return history
    print("History database format is invalid. Existing file was preserved.")
    return None


def view_match_history():
    history = load_history()
    if history is None:
        return
    matches = history["matches"]
    print("\n========== MATCH HISTORY ==========")
    if not matches:
        print("No completed matches recorded yet.")
        return
    for index, match in enumerate(reversed(matches), start=1):
        print(f"\n{index}. Match ID: {match.get('match_id', 'Unknown')}")
        print("Completed:", match.get("completed_at", "Unknown"))
        print("Mode/type/difficulty:", match.get("mode", "?"), "/", match.get("match_type", "?"), "/", match.get("difficulty", "?"))
        print("Rounds:", match.get("rounds_completed", 0))
        print("End reason:", match.get("end_reason", "Unknown"))
        for player in match.get("players", []):
            print(f"   {player.get('name', '?')} | ID: {player.get('player_id', '?')} | Score: {player.get('score', 0)} | {player.get('status', '?')}")


def clear_history():
    history = load_history()
    if history is None:
        return
    if not history["matches"]:
        print("History is already empty.")
        return
    confirm = input("Delete ALL completed match history? Type YES to confirm: ").strip()
    if confirm == "YES":
        if save_json_file(HISTORY_FILE, {"version": 1, "matches": []}):
            print("Match history cleared.")
    else:
        print("History was not changed.")

# ============================================================
# SYSTEM 5B: CAREER STATISTICS AND LEADERBOARD
# ============================================================

def view_statistics(profiles):
    history = load_history()
    if history is None:
        return
    matches = history["matches"]
    print("\n========== CAREER STATISTICS ==========")
    print("Completed matches:", len(matches))
    stats = {}
    for match in matches:
        winner_ids = match.get("winner_ids", [])
        for player in match.get("players", []):
            player_id = player.get("player_id")
            if not player_id:
                continue
            item = stats.setdefault(player_id, {"name": player.get("name", "Unknown"), "matches": 0, "wins": 0, "ties": 0, "points": 0, "best": 0})
            score = player.get("score", 0)
            item["matches"] += 1
            item["points"] += score
            item["best"] = max(item["best"], score)
            if player_id in winner_ids:
                if len(winner_ids) > 1:
                    item["ties"] += 1
                else:
                    item["wins"] += 1
    current_names = {p["player_id"]: p["display_name"] for p in profiles}
    if not stats:
        print("Play and finish a match to generate statistics.")
        return
    ordered = sorted(stats.items(), key=lambda pair: (pair[1]["points"], pair[1]["wins"]), reverse=True)
    for place, (player_id, item) in enumerate(ordered, start=1):
        name = current_names.get(player_id, item["name"])
        average = item["points"] / item["matches"] if item["matches"] else 0
        print(f"\n{place}. {name}")
        print("Player ID:", player_id)
        print("Matches:", item["matches"])
        print("Wins:", item["wins"])
        print("Ties:", item["ties"])
        print("Total points:", item["points"])
        print(f"Average points: {average:.2f}")
        print("Best match score:", item["best"])


def career_leaderboard(profiles):
    history = load_history()
    if history is None:
        return
    totals = {}
    for match in history["matches"]:
        for player in match.get("players", []):
            player_id = player.get("player_id")
            if not player_id:
                continue
            item = totals.setdefault(player_id, {"name": player.get("name", "Unknown"), "points": 0, "matches": 0})
            item["points"] += player.get("score", 0)
            item["matches"] += 1
    current_names = {p["player_id"]: p["display_name"] for p in profiles}
    print("\n========== CAREER LEADERBOARD ==========")
    ordered = sorted(totals.items(), key=lambda pair: pair[1]["points"], reverse=True)
    if not ordered:
        print("No career records yet.")
        return
    for rank, (player_id, item) in enumerate(ordered, start=1):
        name = current_names.get(player_id, item["name"])
        print(f"{rank}. {name} | ID: {player_id} | Total points: {item['points']} | Matches: {item['matches']}")

# ============================================================
# SYSTEM 6: LOGIN AND MAIN MENU
# ============================================================

def login_menu(profiles):
    while True:
        print("\n========== NUMBER GAME V2 ==========")
        print("1. Log in / Select player")
        print("2. Create new player")
        print("3. Exit game")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            selected = select_player(profiles)
            if selected is not None:
                return selected
        elif choice == "2":
            selected = create_player(profiles)
            if selected is not None:
                return selected
        elif choice == "3":
            return None
        else:
            print("Invalid choice.")


def main_menu(profiles, active_profile):
    while True:
        print("\n" + "=" * 42)
        print("           NUMBER GAME V2")
        print("=" * 42)
        print("Logged in:", active_profile["display_name"])
        print("Player ID:", active_profile["player_id"])
        print("\n1. New Match")
        print("2. Continue Previous Match")
        print("3. View Match History")
        print("4. View Career Statistics")
        print("5. Career Leaderboard")
        print("6. View Current Profile")
        print("7. Rename Current Player")
        print("8. Switch Player / Log Out")
        print("9. Clear Match History")
        print("10. Exit Game")
        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            if os.path.exists(SAVE_FILE):
                confirm = input("An unfinished match exists. Replace it? (Y/N): ").strip().casefold()
                if confirm != "y":
                    print("Existing match preserved.")
                    continue
            match = create_match(profiles, active_profile)
            if match is not None:
                if save_match(match):
                    # Start and save the first round before the first guess.
                    start_round(match)
                    result = run_match(match)
                    if result == "exit":
                        return "exit"
                else:
                    print("Match was not started because its initial save failed.")

        elif choice == "2":
            if not os.path.exists(SAVE_FILE):
                print("No unfinished match was found.")
            else:
                result = resume_match()
                if result == "exit":
                    return "exit"

        elif choice == "3":
            view_match_history()
        elif choice == "4":
            view_statistics(profiles)
        elif choice == "5":
            career_leaderboard(profiles)
        elif choice == "6":
            view_profile(active_profile)
        elif choice == "7":
            active_profile = rename_player(profiles, active_profile)
        elif choice == "8":
            selected = login_menu(profiles)
            if selected is None:
                return "exit"
            active_profile = selected
        elif choice == "9":
            clear_history()
        elif choice == "10":
            print("Thanks for playing Number Game V2!")
            return "exit"
        else:
            print("Invalid choice. Choose a listed option.")

# ============================================================
# SYSTEM 7: START PROGRAM
# ============================================================

def main():
    print("=" * 42)
    print("       NUMBER GAME V2")
    print("  PLAYER PROFILES + FULL GAME SYSTEM")
    print("=" * 42)
    profiles = load_profiles()
    if profiles is None:
        print("Could not safely load profiles. Check number_game_profiles.json.")
        return
    while True:
        active_profile = login_menu(profiles)
        if active_profile is None:
            print("Game closed.")
            break
        result = main_menu(profiles, active_profile)
        if result == "exit":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGame interrupted. Progress from the last successful save should remain available.")
    except EOFError:
        print("\nInput ended. Progress from the last successful save should remain available.")
