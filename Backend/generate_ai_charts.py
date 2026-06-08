import os
import numpy as np
import matplotlib.pyplot as plt

from model_comparison import train_ai_model
from random_forest_model import RandomForestMatchModel, train_test_split


current_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(current_dir, "..", "presentation_charts")

os.makedirs(output_dir, exist_ok=True)


def save_model_accuracy_chart():
    # Trenujemy wszystkie modele i pobieramy ich metryki
    manager = train_ai_model()
    metrics = manager.get_model_metrics()

    model_names = []
    accuracies = []

    for model in metrics["models"]:
        model_names.append(model["name"])
        accuracies.append(model["accuracy"] * 100)

    plt.figure(figsize=(8, 5))
    plt.bar(model_names, accuracies)
    plt.title("Porównanie accuracy modeli AI")
    plt.xlabel("Model")
    plt.ylabel("Accuracy [%]")
    plt.ylim(0, 100)

    for index, value in enumerate(accuracies):
        plt.text(index, value + 1, f"{value:.2f}%", ha="center")

    path = os.path.join(output_dir, "model_accuracy.png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    print(f"Zapisano: {path}")


def build_confusion_matrix(y_true, y_pred):
    # Klasy:
    # 1 = HOME_WIN
    # 0 = AWAY_WIN
    matrix = np.zeros((2, 2), dtype=int)

    for true, pred in zip(y_true, y_pred):
        if true == 1 and pred == 1:
            matrix[0][0] += 1  # HOME predicted as HOME
        elif true == 1 and pred == 0:
            matrix[0][1] += 1  # HOME predicted as AWAY
        elif true == 0 and pred == 1:
            matrix[1][0] += 1  # AWAY predicted as HOME
        elif true == 0 and pred == 0:
            matrix[1][1] += 1  # AWAY predicted as AWAY

    return matrix


def save_random_forest_confusion_matrix():
    # Osobno trenujemy Random Forest, żeby uzyskać predykcje na zbiorze testowym
    model = RandomForestMatchModel()

    X, y = model.prepare_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model.model.fit(X_train, y_train)
    predictions = model.model.predict(X_test)

    matrix = build_confusion_matrix(y_test, predictions)

    labels = ["HOME_WIN", "AWAY_WIN"]

    plt.figure(figsize=(6, 5))
    plt.imshow(matrix)
    plt.title("Confusion Matrix — Random Forest")
    plt.xlabel("Predicted class")
    plt.ylabel("True class")

    plt.xticks([0, 1], labels)
    plt.yticks([0, 1], labels)

    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(matrix[i][j]), ha="center", va="center")

    plt.colorbar()

    path = os.path.join(output_dir, "random_forest_confusion_matrix.png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    print(f"Zapisano: {path}")


def save_feature_correlation_heatmap():
    model = RandomForestMatchModel()

    X, y = model.prepare_training_data()

    feature_names = [
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

    # Korelacja cech wejściowych
    correlation_matrix = np.corrcoef(X, rowvar=False)

    plt.figure(figsize=(10, 8))
    plt.imshow(correlation_matrix)
    plt.title("Heatmap korelacji cech modelu")
    plt.colorbar()

    plt.xticks(range(len(feature_names)), feature_names, rotation=90)
    plt.yticks(range(len(feature_names)), feature_names)

    path = os.path.join(output_dir, "feature_correlation_heatmap.png")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()

    print(f"Zapisano: {path}")


def main():
    save_model_accuracy_chart()
    save_random_forest_confusion_matrix()
    save_feature_correlation_heatmap()


if __name__ == "__main__":
    main()