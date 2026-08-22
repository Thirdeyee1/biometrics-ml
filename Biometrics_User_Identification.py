# =========================================================
# REAL-TIME BEHAVIORAL USER DETECTOR
# =========================================================

import math
import threading
import time
import ctypes
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
import tkinter as tk
from pynput import keyboard, mouse
from pynput.keyboard import Key
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from tkinter import messagebox

# =========================================================
# CONFIG
# =========================================================

CSV_FILE = Path("csv_merged.csv")
WINDOW_SECONDS = 5
PAUSE_THRESHOLD = 2.0
BANNED_USERS = ["david"]
CONFIDENCE_THRESHOLD = 0.60
STABILITY_WINDOW = 5
MIN_WINDOW_COUNT_BEFORE_WARNING = 3

try:
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
except Exception:
    screen_width, screen_height = 1920, 1080
screen_diagonal = math.hypot(screen_width, screen_height)

KEY_COLUMNS = [
    *[chr(x) for x in range(ord("a"), ord("z") + 1)],
    *[str(x) for x in range(10)],
    "dot",
    "comma",
    "question",
    "colon",
    "ctrl",
    "shift",
    "enter",
    "backspace",
    "space",
]

DIGRAPH_VALID_KEYS = set(
    [*KEY_COLUMNS]  # same as the collection script
)

# =========================================================
# HELPERS
# =========================================================

SPECIAL_KEY_MAP = {
    Key.space: "space",
    Key.enter: "enter",
    Key.backspace: "backspace",
    Key.shift: "shift",
    Key.shift_l: "shift",
    Key.shift_r: "shift",
    Key.ctrl: "ctrl",
    Key.ctrl_l: "ctrl",
    Key.ctrl_r: "ctrl",
}

PUNCTUATION_MAP = {
    ".": "dot",
    ",": "comma",
    "?": "question",
    ":": "colon",
}


def normalize_key(key):
    if hasattr(key, "char") and key.char is not None:
        char = key.char.lower()
        if char in KEY_COLUMNS:
            return char
        if char in PUNCTUATION_MAP:
            return PUNCTUATION_MAP[char]
        if char.isalpha() or char.isdigit():
            return char
    if key in SPECIAL_KEY_MAP:
        return SPECIAL_KEY_MAP[key]
    return None


# =========================================================
# LOAD DATASET
# =========================================================

df = pd.read_csv(CSV_FILE)
df.fillna(0, inplace=True)

le = LabelEncoder()
df["user_id_encoded"] = le.fit_transform(df["user_id"])

unused_columns = [
    "user_id",
    "user_id_encoded",
    "timestamp",
    "window_index",
    "session_id",
    "session_type",
    "event_type",
]

feature_columns = [
    c for c in df.columns
    if c not in unused_columns
]

X = df[feature_columns].select_dtypes(include=[np.number])
y = df["user_id_encoded"]

X_train_full, X_test_full, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y,
)

rf_initial = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_leaf=6,
    max_features="sqrt",
    random_state=42,
    n_jobs=-1,
)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(rf_initial, X_train_full, y_train, cv=cv, scoring="accuracy", n_jobs=-1)
rf_initial.fit(X_train_full, y_train)

importances = pd.Series(
    rf_initial.feature_importances_,
    index=X_train_full.columns,
).sort_values(ascending=False)

# Only keep the strongest features by importance to reduce overfitting.
top_features = importances.head(20).index.tolist()

X_train = X_train_full[top_features]
X_test = X_test_full[top_features]

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_leaf=6,
    max_features="sqrt",
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)

print("Model trained successfully.")
print("CV mean accuracy:", cv_scores.mean())
print("CV std accuracy:", cv_scores.std())
print("Test accuracy:", accuracy_score(y_test, model.predict(X_test)))
print(classification_report(y_test, model.predict(X_test), target_names=le.classes_))
print("Selected top features:", top_features)

# =========================================================
# REAL-TIME FEATURE STATE
# =========================================================

mouse_positions = []
mouse_x_positions = []
mouse_y_positions = []
mouse_dx_history = []
mouse_dy_history = []
mouse_distances = []
mouse_speeds = []
mouse_accels = []
mouse_direction_changes = [0]

mouse_left_click = 0
mouse_right_click = 0
click_press_times = {}
click_durations = []

scroll_events = 0
scroll_dy_sum = 0.0
scroll_speeds = []

key_counts = {k: 0 for k in KEY_COLUMNS}
total_key_presses = 0
backspace_count = 0
key_press_times = {}
press_timestamps = []
pp_intervals = []
digraph_intervals = []
hold_times = []
last_key_time = None
last_press_time = None
last_release_time = None
pause_count = 0
burst_chars = 0

last_mouse_pos = None
last_mouse_time = None

prediction_history = deque(maxlen=STABILITY_WINDOW)
running = True
window_start_time = time.time()

# =========================================================
# MOUSE EVENTS
# =========================================================

def on_move(x, y):
    global last_mouse_pos, last_mouse_time

    now = time.time()
    if last_mouse_pos is not None and last_mouse_time is not None:
        dx = x - last_mouse_pos[0]
        dy = y - last_mouse_pos[1]
        dist = math.hypot(dx, dy)
        dt = now - last_mouse_time

        normalized_distance = dist / screen_diagonal if screen_diagonal > 0 else 0.0
        speed = (dist / dt) / screen_diagonal if dt > 0 else 0.0

        mouse_x_positions.append(x / screen_width if screen_width else 0.0)
        mouse_y_positions.append(y / screen_height if screen_height else 0.0)
        mouse_dx_history.append(dx)
        mouse_dy_history.append(dy)
        mouse_distances.append(normalized_distance)
        mouse_speeds.append(speed)

        if len(mouse_speeds) > 1:
            mouse_accels.append((mouse_speeds[-1] - mouse_speeds[-2]) / dt if dt > 0 else 0.0)

        if len(mouse_dx_history) > 1:
            if (mouse_dx_history[-2] > 0) != (mouse_dx_history[-1] > 0):
                mouse_direction_changes[0] += 1

        mouse_positions.append((x, y))

    else:
        mouse_x_positions.append(x / screen_width if screen_width else 0.0)
        mouse_y_positions.append(y / screen_height if screen_height else 0.0)

    last_mouse_pos = (x, y)
    last_mouse_time = now


def on_click(x, y, button, pressed):
    global mouse_left_click, mouse_right_click

    if pressed:
        if button == mouse.Button.left:
            mouse_left_click += 1
        elif button == mouse.Button.right:
            mouse_right_click += 1
        click_press_times[button] = time.time()
    else:
        if button in click_press_times:
            click_durations.append(time.time() - click_press_times.pop(button, time.time()))


def on_scroll(x, y, dx, dy):
    global scroll_events, scroll_dy_sum

    now = time.time()
    scroll_events += 1
    scroll_dy_sum += abs(dy)
    scroll_speed = (abs(dx) + abs(dy)) / max(0.001, now - (last_mouse_time or now))
    scroll_speeds.append(scroll_speed)

# =========================================================
# KEYBOARD EVENTS
# =========================================================

def on_press(key):
    global total_key_presses, backspace_count, last_press_time, last_release_time, burst_chars, pause_count

    key_name = normalize_key(key)
    now = time.time()

    if key_name is None:
        return

    total_key_presses += 1
    key_counts[key_name] = key_counts.get(key_name, 0) + 1
    if key_name == "backspace":
        backspace_count += 1

    if last_press_time is not None and (now - last_press_time) < 5.0:
        pp_intervals.append(now - last_press_time)
    last_press_time = now

    if last_release_time is not None:
        gap = now - last_release_time
        if gap > 1.0:
            pause_count += 1
        if gap < 0.3:
            burst_chars += 1

    key_press_times[key_name] = now


def on_release(key):
    global last_release_time

    key_name = normalize_key(key)
    now = time.time()
    if key_name is None:
        return
    if key_name in key_press_times:
        hold_times.append(now - key_press_times.pop(key_name, now))
    if key_name in DIGRAPH_VALID_KEYS:
        if last_release_time is not None and (now - last_release_time) < 5.0:
            digraph_intervals.append(now - last_release_time)
        last_release_time = now

# =========================================================
# FEATURE EXTRACTION
# =========================================================

def reset_window_state():
    global mouse_positions, mouse_x_positions, mouse_y_positions, mouse_dx_history, mouse_dy_history
    global mouse_distances, mouse_speeds, mouse_accels, mouse_direction_changes
    global click_durations, scroll_events, scroll_dy_sum, scroll_speeds
    global key_counts, total_key_presses, backspace_count, key_press_times
    global press_timestamps, pp_intervals, digraph_intervals, hold_times
    global last_key_time, last_press_time, last_release_time, burst_chars, pause_count
    global last_mouse_pos, last_mouse_time, window_start_time

    mouse_positions = []
    mouse_x_positions = []
    mouse_y_positions = []
    mouse_dx_history = []
    mouse_dy_history = []
    mouse_distances = []
    mouse_speeds = []
    mouse_accels = []
    mouse_direction_changes = [0]
    click_durations = []
    scroll_events = 0
    scroll_dy_sum = 0.0
    scroll_speeds = []
    key_counts = {k: 0 for k in KEY_COLUMNS}
    total_key_presses = 0
    backspace_count = 0
    key_press_times = {}
    press_timestamps = []
    pp_intervals = []
    digraph_intervals = []
    hold_times = []
    last_key_time = None
    last_press_time = None
    last_release_time = None
    burst_chars = 0
    pause_count = 0
    last_mouse_pos = None
    last_mouse_time = None
    window_start_time = time.time()


def compute_typing_metrics():
    pp_array = np.array(pp_intervals, dtype=float) if pp_intervals else np.array([], dtype=float)
    digraph_array = np.array(digraph_intervals, dtype=float) if digraph_intervals else np.array([], dtype=float)
    burst_ratio = float(burst_chars) / max(1, total_key_presses)

    elapsed_seconds = max(1.0, time.time() - window_start_time)
    typed_chars = total_key_presses - key_counts.get("ctrl", 0) - key_counts.get("shift", 0)
    wpm = (typed_chars / 5.0) / (elapsed_seconds / 60.0)

    return {
        "total_key_presses": total_key_presses,
        "backspace_rate": backspace_count / max(1, total_key_presses),
        "pause_count": pause_count,
        "burst_ratio": burst_ratio,
        "wpm": float(wpm),
        "avg_hold_time": float(np.mean(hold_times)) if hold_times else 0.0,
        "avg_digraph_latency": float(np.mean(digraph_array)) if digraph_array.size > 0 else 0.0,
        "avg_pp_latency": float(np.mean(pp_array)) if pp_array.size > 0 else 0.0,
    }


def compute_mouse_metrics():
    total_distance = float(np.sum(mouse_distances)) if mouse_distances else 0.0
    average_speed = float(np.mean(mouse_speeds)) if mouse_speeds else 0.0
    average_accel = float(np.mean(mouse_accels)) if mouse_accels else 0.0
    average_x = float(np.mean(mouse_x_positions)) if mouse_x_positions else 0.0
    average_y = float(np.mean(mouse_y_positions)) if mouse_y_positions else 0.0
    straight_line = 0.0
    if len(mouse_x_positions) > 1 and len(mouse_y_positions) > 1:
        straight_line = math.dist(
            (mouse_x_positions[0], mouse_y_positions[0]),
            (mouse_x_positions[-1], mouse_y_positions[-1]),
        )

    path_efficiency = 1.0
    if total_distance > 0:
        path_efficiency = min(1.0, straight_line / total_distance)

    direction_changes = 0
    if len(mouse_dx_history) > 1:
        direction_changes = sum(
            1 for i in range(1, len(mouse_dx_history))
            if (mouse_dx_history[i - 1] > 0) != (mouse_dx_history[i] > 0)
        )

    avg_scroll = float(scroll_dy_sum) / scroll_events if scroll_events > 0 else 0.0

    return {
        "mouse_avg_x": average_x,
        "mouse_avg_y": average_y,
        "mouse_avg_speed": average_speed,
        "mouse_avg_accel": average_accel,
        "mouse_path_efficiency": path_efficiency,
        "mouse_total_distance": total_distance,
        "mouse_direction_changes": direction_changes,
        "mouse_left_click": mouse_left_click,
        "mouse_right_click": mouse_right_click,
        "avg_click_dwell_time": float(np.mean(click_durations)) if click_durations else 0.0,
        "scroll_events": int(scroll_events),
        "avg_scroll_speed": avg_scroll,
    }


def extract_features():
    features = compute_typing_metrics()
    features.update(compute_mouse_metrics())
    features.update({k: float(key_counts.get(k, 0)) for k in KEY_COLUMNS})

    feature_df = pd.DataFrame([features])
    for col in top_features:
        if col not in feature_df.columns:
            feature_df[col] = 0.0
    feature_df = feature_df[top_features]
    return feature_df


# =========================================================
# REAL-TIME PREDICTION LOOP
# =========================================================

def prediction_loop():
    global mouse_left_click, mouse_right_click, total_key_presses, backspace_count

    sample_count = 0
    while running:
        time.sleep(WINDOW_SECONDS)

        feature_df = extract_features()
        prediction = model.predict(feature_df)[0]
        probabilities = model.predict_proba(feature_df)[0]
        confidence = float(np.max(probabilities))
        predicted_user = le.inverse_transform([prediction])[0]

        prediction_history.append(predicted_user)
        sample_count += 1

        if len(prediction_history) >= STABILITY_WINDOW:
            stable_prediction = max(set(prediction_history), key=prediction_history.count)
        else:
            stable_prediction = predicted_user

        status_text = f"Current: {stable_prediction}\nConfidence: {confidence:.2f}"
        if confidence < CONFIDENCE_THRESHOLD or sample_count < MIN_WINDOW_COUNT_BEFORE_WARNING:
            status_text += "\nStatus: low confidence"
        else:
            status_text += "\nStatus: high confidence"

        root.after(0, lambda: status_label.config(text=status_text))
        print(f"Detected User: {stable_prediction} (Confidence: {confidence:.2f})")

        if (
            sample_count >= MIN_WINDOW_COUNT_BEFORE_WARNING and
            confidence >= CONFIDENCE_THRESHOLD and
            stable_prediction.lower() in [u.lower() for u in BANNED_USERS]
        ):
            messagebox.showwarning(
                "WARNING",
                f"{stable_prediction} is not allowed to use this computer!",
            )

        reset_window_state()


# =========================================================
# GUI
# =========================================================

root = tk.Tk()
root.title("Behavioral User Detector")
root.geometry("300x150")
screen_width = root.winfo_screenwidth()
root.geometry(f"+{screen_width - 320}+20")

status_label = tk.Label(
    root,
    text="Current: Unknown\nConfidence: 0.00",
    font=("Arial", 12),
    justify="center",
    anchor="center",
)
status_label.pack(expand=True, pady=20)


def stop_program():
    global running
    running = False
    keyboard_listener.stop()
    mouse_listener.stop()
    root.destroy()

stop_button = tk.Button(
    root,
    text="STOP",
    command=stop_program,
    bg="red",
    fg="white",
    font=("Arial", 12),
)
stop_button.pack(side="bottom", pady=10)

# =========================================================
# START LISTENERS
# =========================================================

keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)

keyboard_listener.start()
mouse_listener.start()

# =========================================================
# START PREDICTION THREAD
# =========================================================

prediction_thread = threading.Thread(target=prediction_loop, daemon=True)
prediction_thread.start()
print("Real-time behavioral detector running...")
root.mainloop()
