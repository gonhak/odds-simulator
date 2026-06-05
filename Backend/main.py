from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_model import train_ai_model

app = FastAPI()


# uczymy ai zaraz po wlaczeniu serwera
ai_brain = train_ai_model()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationConfig(BaseModel):
    gospodarze: str
    goscie: str
    czas_trwania: int
    ilosc_graczy: int

isSimulationRunning = False

@app.post("/api/start")
def start_simulation(config: SimulationConfig):
    global isSimulationRunning
    isSimulationRunning = True
    print("simulation start...")

    # wynik AI
    chances = ai_brain.get_match_probabilities(config.gospodarze, config.goscie)
    chances_home = chances.get('H', 0.33)
    chances_away = chances.get('A', 0.33)

    # zamiana na kursy
    odds_home = round(1 / chances_home, 2)
    odds_away = round(1 / chances_away, 2)

    print(f"Mecz: {config.gospodarze} vs {config.goscie}")
    print(f"Czas: {config.czas_trwania} vs {config.ilosc_graczy}")
    print(f"AI gospodarze: {odds_home} goscie: {odds_away}")

    return {"status": "ok","message": "simulation started", "initial_odds" : {"home" : odds_home , "away" : odds_away}}

@app.post("/api/stop")
def stop_simulation():
    global isSimulationRunning
    isSimulationRunning = False
    print("simulation stop...")

    return {"status": "ok", "message": "simulation stopped"}


@app.get("/api/status")
def get_status():
    # endpoint co sekunde

    if not isSimulationRunning:
        return {"status": "waiting"}

    return {
        "status": "in progress",
        "kursy": {
            "gospodarze": 1.88,
            "goscie": 3.45
        },
        "bets": {
            "gospodarze_proc": 65,
            "goscie_proc": 35
        },
        "ai accuracy": 82,
        "last transactions": [
            {"gracz": "Player_1", "id": "#1001", "pozycja": "Gospodarze", "stawka": 50, "zwrot": 94},
            {"gracz": "Player_2", "id": "#1002", "pozycja": "Goście", "stawka": 100, "zwrot": 345}
        ]
    }