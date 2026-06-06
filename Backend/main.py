from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import get_connection

from ai_model import train_ai_model

import random
import uuid

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

current_sim_state = {
    "home_team": "",
    "away_team": "",
    "home_odd": 0.0,
    "away_odd": 0.0,
    "pool_home": 0.0,
    "pool_away": 0.0
}

def get_team_id_by_name(cursor, team_name):
    # Pobieramy id drużyny po nazwie
    cursor.execute("""
        SELECT id
        FROM teams
        WHERE name = %s
    """, (team_name,))

    team = cursor.fetchone()

    if team is None:
        return None

    return team["id"]

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
    total = chances_home + chances_away

    if total <= 0:
        chances_home = 0.5
        chances_away = 0.5
    else:
        chances_home = chances_home / total
        chances_away = chances_away / total

    # Marża
    margin = 0.95

    # Zamiana prawdopodobieństw na kursy
    odds_home = round(margin / chances_home, 2)
    odds_away = round(margin / chances_away, 2)

    current_sim_state["home_team"] = config.gospodarze
    current_sim_state["away_team"] = config.goscie
    current_sim_state["home_odd"] = odds_home
    current_sim_state["away_odd"] = odds_away
    current_sim_state["pool_home"] = 0.0
    current_sim_state["pool_away"] = 0.0

    current_sim_state["base_prob_home"] = chances_home
    current_sim_state["base_prob_away"] = chances_away

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

        # Tworzymy nowa symulację
        cursor.execute("""
            INSERT INTO simulations (
                home_team_id,
                away_team_id,
                players_count,
                duration_seconds,
                status,
                current_tick,
                total_ticks,
                update_speed_ms,
                volatility,
                started_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            home_team_id,
            away_team_id,
            config.ilosc_graczy,
            config.czas_trwania,
            "RUNNING",
            0,
            config.czas_trwania,
            1000,
            1.00
        ))

        simulation_id = cursor.lastrowid

        # Zapisujemy ustawienia symulacji
        cursor.execute("""
            INSERT INTO simulation_settings (
                simulation_id,
                initial_home_odd,
                initial_away_odd,
                min_stake,
                max_stake
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            simulation_id,
            odds_home,
            odds_away,
            10.00,
            2000.00
        ))

        # Zapisujemy aktualne kursy
        cursor.execute("""
            INSERT INTO odds (
                simulation_id,
                market_type,
                current_odd,
                previous_odd,
                change_value,
                change_percent,
                trend
            )
            VALUES
            (%s, 'HOME_WIN', %s, %s, 0.00, 0.00, 'STABLE'),
            (%s, 'AWAY_WIN', %s, %s, 0.00, 0.00, 'STABLE')
        """, (
            simulation_id, odds_home, odds_home,
            simulation_id, odds_away, odds_away
        ))

        # Zapisujemy pierwszy punkt historii kursów
        cursor.execute("""
            INSERT INTO odds_history (
                simulation_id,
                tick_number,
                market_type,
                odd_value,
                height_percent,
                opacity_value
            )
            VALUES
            (%s, 0, 'HOME_WIN', %s, 50, 0.80),
            (%s, 0, 'AWAY_WIN', %s, 50, 0.80)
        """, (
            simulation_id, odds_home,
            simulation_id, odds_away
        ))

        # Zapisujemy początkowy rozkład zakładów
        cursor.execute("""
            INSERT INTO bet_distribution_snapshots (
                simulation_id,
                tick_number,
                home_total_amount,
                away_total_amount,
                draw_total_amount,
                home_bets_count,
                away_bets_count,
                draw_bets_count,
                home_percent,
                away_percent,
                draw_percent
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            simulation_id,
            0,
            0.00,
            0.00,
            0.00,
            0,
            0,
            0,
            0.00,
            0.00,
            0.00
        ))

        # Zapisujemy podstawowy wynik modelu
        cursor.execute("""
            INSERT INTO grading_results (
                simulation_id,
                tick_number,
                confidence_percent,
                grade,
                risk_level,
                stability_label,
                model_note
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            simulation_id,
            0,
            80.00,
            "A",
            "LOW",
            "STABILNY MODEL",
            "Kursy bazowe zostały obliczone na podstawie danych historycznych. Remis nie jest pokazywany jako osobny wynik zakładu."
        ))

        conn.commit()

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
    isSimulationRunning = False
    print("simulation stop...")

    return {"status": "ok", "message": "simulation stopped"}


@app.get("/api/status")
def get_status():
    if not isSimulationRunning:
        return {"status": "waiting"}

    # losowo 1 do 3 zakladow na sekunde
    new_bets = []
    for _ in range(random.randint(1, 3)):

        # losowanie zakladow graczy
        bet_on_home = random.choices(
            [True, False],
            weights=[current_sim_state["base_prob_home"], current_sim_state["base_prob_away"]],
            k=1
        )[0]

        pozycja = f"Wygrana: {current_sim_state['home_team']}" if bet_on_home else f"Wygrana: {current_sim_state['away_team']}"
        aktualny_kurs = current_sim_state["home_odd"] if bet_on_home else current_sim_state["away_odd"]

        # losujemy stawke
        stawka = round(random.uniform(10.0, 1500.0), 2)
        potencjalny_zwrot = round(stawka * aktualny_kurs, 2)

        if bet_on_home:
            current_sim_state["pool_home"] += stawka
        else:
            current_sim_state["pool_away"] += stawka

        # obiekt wirtualnego gracza
        new_bets.append({
            "gracz": f"Player_#{random.randint(1000, 9999)}",
            "id": f"TX-{uuid.uuid4().hex[:6].upper()}",
            "pozycja": pozycja,
            "stawka": stawka,
            "zwrot": potencjalny_zwrot
        })

    # procentowy rozklad
    total_pool = current_sim_state["pool_home"] + current_sim_state["pool_away"]
    if total_pool > 0:
        home_percent = int((current_sim_state["pool_home"] / total_pool) * 100)
        away_percent = 100 - home_percent
    else:
        home_percent = int(current_sim_state["base_prob_home"] * 100)
        away_percent = int(current_sim_state["base_prob_away"] * 100)

    VIRTUAL_WEIGHT = 500000.0  # Wirtualny kapital początkowy bukmachera

    virtual_home_pool = current_sim_state["base_prob_home"] * VIRTUAL_WEIGHT
    virtual_away_pool = current_sim_state["base_prob_away"] * VIRTUAL_WEIGHT

    blended_home_pool = virtual_home_pool + current_sim_state["pool_home"]
    blended_away_pool = virtual_away_pool + current_sim_state["pool_away"]
    blended_total = blended_home_pool + blended_away_pool

    # Przeliczamy nowe prawdopodobieństwo
    new_prob_home = blended_home_pool / blended_total
    new_prob_away = blended_away_pool / blended_total

    current_sim_state["home_odd"] = round(0.95 / new_prob_home, 2)
    current_sim_state["away_odd"] = round(0.95 / new_prob_away, 2)

    # grading
    diff = abs(home_percent - (current_sim_state["base_prob_home"] * 100))
    if diff > 30:
        ai_accuracy = 45
    elif diff > 15:
        ai_accuracy = 65
    else:
        ai_accuracy = 82

    return {
        "status": "in progress",
        "kursy": {
            "gospodarze": current_sim_state["home_odd"],
            "goscie": current_sim_state["away_odd"],
        },
        "bets": {
            "gospodarze_proc": home_percent,
            "goscie_proc": away_percent
        },
        "ai accuracy": ai_accuracy,
        "last transactions": new_bets
    }

@app.get("/api/teams")
def get_teams():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, short_name, strength_rating, form_rating
        FROM teams
    """)

    teams = cursor.fetchall()

    cursor.close()
    conn.close()

    return teams