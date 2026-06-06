import pandas as pd
import numpy as np
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "..", "premier_league.csv")


def train_test_split(X, y, test_size=0.2):

    np.random.seed()

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

        for c in self.classes:
            prob = self.class_priors.get(c, 0.33)

            # KURS GOSPODARZA
            if home_team in self.feature_probs[c].get('HomeTeam', {}):
                prob *= self.feature_probs[c]['HomeTeam'][home_team]
            else:
                prob *= 1e-6

            # KURS GOSCIA
            if away_team in self.feature_probs[c].get('AwayTeam', {}):
                prob *= self.feature_probs[c]['AwayTeam'][away_team]
            else:
                prob *= 1e-6

            raw_probs[c] = prob
            total_prob += prob

        # suma do 1.0
        final_probs = {}
        if total_prob > 0:
            for c in self.classes:
                final_probs[c] = raw_probs[c] / total_prob

        return final_probs

def train_ai_model():
    print("1. Wczytywanie danych...")
    df = pd.read_csv(csv_path, usecols=['HomeTeam', 'AwayTeam', 'FTR'])

    X = df[['HomeTeam', 'AwayTeam']]
    y = df['FTR']

    print("2. Podzial na dane treningowe i testowe...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = CustomNaiveBayes()
    model.fit(X_train, y_train)

    print("3. Testowanie modelu...")
    predictions = model.predict(X_test)

    # Accuracy
    correct = np.sum(predictions == y_test.values)
    accuracy = correct / len(y_test)

    print(f"{accuracy * 100:.2f}%")

    return model

if __name__ == "__main__":
    train_ai_model()