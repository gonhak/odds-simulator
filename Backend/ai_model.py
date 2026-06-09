import os
from operator import truediv

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RANDOM_SEED = 83
np.random.seed(RANDOM_SEED)

current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "..", "premier_league.csv")


def train_test_split(X, y, test_size=0.2):
    split_idx = int(len(X) * (1 - test_size))

    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]

    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    return X_train, X_test, y_train, y_test


class CustomNaiveBayes:
    def __init__(self):
        self.class_priors = {}
        self.feature_probs = {}
        self.classes = []
        self.accuracy = 0.0
        self.team_profiles = {}

    def fit(self, X, y):
        self.classes = np.unique(y)
        total_samples = len(y)

        for c in self.classes:
            c_mask = (y == c)
            self.class_priors[c] = np.sum(c_mask) / total_samples

            self.feature_probs[c] = {}
            for col in X.columns:
                self.feature_probs[c][col] = {}
                val_counts = X[c_mask][col].value_counts()
                total_c = np.sum(c_mask)
                unique_vals = np.unique(X[col])

                for val in unique_vals:
                    count = val_counts.get(val, 0)
                    # Wygładzanie Laplace'a
                    self.feature_probs[c][col][val] = (count + 1) / (total_c + len(unique_vals))

    def predict(self, X):
        predictions = []
        for _, row in X.iterrows():
            best_class = None
            max_prob = -1

            for c in self.classes:
                prob = self.class_priors[c]

                for col in X.columns:
                    val = row[col]
                    if val in self.feature_probs[c][col]:
                        prob *= self.feature_probs[c][col][val]
                    else:
                        prob *= 1e-6

                if prob > max_prob:
                    max_prob = prob
                    best_class = c

            predictions.append(best_class)
        return np.array(predictions)

    def get_match_probabilities(self, home_team, away_team):
        raw_probs = {}
        total_prob = 0

        # Bezpieczne pobieranie profili z fallbackiem do 'Average'
        h_profile = self.team_profiles.get(home_team, {"HomeAttack": "Average", "HomeDefense": "Average"})
        a_profile = self.team_profiles.get(away_team, {"AwayAttack": "Average", "AwayDefense": "Average"})

        h_attack = h_profile.get('HomeAttack', 'Average')
        h_defense = h_profile.get('HomeDefense', 'Average')
        a_attack = a_profile.get('AwayAttack', 'Average')
        a_defense = a_profile.get('AwayDefense', 'Average')

        for c in self.classes:
            prob = self.class_priors.get(c, 0.33)

            prob *= self.feature_probs[c]['HomeTeam'].get(home_team, 1e-6)
            prob *= self.feature_probs[c]['HomeAttack'].get(h_attack, 1e-6)
            prob *= self.feature_probs[c]['HomeDefense'].get(h_defense, 1e-6)

            prob *= self.feature_probs[c]['AwayTeam'].get(away_team, 1e-6)
            prob *= self.feature_probs[c]['AwayAttack'].get(a_attack, 1e-6)
            prob *= self.feature_probs[c]['AwayDefense'].get(a_defense, 1e-6)

            raw_probs[c] = prob
            total_prob += prob

        final_probs = {}
        if total_prob > 0:
            for c in self.classes:
                final_probs[c] = raw_probs[c] / total_prob
        else:
            final_probs = {"H": 0.33, "D": 0.33, "A": 0.33}

        return final_probs


def show_presentation_plots(y, y_test, predictions):
    print("-> Generowanie wykresów do prezentacji...")
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    sns.countplot(x=y, order=['H', 'D', 'A'], hue=y, palette='viridis', legend=False, ax=axes[0])
    axes[0].set_title('Rozkład wyników meczów (Premier League)', fontsize=14)
    axes[0].set_ylabel('Liczba meczów')
    axes[0].set_xlabel('Wynik')

    classes = ['H', 'D', 'A']
    labels = ['H (Gosp)', 'D (Remis)', 'A (Gość)']

    cm = pd.crosstab(y_test, predictions, rownames=['Rzeczywisty'], colnames=['Przewidywany'])
    cm = cm.reindex(index=classes, columns=classes, fill_value=0)

    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[1], xticklabels=labels, yticklabels=labels)
    axes[1].set_title('Macierz konfuzji (Naiwny Bayes)', fontsize=14)

    plt.tight_layout()
    plt.show()


def train_ai_model(show_plots=False):
    print("1. Wczytywanie danych...")
    df = pd.read_csv(csv_path, usecols=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR'])

    # Słownik przechowujący sumaryczną historię drużyn do liczenia średniej kroczącej
    # Zapobiega wyciekowi danych (Data Leakage)
    running_stats = {}

    def get_init_stats():
        return {"H_scored": 0, "H_conceded": 0, "H_matches": 0,
                "A_scored": 0, "A_conceded": 0, "A_matches": 0}

    # Przygotowujemy listy na nowe, dynamiczne cechy
    home_attacks, home_defenses = [], []
    away_attacks, away_defenses = [], []

    print("2. Dynamiczne wyliczanie statystyk historycznych (Brak Data Leakage)...")
    for _, row in df.iterrows():
        h_team = row['HomeTeam']
        a_team = row['AwayTeam']

        if h_team not in running_stats: running_stats[h_team] = get_init_stats()
        if a_team not in running_stats: running_stats[a_team] = get_init_stats()

        # Pobieramy średnie ZANIM dopiszemy wynik bieżącego meczu
        h_stat = running_stats[h_team]
        a_stat = running_stats[a_team]

        h_avg_scored = h_stat["H_scored"] / h_stat["H_matches"] if h_stat["H_matches"] > 0 else 1.2
        h_avg_conceded = h_stat["H_conceded"] / h_stat["H_matches"] if h_stat["H_matches"] > 0 else 1.2

        a_avg_scored = a_stat["A_scored"] / a_stat["A_matches"] if a_stat["A_matches"] > 0 else 1.2
        a_avg_conceded = a_stat["A_conceded"] / a_stat["A_matches"] if a_stat["A_matches"] > 0 else 1.2

        home_attacks.append(h_avg_scored)
        home_defenses.append(h_avg_conceded)
        away_attacks.append(a_avg_scored)
        away_defenses.append(a_avg_conceded)

        # Aktualizacja statystyk PO pobraniu cech na ten mecz
        running_stats[h_team]["H_scored"] += int(row['FTHG'])
        running_stats[h_team]["H_conceded"] += int(row['FTAG'])
        running_stats[h_team]["H_matches"] += 1

        running_stats[a_team]["A_scored"] += int(row['FTAG'])
        running_stats[a_team]["A_conceded"] += int(row['FTHG'])
        running_stats[a_team]["A_matches"] += 1

    # Przypisujemy wyliczone, bezpieczne ciągłe wartości do DataFrame
    df['HomeAttack_Raw'] = home_attacks
    df['HomeDefense_Raw'] = home_defenses
    df['AwayAttack_Raw'] = away_attacks
    df['AwayDefense_Raw'] = away_defenses

    # Dyskretyzacja (koszykowanie) na podstawie rozkładu historycznego
    df['HomeAttack'] = pd.qcut(df['HomeAttack_Raw'], q=3, labels=['Weak', 'Average', 'Strong'], duplicates='drop')
    df['AwayAttack'] = pd.qcut(df['AwayAttack_Raw'], q=3, labels=['Weak', 'Average', 'Strong'], duplicates='drop')
    df['HomeDefense'] = pd.qcut(df['HomeDefense_Raw'], q=3, labels=['Strong', 'Average', 'Weak'], duplicates='drop')
    df['AwayDefense'] = pd.qcut(df['AwayDefense_Raw'], q=3, labels=['Strong', 'Average', 'Weak'], duplicates='drop')

    X = df[['HomeTeam', 'AwayTeam', 'HomeAttack', 'HomeDefense', 'AwayAttack', 'AwayDefense']]
    y = df['FTR']

    print("3. Podzial na dane treningowe i testowe...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = CustomNaiveBayes()
    model.fit(X_train, y_train)

    # Budowanie OSTATECZNYCH profili drużyn (bierzemy ostatni znany stan z końca zbioru)
    print("4. Budowanie profili końcowych drużyn do przyszłych predykcji...")
    for team in running_stats.keys():
        # Szukamy ostatniego meczu domowego i wyjazdowego tej drużyny
        last_home_match = df[df['HomeTeam'] == team]
        last_away_match = df[df['AwayTeam'] == team]

        h_att = last_home_match['HomeAttack'].iloc[-1] if not last_home_match.empty else 'Average'
        h_def = last_home_match['HomeDefense'].iloc[-1] if not last_home_match.empty else 'Average'
        a_att = last_away_match['AwayAttack'].iloc[-1] if not last_away_match.empty else 'Average'
        a_def = last_away_match['AwayDefense'].iloc[-1] if not last_away_match.empty else 'Average'

        model.team_profiles[team] = {
            'HomeAttack': h_att,
            'HomeDefense': h_def,
            'AwayAttack': a_att,
            'AwayDefense': a_def
        }

    print("5. Testowanie modelu...")
    predictions = model.predict(X_test)

    print("Bayes true classes:", np.unique(y_test.values, return_counts=True))
    print("Bayes predicted classes:", np.unique(predictions, return_counts=True))

    accuracy = np.sum(predictions == y_test.values) / len(y_test)
    model.accuracy = accuracy

    print(f"Naive Bayes accuracy: {accuracy * 100:.2f}%")

    if show_plots:
        show_presentation_plots(y, y_test, predictions)

    return model


if __name__ == "__main__":
    train_ai_model(show_plots=True)