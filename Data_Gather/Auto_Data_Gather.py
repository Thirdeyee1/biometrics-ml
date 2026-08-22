import csv
import time
from pynput import keyboard, mouse
import string
import math
import ctypes
import os
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

print("SCRIPT STARTED")

# =========================
# CONFIG
# =========================
VALID_USERS = {"david", "carlos", "precious", "marjorie"}
USER_ID = input("Enter User ID: ").strip().lower()
while USER_ID not in VALID_USERS:
    print("Invalid name. Accepted names are: david, carlos, precious, marjorie")
    USER_ID = input("Enter User ID: ").strip().lower()

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "behavior_dataset.csv")

# =========================
# SESSION TRACKER
# =========================
def get_session_status(user_id, filepath):
    status = {}
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("user_id", "").strip().lower() != user_id:
                        continue
                    sid = row.get("session_id", "").strip().lower()
                    stype = row.get("session_type", "").strip().lower()
                    try:
                        parts = sid.split("_")
                        day_num = int(parts[0].replace("day", ""))
                        if day_num not in status:
                            status[day_num] = {"controlled": False, "random": False}
                        if stype in ("controlled", "random"):
                            status[day_num][stype] = True
                    except:
                        pass
        except Exception as e:
            print(f"[Session tracker error] {e}")
    return status

status = get_session_status(USER_ID, OUTPUT_FILE)

# Figure out current day and what is still needed
current_day = 1
for day in sorted(status.keys()):
    if status[day]["controlled"] and status[day]["random"]:
        current_day = day + 1
    else:
        current_day = day
        break

if current_day not in status:
    status[current_day] = {"controlled": False, "random": False}

controlled_done = status[current_day]["controlled"]
random_done = status[current_day]["random"]

# Print session summary
print("")
print(f"=== SESSION SUMMARY FOR: {USER_ID.upper()} ===")
if len(status) == 0 or (len(status) == 1 and not controlled_done and not random_done):
    print("  No sessions recorded yet.")
else:
    for day in sorted(status.keys()):
        c = "DONE" if status[day]["controlled"] else "MISSING"
        r = "DONE" if status[day]["random"] else "MISSING"
        print(f"  Day {day} — Controlled: {c} | Random: {r}")

print("")
print(f"  Current day: Day {current_day}")

# Determine which session types are still available today
available = []
if not controlled_done:
    available.append("controlled")
if not random_done:
    available.append("random")

if not available:
    print(f"  Day {current_day} is fully complete. You are on Day {current_day + 1} next.")
    print("==========================================")
    input("Press Enter to exit.")
    exit()

print(f"  Still needed today: {' and '.join(t.upper() for t in available)}")
print("==========================================")
print("")

# Ask which session type to run
if len(available) == 1:
    SESSION_TYPE = available[0]
    print(f"  Only session remaining for today: {SESSION_TYPE.upper()}")
    print(f"  Session ID will be: day{current_day}_{SESSION_TYPE}")
    confirm = input("  Press Enter to start, or type 'exit' to quit: ").strip().lower()
    if confirm == "exit":
        exit()
else:
    print(f"  Which session do you want to do now?")
    print(f"    1 = controlled")
    print(f"    2 = random")
    choice = input("  Enter 1 or 2: ").strip()
    while choice not in ("1", "2"):
        print("  Invalid. Enter 1 for controlled or 2 for random.")
        choice = input("  Enter 1 or 2: ").strip()
    SESSION_TYPE = "controlled" if choice == "1" else "random"
    print(f"  Session ID will be: day{current_day}_{SESSION_TYPE}")
    confirm = input("  Press Enter to start, or type 'exit' to quit: ").strip().lower()
    if confirm == "exit":
        exit()

# Auto-generate session ID
SESSION_ID = f"day{current_day}_{SESSION_TYPE}"
print(f"  Starting: {USER_ID.upper()} | {SESSION_ID} | {SESSION_TYPE.upper()}")
print("")

TOTAL_DURATION = 600 # set 600 for 10 minutes
WINDOW_SIZE = 5

# =========================
# HELPER: GET ACTIVE WINDOW
# =========================
# NOTE: active_window is commented out for now.
# can cause domain mismatch between home and lab window titles,
# and raises privacy concerns during random sessions.
# Uncomment only if needed for debugging purposes.

# def get_active_window_title():
#     try:
#         hwnd = ctypes.windll.user32.GetForegroundWindow()
#         length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
#         buff = ctypes.create_unicode_buffer(length + 1)
#         ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
#         title = buff.value if buff.value else "Desktop"
#         return title.replace(",", "|")
#     except:
#         return "Unknown_Window"

# =========================
# SCREEN NORMALIZATION
# =========================
try:
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
except:
    screen_width, screen_height = 1920, 1080
screen_diagonal = math.sqrt(screen_width**2 + screen_height**2)
print(f"Screen: {screen_width}x{screen_height}, diagonal={round(screen_diagonal, 1)}")

# =========================
# GUI: TIMER (DAEMON THREAD)
# =========================
def start_timer_gui():
    try:
        timer_root = tk.Tk()
        timer_root.title("Timer")
        timer_root.geometry("120x60-20+40")
        timer_root.attributes("-topmost", True)
        label = tk.Label(timer_root, text="", font=("Arial", 14))
        label.pack(expand=True)

        start_t = time.time()
        def update():
            rem = max(0, int(TOTAL_DURATION - (time.time() - start_t)))
            label.config(text=f"{rem // 60:02d}:{rem % 60:02d}")
            if rem > 0:
                timer_root.after(1000, update)
            else:
                timer_root.destroy()
        update()
        timer_root.mainloop()
    except:
        pass

threading.Thread(target=start_timer_gui, daemon=True).start()

# =========================
# KEYS & CSV HEADER
# =========================
SPECIAL_KEYS = ["dot", "comma", "question", "colon", "ctrl", "shift", "enter", "backspace", "space"]
char_keys = list(string.ascii_lowercase + string.digits)
all_keys = char_keys + SPECIAL_KEYS
DIGRAPH_VALID_KEYS = set(char_keys + ["dot", "comma", "question", "colon", "enter", "backspace", "space"])

header = ["user_id", "session_id", "session_type", "timestamp", "window_index", "event_type"]
# header += ["active_window"]  # commented out — see note above
header += all_keys
header += [
    "wpm", "avg_hold_time", "avg_digraph_latency", "avg_pp_latency",
    "backspace_rate", "pause_count", "burst_ratio",
    "mouse_avg_x", "mouse_avg_y", "mouse_avg_speed", "mouse_avg_accel",
    "mouse_path_efficiency", "mouse_total_distance", "mouse_direction_changes",
    "mouse_left_click", "mouse_right_click", "avg_click_dwell_time",
    "scroll_events", "avg_scroll_speed"
]

file_exists = os.path.isfile(OUTPUT_FILE)
csv_file = open(OUTPUT_FILE, "a", newline="", buffering=1, encoding="utf-8")
writer = csv.writer(csv_file)
if not file_exists:
    writer.writerow(header)

# =========================
# DATA TRACKING
# =========================
def reset_window():
    return {
        "key_freq": {k: 0 for k in all_keys},
        "hold_sum": 0.0, "hold_count": 0,
        "digraph_sum": 0.0, "digraph_count": 0,
        "pp_latency_sum": 0.0, "pp_latency_count": 0,
        "total_chars": 0, "pause_count": 0, "burst_chars": 0,
        "mouse_x": [], "mouse_y": [], "mouse_speed": [],
        "mouse_distance": 0.0, "mouse_left_click": 0, "mouse_right_click": 0,
        "mouse_dx_history": [], "mouse_dy_history": [],
        "click_dwell_times": [], "scroll_events": 0, "scroll_dy_sum": 0.0,
    }

window = reset_window()
window_lock = threading.Lock()
pressed_keys, last_release_time, last_press_time = {}, None, None
pressed_mouse_buttons, window_index = {}, 0

# =========================
# KEY MAPPING
# =========================
def map_key(key):
    try:
        k = key.char.lower()
        mapping = {".": "dot", ",": "comma", "?": "question", ":": "colon"}
        return mapping.get(k, k if k in char_keys else None)
    except:
        k_map = {
            keyboard.Key.space: "space",
            keyboard.Key.enter: "enter",
            keyboard.Key.backspace: "backspace"
        }
        if key in k_map: return k_map[key]
        if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]: return "ctrl"
        if key in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r]: return "shift"
    return None

# =========================
# KEY EVENTS
# =========================
def on_press(key):
    global last_press_time, last_release_time
    now, mapped = time.time(), map_key(key)
    try:
        with window_lock:
            if mapped:
                window["key_freq"][mapped] += 1
                window["total_chars"] += 1
            k_str = str(key)
            if k_str not in pressed_keys:
                pressed_keys[k_str] = now
                if mapped in DIGRAPH_VALID_KEYS:
                    if last_press_time and (now - last_press_time < 5.0):
                        window["pp_latency_sum"] += (now - last_press_time)
                        window["pp_latency_count"] += 1
                    last_press_time = now
                    if last_release_time:
                        gap = now - last_release_time
                        if gap > 1.0: window["pause_count"] += 1
                        if gap < 0.3: window["burst_chars"] += 1
    except Exception as e:
        print(f"[on_press error] {e}")

def on_release(key):
    global last_release_time
    now, k_str, mapped = time.time(), str(key), map_key(key)
    try:
        with window_lock:
            if k_str in pressed_keys:
                hold = now - pressed_keys.pop(k_str)
                window["hold_sum"] += hold
                window["hold_count"] += 1
                if mapped in DIGRAPH_VALID_KEYS:
                    if last_release_time and (now - last_release_time < 5.0):
                        window["digraph_sum"] += (now - last_release_time)
                        window["digraph_count"] += 1
                    last_release_time = now
    except Exception as e:
        print(f"[on_release error] {e}")

# =========================
# MOUSE EVENTS
# =========================
mouse_last_pos, mouse_last_time = None, None

def on_move(x, y):
    global mouse_last_pos, mouse_last_time
    now = time.time()
    try:
        if mouse_last_pos is None:
            mouse_last_pos, mouse_last_time = (x, y), now
            return
        dx, dy = x - mouse_last_pos[0], y - mouse_last_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        dt = now - mouse_last_time
        speed = (dist / dt) / screen_diagonal if dt > 0 else 0
        with window_lock:
            window["mouse_x"].append(x / screen_width)
            window["mouse_y"].append(y / screen_height)
            window["mouse_speed"].append(speed)
            window["mouse_distance"] += dist / screen_diagonal
            window["mouse_dx_history"].append(dx)
            window["mouse_dy_history"].append(dy)
        mouse_last_pos, mouse_last_time = (x, y), now
    except Exception as e:
        print(f"[on_move error] {e}")

def on_click(x, y, button, pressed_state):
    now = time.time()
    try:
        with window_lock:
            if pressed_state:
                pressed_mouse_buttons[button] = now
                if button == mouse.Button.left: window["mouse_left_click"] += 1
                elif button == mouse.Button.right: window["mouse_right_click"] += 1
            elif button in pressed_mouse_buttons:
                window["click_dwell_times"].append(now - pressed_mouse_buttons.pop(button))
    except Exception as e:
        print(f"[on_click error] {e}")

def on_scroll(x, y, dx, dy):
    try:
        with window_lock:
            window["scroll_events"] += 1
            window["scroll_dy_sum"] += abs(dy)
    except Exception as e:
        print(f"[on_scroll error] {e}")

# =========================
# FLUSH WINDOW TO CSV
# =========================
def flush_window(snap, snap_index, actual_size):
    try:
        t_chars = snap["total_chars"]
        wpm = (t_chars / 5) * (60 / actual_size) if t_chars > 0 else 0

        speeds = snap["mouse_speed"]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        accels = [speeds[i] - speeds[i-1] for i in range(1, len(speeds))]
        avg_accel = sum(accels) / len(accels) if accels else 0

        path_eff = 1.0
        if len(snap["mouse_x"]) > 1:
            euc = math.dist(
                (snap["mouse_x"][0], snap["mouse_y"][0]),
                (snap["mouse_x"][-1], snap["mouse_y"][-1])
            )
            path_eff = euc / snap["mouse_distance"] if snap["mouse_distance"] > 0 else 1.0

        direction_changes = len([
            i for i in range(1, len(snap["mouse_dx_history"]))
            if (snap["mouse_dx_history"][i-1] > 0) != (snap["mouse_dx_history"][i] > 0)
        ])

        row = [
            USER_ID,
            SESSION_ID,
            SESSION_TYPE,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            snap_index,
            "window",
            # get_active_window_title(),  # commented out — see note above
        ]

        for k in all_keys:
            row.append(snap["key_freq"][k])

        row.extend([
            round(wpm, 2),
            round(snap["hold_sum"] / snap["hold_count"] if snap["hold_count"] > 0 else 0, 5),
            round(snap["digraph_sum"] / snap["digraph_count"] if snap["digraph_count"] > 0 else 0, 5),
            round(snap["pp_latency_sum"] / snap["pp_latency_count"] if snap["pp_latency_count"] > 0 else 0, 5),
            round(snap["key_freq"].get("backspace", 0) / t_chars if t_chars > 0 else 0, 5),
            snap["pause_count"],
            round(snap["burst_chars"] / t_chars if t_chars > 0 else 0, 5),
            round(sum(snap["mouse_x"]) / len(snap["mouse_x"]) if snap["mouse_x"] else 0, 4),
            round(sum(snap["mouse_y"]) / len(snap["mouse_y"]) if snap["mouse_y"] else 0, 4),
            round(avg_speed, 6),
            round(avg_accel, 6),
            round(path_eff, 5),
            round(snap["mouse_distance"], 6),
            direction_changes,
            snap["mouse_left_click"],
            snap["mouse_right_click"],
            round(sum(snap["click_dwell_times"]) / len(snap["click_dwell_times"]) if snap["click_dwell_times"] else 0, 5),
            snap["scroll_events"],
            round(snap["scroll_dy_sum"] / snap["scroll_events"] if snap["scroll_events"] > 0 else 0, 4)
        ])

        writer.writerow(row)
        print(f"[{SESSION_TYPE.upper()}] Window {snap_index} written — chars={t_chars}, wpm={round(wpm, 1)}")

    except Exception as e:
        print(f"[flush_window error] {e}")

# =========================
# START LISTENERS
# =========================
k_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
m_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
k_listener.start()
m_listener.start()

print(f"Recording [{SESSION_TYPE.upper()}] session for {TOTAL_DURATION}s in {WINDOW_SIZE}s windows. Expected rows: {TOTAL_DURATION // WINDOW_SIZE}")

# =========================
# MAIN LOOP
# =========================
start_time = last_win_time = time.time()
try:
    while time.time() - start_time < TOTAL_DURATION:
        if time.time() - last_win_time >= WINDOW_SIZE:
            with window_lock:
                snap, idx = dict(window), window_index
                window = reset_window()
                window_index += 1
            last_win_time += WINDOW_SIZE
            flush_window(snap, idx, WINDOW_SIZE)
        time.sleep(0.05)

finally:
    final_duration = time.time() - last_win_time
    if final_duration >= 1.0:
        with window_lock:
            snap, idx = dict(window), window_index
        print(f"[Final window] Flushing {round(final_duration, 1)}s of remaining data...")
        flush_window(snap, idx, max(final_duration, 1.0))
    else:
        print("[Final window] Less than 1s remaining, skipping.")

    k_listener.stop()
    m_listener.stop()
    csv_file.close()

# =========================
# DONE
# =========================
print(f"FINISHED — Total Windows Captured: {window_index}")
time.sleep(1)
final_root = tk.Tk()
final_root.withdraw()
messagebox.showinfo(
    "Done",
    f"Data collection completed!\nUser: {USER_ID}\nSession: {SESSION_ID}\nType: {SESSION_TYPE.upper()}\nWindows captured: {window_index}"
)
final_root.destroy()