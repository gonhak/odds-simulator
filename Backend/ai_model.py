import pandas as pd
import numpy as np
import os

import matplotlib.pyplot as plt
import seaborn as sns

current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "..", "premier_league.csv")


def train_test_split(X, y, test_size=0.2):

    np.random.seed(42)

    # Mieszamy indeksy wierszy
    indices = np.random.permutation(len(X))
    test_size_count = int(len(X) * test_size)

    # Dzielimy indeksy
    test_idx = indices[:test_size_count]
    train_idx = indices[test_size_count:]

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

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

        h_profile = self.team_profiles.get(home_team, {})
        a_profile = self.team_profiles.get(away_team, {})

        h_attack = h_profile.get('HomeAttack', 'Average')
        h_defense = h_profile.get('HomeDefense', 'Average')
        a_attack = a_profile.get('AwayAttack', 'Average')
        a_defense = a_profile.get('AwayDefense', 'Average')

        for c in self.classes:
            prob = self.class_priors.get(c, 0.33)

            # OBLICZANIE WPLYWU CECH DLA GOSPODARZA
            prob *= self.feature_probs[c]['HomeTeam'].get(home_team, 1e-6)
            prob *= self.feature_probs[c]['HomeAttack'].get(h_attack, 1e-6)
            prob *= self.feature_probs[c]['HomeDefense'].get(h_defense, 1e-6)

            # OBLICZANIE WPLYWU CECH DLA GOSCIA
            prob *= self.feature_probs[c]['AwayTeam'].get(away_team, 1e-6)
            prob *= self.feature_probs[c]['AwayAttack'].get(a_attack, 1e-6)
            prob *= self.feature_probs[c]['AwayDefense'].get(a_defense, 1e-6)

            raw_probs[c] = prob
            total_prob += prob

        # suma do 1.0
        final_probs = {}
        if total_prob > 0:
            for c in self.classes:
                final_probs[c] = raw_probs[c] / total_prob

        return final_probs

    def get_model_metrics(self):
        return {
            "model": "Custom Naive Bayes (with Feature Engineering)",
            "accuracy": round(self.accuracy, 4),
            "features": [
                "HomeTeam", "AwayTeam",
                "HomeAttack", "HomeDefense",
                "AwayAttack", "AwayDefense"
            ]
        }


def show_presentation_plots(y, y_test, predictions):
    print("-> Generowanie wykresów do prezentacji...")

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # WYKRES ROZKLADU
    sns.countplot(x=y, order=['H', 'D', 'A'], hue=y, palette='viridis', legend=False, ax=axes[0])
    axes[0].set_title('Rozkład wyników meczów (Premier League)', fontsize=14)
    axes[0].set_ylabel('Liczba meczów')
    axes[0].set_xlabel('Wynik (H - Gospodarz, D - Remis, A - Gość)')

    # MACIERZ KONFUZJI
    classes = ['H', 'D', 'A']
    # Tworzymy mapę nazw dla etykiet wykresu, żeby były bardziej czytelne
    labels = ['H (Gosp)', 'D (Remis)', 'A (Gość)']

    cm = pd.crosstab(y_test, predictions, rownames=['Rzeczywisty'], colnames=['Przewidywany'])
    cm = cm.reindex(index=classes, columns=classes, fill_value=0)

    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[1],
                xticklabels=labels, yticklabels=labels)
    axes[1].set_title('Macierz konfuzji (Naiwny Bayes)', fontsize=14)

    plt.tight_layout()
    plt.show()


def train_ai_model(show_plots=False):
    print("1. Wczytywanie danych...")
    df = pd.read_csv(csv_path, usecols=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR'])

    # srednia straconych i strzelonych goli
    home_stats = df.groupby('HomeTeam').agg({'FTHG': 'mean', 'FTAG': 'mean'}).rename(
        columns={'FTHG': 'Scored', 'FTAG': 'Conceded'})
    away_stats = df.groupby('AwayTeam').agg({'FTAG': 'mean', 'FTHG': 'mean'}).rename(
        columns={'FTAG': 'Scored', 'FTHG': 'Conceded'})

    # koszykowanie (slaby, sredni i mocy)
    # Atak: im wiecej strzelonych tym lepiej
    df['HomeAttack'] = df['HomeTeam'].map(home_stats['Scored'])
    df['HomeAttack'] = pd.qcut(df['HomeAttack'], q=3, labels=['Weak', 'Average', 'Strong'], duplicates='drop')

    df['AwayAttack'] = df['AwayTeam'].map(away_stats['Scored'])
    df['AwayAttack'] = pd.qcut(df['AwayAttack'], q=3, labels=['Weak', 'Average', 'Strong'], duplicates='drop')

    # Obrona: im mniej straconych tym lepiej (odwrotna kolejnosc etykiet)
    df['HomeDefense'] = df['HomeTeam'].map(home_stats['Conceded'])
    df['HomeDefense'] = pd.qcut(df['HomeDefense'], q=3, labels=['Strong', 'Average', 'Weak'], duplicates='drop')

    df['AwayDefense'] = df['AwayTeam'].map(away_stats['Conceded'])
    df['AwayDefense'] = pd.qcut(df['AwayDefense'], q=3, labels=['Strong', 'Average', 'Weak'], duplicates='drop')

    X = df[['HomeTeam', 'AwayTeam', 'HomeAttack', 'HomeDefense', 'AwayAttack', 'AwayDefense']]
    y = df['FTR']

    print("2. Podzial na dane treningowe i testowe...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = CustomNaiveBayes()
    model.fit(X_train, y_train)

    team_names = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
    for team in team_names:
        team_data = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].iloc[0]
        model.team_profiles[team] = {
            'HomeAttack': team_data['HomeAttack'] if team == team_data['HomeTeam'] else 'Average',
            'HomeDefense': team_data['HomeDefense'] if team == team_data['HomeTeam'] else 'Average',
            'AwayAttack': team_data['AwayAttack'] if team == team_data['AwayTeam'] else 'Average',
            'AwayDefense': team_data['AwayDefense'] if team == team_data['AwayTeam'] else 'Average'
        }

    print("3. Testowanie modelu...")
    predictions = model.predict(X_test)


    # Accuracy
    correct = np.sum(predictions == y_test.values)
    accuracy = correct / len(y_test)
    model.accuracy = accuracy

    print(f"Naive Bayes accuracy: {accuracy * 100:.2f}%")

    if show_plots:
        show_presentation_plots(y, y_test, predictions)

    return model

if __name__ == "__main__":
    train_ai_model(show_plots=True)