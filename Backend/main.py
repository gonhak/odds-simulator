from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import get_connection

#from random_forest_model import train_ai_model
#from ai_model import train_ai_model
from decision_tree_model import train_ai_model
#from model_comparison import train_ai_model

import random
import uuid

app = FastAPI()

TEAM_NAME_MAP = {
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Nottingham Forest": "Nott'm Forest"
}

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
current_simulation_id = None

current_sim_state = {
    "home_team": "",
    "away_team": "",
    "home_odd": 0.0,
    "away_odd": 0.0,
    "pool_home": 0.0,
    "pool_away": 0.0
}

def get_team_id_by_name(cursor, team_name):
    cursor.execute("""
        SELECT id
        FROM teams
        WHERE name = %s
    """, (
        team_name,
    ))

    team = cursor.fetchone()
    return team["id"] if team else None

def get_or_create_matchup(cursor, home_team_id, away_team_id):
    cursor.execute("""
        SELECT id
        FROM matchups
        WHERE home_team_id = %s
          AND away_team_id = %s
    """, (
        home_team_id,
        away_team_id
    ))

    matchup = cursor.fetchone()

    if matchup:
        return matchup["id"]

    cursor.execute("""
        INSERT INTO matchups (
            home_team_id,
            away_team_id
        )
        VALUES (%s, %s)
    """, (
        home_team_id,
        away_team_id
    ))

    return cursor.lastrowid

@app.post("/api/start")
def start_simulation(config: SimulationConfig):
    
    global current_simulation_id
    global isSimulationRunning

    
    home_for_model = TEAM_NAME_MAP.get(config.gospodarze, config.gospodarze)
    away_for_model = TEAM_NAME_MAP.get(config.goscie, config.goscie)
    chances = ai_brain.get_match_probabilities(home_for_model, away_for_model)
    
    print("simulation start...")
    
    # Model zwraca H, D, A, ale frontend obsługuje tylko kursy dla gospodarzy i gości. Dlatego bierzemy tylko H i A, a następnie normalizujemy je do dwóch wyników.
    chances_h = float(chances.get("H", 0.33))
    chances_a = float(chances.get("A", 0.33))

    # Сглаживание — смешиваем с равномерным распределением
    alpha = 0.25
    chances_home = alpha * 0.33 + (1 - alpha) * chances_h
    chances_away = alpha * 0.33 + (1 - alpha) * chances_a

    print(f"Команды: {config.gospodarze} vs {config.goscie}")
    print(f"Вероятности модели: {chances}")     
    
    # Normalizacja H/A, ponieważ nie obsługujemy remisu
    total = chances_home + chances_away

    if total <= 0:
        chances_home = 0.5
        chances_away = 0.5
    else:
        chances_home = chances_home / total
        chances_away = chances_away / total

    # Ograniczenie skrajnych prawdopodobieństw,
    # żeby Random Forest nie generował absurdalnych kursów typu 1.00 / 40.00
    min_probability = 0.06
    max_probability = 0.94

    chances_home = max(min_probability, min(max_probability, chances_home))
    chances_away = max(min_probability, min(max_probability, chances_away))

    # Ponowna normalizacja po ograniczeniu
    total = chances_home + chances_away
    chances_home = chances_home / total
    chances_away = chances_away / total

    # Marża bukmachera
    margin = 0.95

    # Zamiana prawdopodobieństw na kursy
    odds_home = round(margin / chances_home, 2)
    odds_away = round(margin / chances_away, 2)

    # Ograniczenie kursów do zakresu użytecznego dla symulacji
    odds_home = max(1.01, min(20.00, odds_home))
    odds_away = max(1.01, min(20.00, odds_away))

    print(f"Mecz: {config.gospodarze} vs {config.goscie}")
    print(f"AI gospodarze: {odds_home}, goscie: {odds_away}")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Pobieramy id drużyn z tabeli teams
        home_team_id = get_team_id_by_name(cursor, config.gospodarze)
        away_team_id = get_team_id_by_name(cursor, config.goscie)

        if home_team_id is None:
            return {
                "status": "error",
                "message": f"Nie znaleziono drużyny gospodarzy w bazie: {config.gospodarze}"
            }

        if away_team_id is None:
            return {
                "status": "error",
                "message": f"Nie znaleziono drużyny gości w bazie: {config.goscie}"
            }
            
        matchup_id = get_or_create_matchup(
            cursor,
            home_team_id,
            away_team_id
        )
        # Tworzymy nowa symulację
        cursor.execute("""
            INSERT INTO simulations (
                matchup_id,
                base_home_probability,
                base_away_probability,
                status
            )
            VALUES (%s, %s, %s, 'RUNNING')
        """, (
            matchup_id,
            round(chances_home, 6),
            round(chances_away, 6)
        ))

        simulation_id = cursor.lastrowid

        # zapisujemy początkowt tik
        cursor.execute("""
            INSERT INTO simulation_ticks (
                simulation_id,
                tick_number,
                home_odd,
                away_odd
            )
            VALUES (%s, 0, %s, %s)
        """, (
            simulation_id,
            odds_home,
            odds_away
        ))

        conn.commit()

        current_simulation_id = simulation_id
        isSimulationRunning = True
        
        current_sim_state["home_team"] = config.gospodarze
        current_sim_state["away_team"] = config.goscie
        
        current_sim_state["home_odd"] = odds_home
        current_sim_state["away_odd"] = odds_away
        
        current_sim_state["pool_home"] = 0.0
        current_sim_state["pool_away"] = 0.0
        
        current_sim_state["home_bets_count"] = 0
        current_sim_state["away_bets_count"] = 0
        
        current_sim_state["tick"] = 0
        
        current_sim_state["base_prob_home"] = chances_home
        current_sim_state["base_prob_away"] = chances_away
            
        return {
            "status": "ok",
            "message": "simulation started",
            "simulation_id": simulation_id,
            "initial_odds": {
                "home": odds_home,
                "away": odds_away
            }
        }

    except Exception as e:
        conn.rollback()
        
        current_simulation_id = None
        isSimulationRunning = False
        
        print("Błąd podczas zapisu symulacji do bazy:", e)

        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        cursor.close()
        conn.close()

@app.post("/api/stop")
def stop_simulation():
    global isSimulationRunning
    global current_simulation_id

    if current_simulation_id is None:
        isSimulationRunning = False

        return {
            "status": "ok",
            "message": "Brak aktywnej symulacji"
        }

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            UPDATE simulations
            SET status = 'FINISHED',
                finished_at = CURRENT_TIMESTAMP(3)
            WHERE id = %s
        """, (
            current_simulation_id,
        ))

        conn.commit()

        stopped_simulation_id = current_simulation_id

        current_simulation_id = None
        isSimulationRunning = False

        return {
            "status": "ok",
            "message": "simulation stopped",
            "simulation_id": stopped_simulation_id
        }

    except Exception as e:
        conn.rollback()
        print("Błąd podczas zatrzymywania symulacji:", e)

        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        cursor.close()
        conn.close()

@app.get("/api/status")
def get_status():
    global current_simulation_id
    global isSimulationRunning

    if not isSimulationRunning:
        return {
            "status": "waiting"
        }

    if current_simulation_id is None:
        return {
            "status": "error",
            "message": "Brak aktywnej symulacji"
        }

    # Numer nowego ticka
    tick_number = current_sim_state.get("tick", 0) + 1

    # Lokalne kopie aktualnego stanu
    pool_home = current_sim_state["pool_home"]
    pool_away = current_sim_state["pool_away"]

    home_bets_count = current_sim_state["home_bets_count"]
    away_bets_count = current_sim_state["away_bets_count"]

    bets_to_save = []
    new_bets = []

    # Generujemy od 1 do 3 zakładów podczas jednego ticka
    for _ in range(random.randint(1, 3)):

        bet_on_home = random.choices(
            [True, False],
            weights=[
                current_sim_state["base_prob_home"],
                current_sim_state["base_prob_away"]
            ],
            k=1
        )[0]

        if bet_on_home:
            market_type = "HOME_WIN"
            pozycja = (
                f"Wygrana: {current_sim_state['home_team']}"
            )
            aktualny_kurs = current_sim_state["home_odd"]
        else:
            market_type = "AWAY_WIN"
            pozycja = (
                f"Wygrana: {current_sim_state['away_team']}"
            )
            aktualny_kurs = current_sim_state["away_odd"]

        stawka = round(
            random.uniform(10.0, 1500.0),
            2
        )

        potencjalny_zwrot = round(
            stawka * aktualny_kurs,
            2
        )

        # Dane tylko dla frontend-u
        player_name = (
            f"Player_#{random.randint(1000, 9999)}"
        )

        transaction_id = (
            f"TX-{uuid.uuid4().hex[:6].upper()}"
        )

        if bet_on_home:
            pool_home += stawka
            home_bets_count += 1
        else:
            pool_away += stawka
            away_bets_count += 1

        # Dane zapisywane w tabeli bets
        bets_to_save.append(
            (
                market_type,
                stawka,
                aktualny_kurs
            )
        )

        # Dane zwracane do frontend-u
        new_bets.append({
            "gracz": player_name,
            "id": transaction_id,
            "pozycja": pozycja,
            "stawka": stawka,
            "zwrot": potencjalny_zwrot
        })

    # Procentowy rozkład zakładów
    total_pool = pool_home + pool_away

    if total_pool > 0:
        home_percent = int(
            (pool_home / total_pool) * 100
        )
        away_percent = 100 - home_percent
    else:
        home_percent = int(
            current_sim_state["base_prob_home"] * 100
        )
        away_percent = 100 - home_percent

    # Wirtualny kapitał bukmachera
    virtual_weight = 500000.0

    virtual_home_pool = (
        current_sim_state["base_prob_home"]
        * virtual_weight
    )

    virtual_away_pool = (
        current_sim_state["base_prob_away"]
        * virtual_weight
    )

    blended_home_pool = (
        virtual_home_pool + pool_home
    )

    blended_away_pool = (
        virtual_away_pool + pool_away
    )

    blended_total = (
        blended_home_pool + blended_away_pool
    )

    new_prob_home = (
        blended_home_pool / blended_total
    )

    new_prob_away = (
        blended_away_pool / blended_total
    )

    # Nowe kursy po przetworzeniu zakładów tego ticka
    home_odd = round(
        0.95 / new_prob_home,
        2
    )

    away_odd = round(
        0.95 / new_prob_away,
        2
    )

    home_odd = max(
        1.01,
        min(20.00, home_odd)
    )

    away_odd = max(
        1.01,
        min(20.00, away_odd)
    )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Tworzymy nowy tick
        cursor.execute("""
            INSERT INTO simulation_ticks (
                simulation_id,
                tick_number,
                home_odd,
                away_odd
            )
            VALUES (%s, %s, %s, %s)
        """, (
            current_simulation_id,
            tick_number,
            home_odd,
            away_odd
        ))

        tick_id = cursor.lastrowid

        # Zapisujemy wszystkie zakłady tego ticka
        cursor.executemany("""
            INSERT INTO bets (
                tick_id,
                market_type,
                stake,
                odd_at_bet
            )
            VALUES (%s, %s, %s,%s)
        """, [
            (
                tick_id,
                market_type,
                stake,
                odd_at_bet
            )
            for market_type, stake, odd_at_bet in bets_to_save
        ])

        conn.commit()

        # Aktualizujemy stan w pamięci dopiero po zapisie do bazy
        current_sim_state["tick"] = tick_number
        current_sim_state["pool_home"] = pool_home
        current_sim_state["pool_away"] = pool_away

        current_sim_state["home_bets_count"] = (
            home_bets_count
        )

        current_sim_state["away_bets_count"] = (
            away_bets_count
        )

        current_sim_state["home_odd"] = home_odd
        current_sim_state["away_odd"] = away_odd

        # Zostawiamy tylko dla obecnego frontend-u
        diff = abs(
            home_percent
            - current_sim_state["base_prob_home"] * 100
        )

        if diff > 30:
            ai_accuracy = 45
        elif diff > 15:
            ai_accuracy = 65
        else:
            ai_accuracy = 82

        return {
            "status": "in progress",

            "kursy": {
                "gospodarze": home_odd,
                "goscie": away_odd
            },

            "bets": {
                "gospodarze_proc": home_percent,
                "goscie_proc": away_percent
            },

            "ai accuracy": ai_accuracy,

            "last transactions": new_bets
        }

    except Exception as e:
        conn.rollback()
        print(
            "Błąd podczas aktualizacji symulacji:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        cursor.close()
        conn.close()

@app.get("/api/teams")
def get_teams():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, name, short_name
            FROM teams
            ORDER BY name
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

@app.get("/api/model/metrics")
def get_model_metrics():
    return ai_brain.get_model_metrics()