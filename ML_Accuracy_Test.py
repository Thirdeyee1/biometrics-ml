import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.preprocessing import LabelEncoder

# Set plot style for professional clean visuals
sns.set_theme(style="whitegrid")

# =========================================================
# 1. LOAD DATASET & PRE-PROCESSING
# =========================================================
df = pd.read_csv("csv_merged.csv")
df.fillna(0, inplace=True)

# Map raw user names to anonymized stylized user tokens
user_mapping = {
    "carlos": "User 1",
    "david": "User 2",
    "precious": "User 3",
    "marjorie": "User 4"
}
df["user_id"] = df["user_id"].map(user_mapping).fillna(df["user_id"])

le = LabelEncoder()
df["user_id_encoded"] = le.fit_transform(df["user_id"])
classes = le.classes_

unused_columns = [
    "user_id", "user_id_encoded", "timestamp", "window_index",
    "session_id", "session_type", "event_type"
]
feature_columns = [c for c in df.columns if c not in unused_columns]

X = df[feature_columns].select_dtypes(include=[np.number])
y = df["user_id_encoded"]

# Stratified Train/Test Split (70:30)
X_train_full, X_test_full, y_train, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y
)

# =========================================================
# 2. COMPUTE INTERMEDIATE ENGINE DATA FOR APPLICABLE GRAPHS
# =========================================================
rf_initial = RandomForestClassifier(
    n_estimators=300, max_depth=12, min_samples_leaf=6,
    max_features="sqrt", random_state=42, n_jobs=-1
)
rf_initial.fit(X_train_full, y_train)

importances = pd.Series(
    rf_initial.feature_importances_, index=X_train_full.columns
).sort_values(ascending=False)

feature_counts = range(1, len(importances) + 1)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# --- Data Generation: Validation Curve over Features ---
train_mean_feats, train_std_feats = [], []
val_mean_feats, val_std_feats = [], []

for k in feature_counts:
    temp_features = importances.head(k).index.tolist()
    temp_model = RandomForestClassifier(n_estimators=100, max_depth=12, min_samples_leaf=6, random_state=42, n_jobs=-1)
    scores = cross_validate(temp_model, X_train_full[temp_features], y_train, cv=cv, scoring='accuracy', return_train_score=True, n_jobs=-1)
    train_mean_feats.append(np.mean(scores['train_score']))
    train_std_feats.append(np.std(scores['train_score']))
    val_mean_feats.append(np.mean(scores['test_score']))
    val_std_feats.append(np.std(scores['test_score']))

# --- Fit Final Optimized Model ---
top_features = importances.head(6).index.tolist()
X_train = X_train_full[top_features]
X_test = X_test_full[top_features]

optimized_model = RandomForestClassifier(
    n_estimators=300, max_depth=12, min_samples_leaf=6,
    max_features="sqrt", random_state=42, n_jobs=-1
)
optimized_model.fit(X_train, y_train)
y_pred = optimized_model.predict(X_test)
cm = confusion_matrix(y_test, y_pred)

# =========================================================
# 3. FUNCTION TO REDRAW ISOLATED PLOT FOR CLEAN PNG DOWNLOAD
# =========================================================
def save_isolated_plot(panel_id):
    fig_save, ax_save = plt.subplots(figsize=(8, 6))
    output_name = f"dashboard_{panel_id}.png"
    
    if panel_id == "Gini_Feature_Importance":
        importances.sort_values(ascending=True).plot(kind='barh', color='skyblue', edgecolor='black', ax=ax_save)
        ax_save.set_title("Feature Selection via Baseline Gini Importance", fontsize=12, fontweight='bold', pad=10)
        ax_save.set_xlabel("Gini Importance Score")
        ax_save.set_ylabel("Extracted Features")

    elif panel_id == "Feature_Validation_Curve":
        ax_save.plot(feature_counts, train_mean_feats, marker='o', color='#1f77b4', linewidth=2, label='Training Score')
        ax_save.fill_between(feature_counts, np.array(train_mean_feats) - np.array(train_std_feats), np.array(train_mean_feats) + np.array(train_std_feats), alpha=0.12, color='#1f77b4')
        ax_save.plot(feature_counts, val_mean_feats, marker='s', color='#ff7f0e', linewidth=2, label='Cross-Validation Score')
        ax_save.fill_between(feature_counts, np.array(val_mean_feats) - np.array(val_std_feats), np.array(val_mean_feats) + np.array(val_std_feats), alpha=0.12, color='#ff7f0e')
        ax_save.set_title("Validation Curve: Structural Feature Complexity", fontsize=12, fontweight='bold', pad=10)
        ax_save.set_xlabel("Model Complexity")
        ax_save.set_ylabel("Accuracy Score")
        ax_save.set_xticks(list(feature_counts))
        ax_save.legend(loc='lower right')

    elif panel_id == "Confusion_Matrix_Heatmap":
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes, cbar=True, ax=ax_save, annot_kws={"size": 11, "weight": "bold"})
        ax_save.set_title("Optimized Confusion Matrix", fontsize=12, fontweight='bold', pad=10)
        ax_save.set_xlabel("Predicted Behavioral Identity")
        ax_save.set_ylabel("True Behavioral Identity")
        ax_save.set_yticklabels(classes, rotation=0)

    plt.tight_layout()
    fig_save.savefig(output_name, dpi=300)
    plt.close(fig_save)
    print(f"Successfully exported clean, isolated graph panel to: {output_name}")

# =========================================================
# 4. CONSTRUCT THE MASTER DISPLAY DASHBOARD (IDENTICAL FIXED SIZES)
# =========================================================
fig = plt.figure(figsize=(15, 12), layout=None)

# Fixed subplot grid bounding configurations to guarantee size uniformity
ax_a = fig.add_axes([0.08, 0.56, 0.40, 0.36])  # Top-Left Panel
ax_b = fig.add_axes([0.56, 0.56, 0.40, 0.36])  # Top-Right Panel
ax_c = fig.add_axes([0.32, 0.08, 0.40, 0.36])  # Bottom-Center Panel

axes_list = [ax_a, ax_b, ax_c]
titles_list = ["Gini_Feature_Importance", "Feature_Validation_Curve", "Confusion_Matrix_Heatmap"]

# --- PANEL A: Gini Importance ---
importances.sort_values(ascending=True).plot(kind='barh', color='skyblue', edgecolor='black', ax=ax_a)
ax_a.set_title("A. Feature Selection via Baseline Gini Importance", fontsize=11, fontweight='bold', pad=10)
ax_a.set_xlabel("Gini Importance Score")
ax_a.set_ylabel("Extracted Features")

# --- PANEL B: Validation Curve ---
ax_b.plot(feature_counts, train_mean_feats, marker='o', color='#1f77b4', linewidth=2, label='Training Score')
ax_b.fill_between(feature_counts, np.array(train_mean_feats) - np.array(train_std_feats), np.array(train_mean_feats) + np.array(train_std_feats), alpha=0.12, color='#1f77b4')
ax_b.plot(feature_counts, val_mean_feats, marker='s', color='#ff7f0e', linewidth=2, label='Cross-Validation Score')
ax_b.fill_between(feature_counts, np.array(val_mean_feats) - np.array(val_std_feats), np.array(val_mean_feats) + np.array(val_std_feats), alpha=0.12, color='#ff7f0e')
ax_b.set_title("B. Validation Curve: Structural Feature Complexity", fontsize=11, fontweight='bold', pad=10)
ax_b.set_xlabel("Model Complexity")
ax_b.set_ylabel("Accuracy Score")
ax_b.set_xticks(list(feature_counts))
ax_b.legend(loc='lower right', fontsize=8.5)

# --- PANEL C: Optimized Confusion Matrix Heatmap ---
sns.heatmap(
    cm, annot=True, fmt='d', cmap='Blues', 
    xticklabels=classes, yticklabels=classes, cbar=True, ax=ax_c,
    annot_kws={"size": 11, "weight": "bold"}
)
ax_c.set_title("C. Optimized Confusion Matrix", fontsize=11, fontweight='bold', pad=10)
ax_c.set_xlabel("Predicted Behavioral Identity")
ax_c.set_ylabel("True Behavioral Identity")
ax_c.set_yticklabels(classes, rotation=0)

# Main centered dashboard title
fig.text(0.5, 0.96, "Advanced Random Forest Behavioral Evaluation Dashboard", fontsize=15, fontweight='bold', ha='center')

# =========================================================
# 5. CLICK INTERACTION HANDLER FOR INSTANT DOWNLOADS
# =========================================================
buttons = []
for idx, ax in enumerate(axes_list):
    btn = ax.text(
        1.0, 1.05, "Save PNG", 
        transform=ax.transAxes, fontsize=9, color="white", weight="bold",
        bbox=dict(boxstyle="square,pad=0.3", facecolor="#2b2b2b", edgecolor="none", alpha=0.85),
        picker=True, ha='right'
    )
    buttons.append((btn, titles_list[idx]))

def on_window_click(event):
    for btn, panel_id in buttons:
        if event.artist == btn:
            save_isolated_plot(panel_id)
            break

fig.canvas.mpl_connect('pick_event', on_window_click)

# =========================================================
# 6. TERMINAL METRICS REPORTING ENGINE (NEW ADDITION)
# =========================================================
print("\n" + "="*70)
print("              THESIS EXPERIMENTAL RUN SYSTEM LOGS                 ")
print("="*70)

print("\n[PART 1] GINI MEAN DECREASE IN IMPURITY FEATURE RANKINGS:")
for i, (fname, fscore) in enumerate(importances.items(), 1):
    print(f"  Rank {i:02d} | Feature: {fname:<24} | Gini Weight: {fscore:.4f}")

print("\n[PART 2] VALIDATION CURVE MODEL ANALYSIS OVER TIME:")
print(f"  {'Complexity (k)':<16} | {'Mean Train Acc':<16} | {'Mean CV Acc':<14} | {'Overfit Gap':<12}")
print("  " + "-"*65)
for idx, k in enumerate(feature_counts):
    gap = train_mean_feats[idx] - val_mean_feats[idx]
    print(f"  {k:<16} | {train_mean_feats[idx]:<16.4%} | {val_mean_feats[idx]:<14.4%} | {gap:<12.4%}")

print("\n[PART 3] MODEL OPTIMIZATION AND PRUNING RESULTS:")
print(f"  Selected Feature Optimization Cutoff Point: 6 Features")
print(f"  Features Retained: {top_features}")
print(f"  Final Hold-Out Testing Set Accuracy Achieved: {accuracy_score(y_test, y_pred):.4%}")

print("\n[PART 4] CLASSIFICATION REPORT FOR INDIVIDUAL ANONYMIZED PROFILES:")
print(classification_report(y_test, y_pred, target_names=classes))

print("[PART 5] TEXT-BASED CONFUSION MATRIX ARRAY MATRIX:")
print(f"  Order Matrix Keys: {list(classes)}")
print(cm)
print("="*70)

print("\nLaunching unified interactive 3-Graph Fixed Uniform Dashboard window pop-up...")
print("-> Click the dark 'Save PNG' label box above any plot to export it safely!")
plt.show()