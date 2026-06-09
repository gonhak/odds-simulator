import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from collections import deque

# ── ścieżka do CSV ──────────────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "..", "premier_league.csv")
output_dir = current_dir  # zapisujemy obok skryptu

# ════════════════════════════════════════════════════════════════════════════
# DECISION TREE – kopiujemy tylko to co potrzebne do predykcji
# ════════════════════════════════════════════════════════════════════════════
class TeamStats:
    def __init__(self):
        self.matches_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.last_points = deque(maxlen=5)
        self.last_goals_for = deque(maxlen=5)
        self.last_goals_against = deque(maxlen=5)
        self.elo = 1500.0

    def form_last_5(self):
        if len(self.last_points) == 0:
            return 0.5
        return sum(self.last_points) / (len(self.last_points) * 3)

    def avg_goals_for(self):
        return sum(self.last_goals_for) / len(self.last_goals_for) if self.last_goals_for else 1.2

    def avg_goals_against(self):
        return sum(self.last_goals_against) / len(self.last_goals_against) if self.last_goals_against else 1.2

    def win_rate(self):
        return self.wins / self.matches_played if self.matches_played else 0.5


def expected_score(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(hs, aws, result):
    k = 24
    he = expected_score(hs.elo + 60, aws.elo)
    ae = 1 - he
    s = {"H": (1.0, 0.0), "A": (0.0, 1.0)}.get(result, (0.5, 0.5))
    hs.elo += k * (s[0] - he)
    aws.elo += k * (s[1] - ae)


def update_team_stats(hs, aws, hg, ag, result):
    hs.matches_played += 1
    aws.matches_played += 1
    if result == "H":
        hs.wins += 1; aws.losses += 1; hp, ap = 3, 0
    elif result == "A":
        hs.losses += 1; aws.wins += 1; hp, ap = 0, 3
    else:
        hs.draws += 1; aws.draws += 1; hp, ap = 1, 1
    hs.last_points.append(hp); aws.last_points.append(ap)
    hs.last_goals_for.append(hg); hs.last_goals_against.append(ag)
    aws.last_goals_for.append(ag); aws.last_goals_against.append(hg)
    update_elo(hs, aws, result)


class DTNode:
    def __init__(self, fi=None, thr=None, left=None, right=None, value=None, probs=None):
        self.fi = fi; self.thr = thr; self.left = left; self.right = right
        self.value = value; self.probs = probs


class CustomDecisionTree:
    def __init__(self, max_depth=6, mss=4, msl=2):
        self.max_depth = max_depth; self.mss = mss; self.msl = msl; self.root = None

    def gini(self, y):
        if not len(y): return 0
        _, c = np.unique(y, return_counts=True)
        p = c / len(y)
        return 1 - np.sum(p ** 2)

    def majority(self, y):
        cls, cnt = np.unique(y, return_counts=True)
        return cls[np.argmax(cnt)]

    def dist(self, y):
        c = np.bincount(y, minlength=3) + 1
        return c / c.sum()

    def thresholds(self, v):
        u = np.unique(v)
        return u if len(u) <= 10 else np.percentile(u, [10,20,30,40,50,60,70,80,90])

    def best_split(self, X, y):
        bf = bt = None; bs = float("inf")
        ns, nf = X.shape
        for fi in range(nf):
            for thr in self.thresholds(X[:, fi]):
                lm = X[:, fi] <= thr; rm = ~lm
                yl, yr = y[lm], y[rm]
                if len(yl) < self.msl or len(yr) < self.msl: continue
                wg = len(yl)/ns*self.gini(yl) + len(yr)/ns*self.gini(yr)
                if wg < bs: bs = wg; bf = fi; bt = thr
        return bf, bt

    def build(self, X, y, d):
        if d >= self.max_depth or len(y) < self.mss or len(np.unique(y)) == 1:
            return DTNode(value=self.majority(y), probs=self.dist(y))
        fi, thr = self.best_split(X, y)
        if fi is None:
            return DTNode(value=self.majority(y), probs=self.dist(y))
        lm = X[:, fi] <= thr
        return DTNode(fi=fi, thr=thr,
                      left=self.build(X[lm], y[lm], d+1),
                      right=self.build(X[~lm], y[~lm], d+1))

    def fit(self, X, y): self.root = self.build(X, y, 0)

    def pred1(self, x, n):
        if n.left is None and n.right is None: return n.value
        return self.pred1(x, n.left) if x[n.fi] <= n.thr else self.pred1(x, n.right)

    def predict(self, X): return np.array([self.pred1(x, self.root) for x in X])


def run_decision_tree():
    df = pd.read_csv(csv_path, usecols=["HomeTeam","AwayTeam","FTHG","FTAG","FTR"])
    team_stats = {}

    def gs(t):
        if t not in team_stats: team_stats[t] = TeamStats()
        return team_stats[t]

    def features(ht, at):
        h, a = gs(ht), gs(at)
        return np.array([
            h.form_last_5(), a.form_last_5(),
            h.avg_goals_for()/5, a.avg_goals_for()/5,
            h.avg_goals_against()/5, a.avg_goals_against()/5,
            h.win_rate(), a.win_rate(),
            h.elo/2000, a.elo/2000,
            (h.elo - a.elo)/400, 1.0
        ])

    X, y = [], []
    for _, row in df.iterrows():
        X.append(features(row["HomeTeam"], row["AwayTeam"]))
        y.append(0 if row["FTR"]=="H" else 1 if row["FTR"]=="D" else 2)
        update_team_stats(gs(row["HomeTeam"]), gs(row["AwayTeam"]),
                          int(row["FTHG"]), int(row["FTAG"]), row["FTR"])

    X, y = np.array(X), np.array(y)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = CustomDecisionTree()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = np.sum(preds == y_test) / len(y_test)
    print(f"Decision Tree accuracy: {acc*100:.2f}%")
    return y_test, preds, acc


# ════════════════════════════════════════════════════════════════════════════
# NAIVE BAYES
# ════════════════════════════════════════════════════════════════════════════
def run_naive_bayes():
    df = pd.read_csv(csv_path, usecols=["HomeTeam","AwayTeam","FTHG","FTAG","FTR"])

    home_stats = df.groupby("HomeTeam").agg({"FTHG":"mean","FTAG":"mean"}).rename(
        columns={"FTHG":"Scored","FTAG":"Conceded"})
    away_stats = df.groupby("AwayTeam").agg({"FTAG":"mean","FTHG":"mean"}).rename(
        columns={"FTAG":"Scored","FTHG":"Conceded"})

    df["HomeAttack"]  = pd.qcut(df["HomeTeam"].map(home_stats["Scored"]),
                                 q=3, labels=["Weak","Average","Strong"], duplicates="drop")
    df["AwayAttack"]  = pd.qcut(df["AwayTeam"].map(away_stats["Scored"]),
                                 q=3, labels=["Weak","Average","Strong"], duplicates="drop")
    df["HomeDefense"] = pd.qcut(df["HomeTeam"].map(home_stats["Conceded"]),
                                 q=3, labels=["Strong","Average","Weak"], duplicates="drop")
    df["AwayDefense"] = pd.qcut(df["AwayTeam"].map(away_stats["Conceded"]),
                                 q=3, labels=["Strong","Average","Weak"], duplicates="drop")

    X = df[["HomeTeam","AwayTeam","HomeAttack","HomeDefense","AwayAttack","AwayDefense"]]
    y = df["FTR"]

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    classes = np.unique(y_train)
    priors = {}
    feat_probs = {}
    for c in classes:
        mask = y_train == c
        priors[c] = mask.sum() / len(y_train)
        feat_probs[c] = {}
        for col in X_train.columns:
            vc = X_train[mask][col].value_counts()
            total_c = mask.sum()
            uniq = np.unique(X_train[col])
            feat_probs[c][col] = {v: (vc.get(v,0)+1)/(total_c+len(uniq)) for v in uniq}

    def predict_nb(X_df):
        preds = []
        for _, row in X_df.iterrows():
            best, bprob = None, -1
            for c in classes:
                p = priors[c]
                for col in X_df.columns:
                    p *= feat_probs[c][col].get(row[col], 1e-6)
                if p > bprob: bprob = p; best = c
            preds.append(best)
        return np.array(preds)

    preds = predict_nb(X_test)
    acc = np.sum(preds == y_test.values) / len(y_test)
    print(f"Naive Bayes accuracy: {acc*100:.2f}%")
    return y_test.values, preds, acc


# ════════════════════════════════════════════════════════════════════════════
# GENEROWANIE WYKRESÓW
# ════════════════════════════════════════════════════════════════════════════
def confusion_matrix_data(y_true, y_pred, labels):
    cm = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in labels and p in labels:
            cm[labels.index(t)][labels.index(p)] += 1
    return cm


def plot_confusion_matrix(ax, cm, labels, title, cmap):
    sns.heatmap(cm, annot=True, fmt="d", cmap=cmap, ax=ax,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, linecolor="white",
                annot_kws={"size": 13, "weight": "bold"})
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Przewidywany", fontsize=11)
    ax.set_ylabel("Rzeczywisty", fontsize=11)
    ax.tick_params(labelsize=10)


def generate_all_plots():
    sns.set_theme(style="whitegrid", palette="muted")

    print("Trenowanie Decision Tree...")
    dt_true, dt_pred, dt_acc = run_decision_tree()

    print("Trenowanie Naive Bayes...")
    nb_true, nb_pred, nb_acc = run_naive_bayes()

    labels_int = [0, 1, 2]
    labels_str = ["H", "D", "A"]
    label_names = ["H (Gosp.)", "D (Remis)", "A (Gość)"]

    # ── 1. Confusion matrices obok siebie ───────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Macierze konfuzji – porównanie modeli", fontsize=15, fontweight="bold", y=1.02)

    cm_dt = confusion_matrix_data(dt_true.tolist(), dt_pred.tolist(), labels_int)
    cm_nb_raw = confusion_matrix_data(nb_true.tolist(), nb_pred.tolist(), labels_str)

    plot_confusion_matrix(axes[0], cm_dt, label_names,
                          f"Decision Tree  (acc = {dt_acc*100:.1f}%)", "Greens")
    plot_confusion_matrix(axes[1], cm_nb_raw, label_names,
                          f"Naive Bayes  (acc = {nb_acc*100:.1f}%)", "Blues")

    plt.tight_layout()
    path1 = os.path.join(output_dir, "confusion_matrices.png")
    plt.savefig(path1, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Zapisano: {path1}")

    # ── 2. Porównanie accuracy – bar chart ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(6, 5))
    models = ["Decision Tree", "Naive Bayes"]
    accs   = [dt_acc * 100, nb_acc * 100]
    colors = ["#2ecc71", "#3498db"]
    bars = ax.bar(models, accs, color=colors, width=0.45, edgecolor="white", linewidth=1.5)

    # linia baseline
    ax.axhline(y=46, color="gray", linestyle="--", linewidth=1.2, label="Baseline (zawsze H) ~46%")
    ax.axhline(y=33, color="salmon", linestyle="--", linewidth=1.2, label="Losowe zgadywanie ~33%")

    for bar, val in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=13, fontweight="bold")

    ax.set_ylim(0, max(accs) + 10)
    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_title("Porównanie dokładności modeli", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    ax.tick_params(labelsize=11)
    sns.despine()

    plt.tight_layout()
    path2 = os.path.join(output_dir, "accuracy_comparison.png")
    plt.savefig(path2, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Zapisano: {path2}")

    # ── 3. Rozkład predykcji – czy model jest bias? ─────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Rozkład predykcji – czy model faworyzuje jedną klasę?",
                 fontsize=14, fontweight="bold")

    def pred_dist(preds, label_list):
        vals, cnts = np.unique(preds, return_counts=True)
        d = {l: 0 for l in label_list}
        for v, c in zip(vals, cnts): d[v] = c
        return d

    dt_dist = pred_dist(dt_pred, labels_int)
    nb_dist = pred_dist(nb_pred, labels_str)

    # Decision Tree
    axes[0].bar(label_names, [dt_dist[k] for k in labels_int],
                color=["#2ecc71","#f1c40f","#e74c3c"], edgecolor="white", linewidth=1.2)
    axes[0].set_title("Decision Tree", fontsize=13, fontweight="bold")
    axes[0].set_ylabel("Liczba predykcji", fontsize=11)
    axes[0].tick_params(labelsize=10)

    # Naive Bayes
    axes[1].bar(label_names, [nb_dist.get(k, 0) for k in labels_str],
                color=["#3498db","#9b59b6","#e67e22"], edgecolor="white", linewidth=1.2)
    axes[1].set_title("Naive Bayes", fontsize=13, fontweight="bold")
    axes[1].set_ylabel("Liczba predykcji", fontsize=11)
    axes[1].tick_params(labelsize=10)

    plt.tight_layout()
    path3 = os.path.join(output_dir, "prediction_distribution.png")
    plt.savefig(path3, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Zapisano: {path3}")

    print("\nWszystkie wykresy wygenerowane!")
    print(f"  {path1}")
    print(f"  {path2}")
    print(f"  {path3}")


if __name__ == "__main__":
    generate_all_plots()