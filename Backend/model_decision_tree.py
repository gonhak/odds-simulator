import os
from collections import deque

import numpy as np
import pandas as pd


current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "..", "premier_league.csv")


def train_test_split(X, y, test_size=0.2):
    split_idx = int(len(X) * (1 - test_size))

    X_train = X[:split_idx]
    X_test = X[split_idx:]

    y_train = y[:split_idx]
    y_test = y[split_idx:]

    return X_train, X_test, y_train, y_test


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
        # Forma z ostatnich 5 meczów w zakresie 0-1
        if len(self.last_points) == 0:
            return 0.5

        return sum(self.last_points) / (len(self.last_points) * 3)

    def avg_goals_for(self):
        if len(self.last_goals_for) == 0:
            return 1.2

        return sum(self.last_goals_for) / len(self.last_goals_for)

    def avg_goals_against(self):
        if len(self.last_goals_against) == 0:
            return 1.2

        return sum(self.last_goals_against) / len(self.last_goals_against)

    def win_rate(self):
        if self.matches_played == 0:
            return 0.5

        return self.wins / self.matches_played


def expected_score(elo_a, elo_b):
    # Klasyczny wzór Elo
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(home_stats, away_stats, result):
    # Aktualizacja Elo po meczu
    k = 24

    home_expected = expected_score(home_stats.elo + 60, away_stats.elo)
    away_expected = 1 - home_expected

    if result == "H":
        home_score = 1.0
        away_score = 0.0
    elif result == "A":
        home_score = 0.0
        away_score = 1.0
    else:
        home_score = 0.5
        away_score = 0.5

    home_stats.elo += k * (home_score - home_expected)
    away_stats.elo += k * (away_score - away_expected)


def update_team_stats(home_stats, away_stats, home_goals, away_goals, result):
    # Aktualizacja statystyk drużyn po zakończonym meczu
    home_stats.matches_played += 1
    away_stats.matches_played += 1

    if result == "H":
        home_stats.wins += 1
        away_stats.losses += 1

        home_points = 3
        away_points = 0

    elif result == "A":
        home_stats.losses += 1
        away_stats.wins += 1

        home_points = 0
        away_points = 3

    else:
        home_stats.draws += 1
        away_stats.draws += 1

        home_points = 1
        away_points = 1

    home_stats.last_points.append(home_points)
    away_stats.last_points.append(away_points)

    home_stats.last_goals_for.append(home_goals)
    home_stats.last_goals_against.append(away_goals)

    away_stats.last_goals_for.append(away_goals)
    away_stats.last_goals_against.append(home_goals)

    update_elo(home_stats, away_stats, result)


class DecisionTreeNode:
    def __init__(
        self,
        feature_index=None,
        threshold=None,
        left=None,
        right=None,
        value=None,
        class_probs=None
    ):
        self.feature_index = feature_index
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value
        self.class_probs = class_probs


class CustomDecisionTree:
    def __init__(self, max_depth=6, min_samples_split=4, min_samples_leaf=2):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.root = None

    def gini(self, y):
        # Indeks Giniego dla podziału klas
        if len(y) == 0:
            return 0

        classes, counts = np.unique(y, return_counts=True)
        probabilities = counts / len(y)

        return 1 - np.sum(probabilities ** 2)

    def majority_class(self, y):
        # Najczęściej występująca klasa w danym węźle
        classes, counts = np.unique(y, return_counts=True)
        return classes[np.argmax(counts)]

    def class_distribution(self, y):
        # Rozkład klas w liściu drzewa
        # 0 = H, 1 = D, 2 = A
        counts = np.bincount(y, minlength=3)

        # Wygładzanie Laplace'a, żeby uniknąć prawdopodobieństwa 0
        counts = counts + 1

        probabilities = counts / np.sum(counts)

        return probabilities

    def find_thresholds(self, values):
        # Wybieramy kilka progów zamiast testować każdą możliwą wartość
        unique_values = np.unique(values)

        if len(unique_values) <= 10:
            return unique_values

        return np.percentile(
            unique_values,
            [10, 20, 30, 40, 50, 60, 70, 80, 90]
        )

    def best_split(self, X, y):
        best_feature = None
        best_threshold = None
        best_score = float("inf")

        n_samples, n_features = X.shape

        for feature_index in range(n_features):
            thresholds = self.find_thresholds(X[:, feature_index])

            for threshold in thresholds:
                left_mask = X[:, feature_index] <= threshold
                right_mask = X[:, feature_index] > threshold

                y_left = y[left_mask]
                y_right = y[right_mask]

                if len(y_left) < self.min_samples_leaf:
                    continue

                if len(y_right) < self.min_samples_leaf:
                    continue

                weighted_gini = (
                    len(y_left) / n_samples * self.gini(y_left)
                    + len(y_right) / n_samples * self.gini(y_right)
                )

                if weighted_gini < best_score:
                    best_score = weighted_gini
                    best_feature = feature_index
                    best_threshold = threshold

        return best_feature, best_threshold

    def build_tree(self, X, y, depth):
        # Warunki zatrzymania drzewa
        if (
            depth >= self.max_depth
            or len(y) < self.min_samples_split
            or len(np.unique(y)) == 1
        ):
            return DecisionTreeNode(
                value=self.majority_class(y),
                class_probs=self.class_distribution(y)
            )

        feature_index, threshold = self.best_split(X, y)

        if feature_index is None:
            return DecisionTreeNode(
                value=self.majority_class(y),
                class_probs=self.class_distribution(y)
            )

        left_mask = X[:, feature_index] <= threshold
        right_mask = X[:, feature_index] > threshold

        left_node = self.build_tree(X[left_mask], y[left_mask], depth + 1)
        right_node = self.build_tree(X[right_mask], y[right_mask], depth + 1)

        return DecisionTreeNode(
            feature_index=feature_index,
            threshold=threshold,
            left=left_node,
            right=right_node
        )

    def fit(self, X, y):
        self.root = self.build_tree(X, y, 0)

    def predict_one(self, x, node):
        if node.left is None and node.right is None:
            return node.value
        if x[node.feature_index] <= node.threshold:
            return self.predict_one(x, node.left)
        return self.predict_one(x, node.right)

    def predict(self, X):
        return np.array([self.predict_one(x, self.root) for x in X])

    def predict_proba_one(self, x, node=None):
        # Zwracamy prawdopodobieństwa na podstawie rozkładu klas w liściu
        if node is None:
            node = self.root

        if node.value is not None:
            probabilities = node.class_probs

            return {
                "H": float(probabilities[0]),
                "D": float(probabilities[1]),
                "A": float(probabilities[2])
            }

        if x[node.feature_index] <= node.threshold:
            return self.predict_proba_one(x, node.left)

        return self.predict_proba_one(x, node.right)


class DecisionTreeMatchModel:
    def __init__(self):
        self.model = CustomDecisionTree(
            max_depth=6,
            min_samples_split=4,
            min_samples_leaf=2
        )

        self.team_stats = {}
        self.accuracy = 0.0

    def get_stats(self, team):
        if team not in self.team_stats:
            self.team_stats[team] = TeamStats()

        return self.team_stats[team]

    def create_features_from_stats(self, home_team, away_team):
        home_stats = self.get_stats(home_team)
        away_stats = self.get_stats(away_team)

        features = [
            home_stats.form_last_5(),
            away_stats.form_last_5(),

            home_stats.avg_goals_for() / 5,
            away_stats.avg_goals_for() / 5,

            home_stats.avg_goals_against() / 5,
            away_stats.avg_goals_against() / 5,

            home_stats.win_rate(),
            away_stats.win_rate(),

            home_stats.elo / 2000,
            away_stats.elo / 2000,

            (home_stats.elo - away_stats.elo) / 400,

            1.0  # przewaga własnego boiska
        ]

        return np.array(features)

    def prepare_training_data(self):
        print("1. Wczytywanie danych do Decision Tree...")

        df = pd.read_csv(
            csv_path,
            usecols=["HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
        )

        X = []
        y = []

        for _, row in df.iterrows():
            home_team = row["HomeTeam"]
            away_team = row["AwayTeam"]

            home_goals = int(row["FTHG"])
            away_goals = int(row["FTAG"])
            result = row["FTR"]

            # Tworzymy cechy przed aktualizacją statystyk aktualnym meczem
            features = self.create_features_from_stats(home_team, away_team)

            # Model uczy się trzech klas: H, D, A
            X.append(features)

            if result == "H":
                y.append(0)
            elif result == "D":
                y.append(1)
            else:
                y.append(2)

            # Po utworzeniu próbki aktualizujemy historię drużyn
            update_team_stats(
                self.get_stats(home_team),
                self.get_stats(away_team),
                home_goals,
                away_goals,
                result
            )

        return np.array(X), np.array(y)

    def fit(self):
        self.team_stats = {}
        X, y = self.prepare_training_data()

        print("2. Podział danych na train/test...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

        print("3. Trenowanie Decision Tree...")
        self.model.fit(X_train, y_train)

        print("4. Testowanie Decision Tree...")
        predictions = self.model.predict(X_test)
        
        print("Tree true classes:", np.unique(y_test, return_counts=True))
        print("Tree predicted classes:", np.unique(predictions, return_counts=True))

        correct = np.sum(predictions == y_test)
        self.accuracy = correct / len(y_test)

        print(f"Decision Tree accuracy: {self.accuracy * 100:.2f}%")

    def get_match_probabilities(self, home_team, away_team):
        features = self.create_features_from_stats(home_team, away_team)
        return self.model.predict_proba_one(features)

    def get_model_metrics(self):
        return {
            "model": "Custom Decision Tree",
            "accuracy": round(self.accuracy, 4),
            "max_depth": self.model.max_depth,
            "min_samples_split": self.model.min_samples_split,
            "min_samples_leaf": self.model.min_samples_leaf,
            "features": [
                "home_form_last_5",
                "away_form_last_5",
                "home_avg_goals_for",
                "away_avg_goals_for",
                "home_avg_goals_against",
                "away_avg_goals_against",
                "home_win_rate",
                "away_win_rate",
                "home_elo",
                "away_elo",
                "elo_difference",
                "home_advantage"
            ]
        }


def train_ai_model():
    model = DecisionTreeMatchModel()
    model.fit()
    return model


if __name__ == "__main__":
    train_ai_model()