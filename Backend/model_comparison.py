from ai_model import train_ai_model as train_naive_bayes
from decision_tree_model import train_ai_model as train_decision_tree


class ModelComparisonManager:
    def __init__(self):
        self.models = []
        self.metrics = []
        self.best_model = None
        self.best_model_name = None

    def train_all_models(self):
        print("=== Trenowanie modeli AI ===")

        # 1. Naive Bayes
        print("\n--- Naive Bayes ---")
        naive_bayes = train_naive_bayes()
        naive_metrics = naive_bayes.get_model_metrics()

        self.models.append({
            "name": "Naive Bayes",
            "model": naive_bayes,
            "accuracy": naive_metrics["accuracy"],
            "metrics": naive_metrics
        })

        # 2. Decision Tree
        print("\n--- Decision Tree ---")
        decision_tree = train_decision_tree()
        decision_metrics = decision_tree.get_model_metrics()

        self.models.append({
            "name": "Decision Tree",
            "model": decision_tree,
            "accuracy": decision_metrics["accuracy"],
            "metrics": decision_metrics
        })

        # Wybór najlepszego modelu. Główne kryterium: accuracy, jeżeli accuracy jest bardzo podobna, wybieramy Decision Tree,ponieważ jest bardziej interpretowalny.  
        accuracy_tolerance = 0.001

        best_accuracy = max(item["accuracy"] for item in self.models)

        candidates = [
            item for item in self.models
            if abs(item["accuracy"] - best_accuracy) <= accuracy_tolerance
        ]

        decision_tree_candidate = next(
            (item for item in candidates if item["name"] == "Decision Tree"),
            None
        )

        if decision_tree_candidate is not None:
            best = decision_tree_candidate
        else:
            best = candidates[0]

        self.best_model = best["model"]
        self.best_model_name = best["name"]

        self.metrics = [
            {
                "name": item["name"],
                "accuracy": item["accuracy"],
                "details": item["metrics"]
            }
            for item in self.models
        ]

        print("\n=== Wyniki porównania modeli ===")
        for item in self.metrics:
            print(f"{item['name']}: {item['accuracy'] * 100:.2f}%")

        print(f"Najlepszy model: {self.best_model_name}")

    def get_match_probabilities(self, home_team, away_team):
        # Backend korzysta tylko z najlepszego wybranego modelu
        if self.best_model is None:
            return {
                "H": 0.33,
                "D": 0.33,
                "A": 0.33
            }

        return self.best_model.get_match_probabilities(home_team, away_team)

    def get_model_metrics(self):
        return {
            "best_model": self.best_model_name,
            "models": self.metrics
        }


def train_ai_model():
    manager = ModelComparisonManager()
    manager.train_all_models()
    return manager


if __name__ == "__main__":
    train_ai_model()