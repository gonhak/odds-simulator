from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import get_connection

#from random_forest_model import train_ai_model
#from ai_model import train_ai_model
#from decision_tree_model import train_ai_model
from model_comparison import train_ai_model

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

    # Wynik AI
    chances = ai_brain.get_match_probabilities(config.gospodarze, config.goscie)

    print("Model zwrócił:", chances)

    chances_home = float(chances.get("H", 0.5))
    chances_away = float(chances.get("A", 0.5))

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

        global current_simulation_id
        current_simulation_id = simulation_id

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
    global current_simulation_id

    isSimulationRunning = False
    print("simulation stop...")

    if current_simulation_id is None:
        return {
            "status": "ok",
            "message": "simulation stopped, but no active simulation was found in database"
        }

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # aktualizujemy status symulacji w bazie danych
        cursor.execute("""
            UPDATE simulations
            SET status = 'FINISHED',
                finished_at = NOW()
            WHERE id = %s
        """, (
            current_simulation_id,
        ))

        conn.commit()

        stopped_simulation_id = current_simulation_id
        current_simulation_id = None

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
        return {"status": "waiting"}
    
    if current_simulation_id is None:
        return {
            "status": "error",
            "message": "Brak aktywnej symulacji w bazie danych"
        }
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Zwiększamy numer ticka symulacji
        current_sim_state["tick"] = current_sim_state.get("tick", 0) + 1
        tick_number = current_sim_state["tick"]

        # losowo 1 do 3 zakladow na sekunde
        new_bets = []

        for _ in range(random.randint(1, 3)):

            # losowanie zakladow graczy
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
                pozycja = f"Wygrana: {current_sim_state['home_team']}"
                aktualny_kurs = current_sim_state["home_odd"]
            else:
                market_type = "AWAY_WIN"
                pozycja = f"Wygrana: {current_sim_state['away_team']}"
                aktualny_kurs = current_sim_state["away_odd"]

            # losujemy stawke
            stawka = round(random.uniform(10.0, 1500.0), 2)
            potencjalny_zwrot = round(stawka * aktualny_kurs, 2)

            player_name = f"Player_#{random.randint(1000, 9999)}"
            transaction_id = f"TX-{uuid.uuid4().hex[:6].upper()}"

            if bet_on_home:
                current_sim_state["pool_home"] += stawka
                current_sim_state["home_bets_count"] += 1
            else:
                current_sim_state["pool_away"] += stawka
                current_sim_state["away_bets_count"] += 1

            # Zapisujemy zakład do bazy danych
            cursor.execute("""
                INSERT INTO simulation_bets (
                    simulation_id,
                    generated_player_name,
                    transaction_id,
                    market_type,
                    stake,
                    odd_at_bet,
                    possible_return
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                current_simulation_id,
                player_name,
                transaction_id,
                market_type,
                stawka,
                aktualny_kurs,
                potencjalny_zwrot
            ))

            # obiekt wirtualnego gracza
            new_bets.append({
                "gracz": player_name,
                "id": transaction_id,
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

        # Wirtualny kapital początkowy bukmachera
        VIRTUAL_WEIGHT = 500000.0

        virtual_home_pool = current_sim_state["base_prob_home"] * VIRTUAL_WEIGHT
        virtual_away_pool = current_sim_state["base_prob_away"] * VIRTUAL_WEIGHT

        blended_home_pool = virtual_home_pool + current_sim_state["pool_home"]
        blended_away_pool = virtual_away_pool + current_sim_state["pool_away"]
        blended_total = blended_home_pool + blended_away_pool

        # Przeliczamy nowe prawdopodobieństwo
        new_prob_home = blended_home_pool / blended_total
        new_prob_away = blended_away_pool / blended_total

        previous_home_odd = current_sim_state["home_odd"]
        previous_away_odd = current_sim_state["away_odd"]

        current_sim_state["home_odd"] = round(0.95 / new_prob_home, 2)
        current_sim_state["away_odd"] = round(0.95 / new_prob_away, 2)

        home_odd = current_sim_state["home_odd"]
        away_odd = current_sim_state["away_odd"]

        home_change = round(home_odd - previous_home_odd, 2)
        away_change = round(away_odd - previous_away_odd, 2)

        home_change_percent = round((home_change / previous_home_odd) * 100, 2) if previous_home_odd != 0 else 0
        away_change_percent = round((away_change / previous_away_odd) * 100, 2) if previous_away_odd != 0 else 0

        home_trend = "UP" if home_change > 0 else "DOWN" if home_change < 0 else "STABLE"
        away_trend = "UP" if away_change > 0 else "DOWN" if away_change < 0 else "STABLE"

        # Aktualizujemy tabelę odds
        cursor.execute("""
            UPDATE odds
            SET current_odd = %s,
                previous_odd = %s,
                change_value = %s,
                change_percent = %s,
                trend = %s
            WHERE simulation_id = %s AND market_type = 'HOME_WIN'
        """, (
            home_odd,
            previous_home_odd,
            home_change,
            home_change_percent,
            home_trend,
            current_simulation_id
        ))

        cursor.execute("""
            UPDATE odds
            SET current_odd = %s,
                previous_odd = %s,
                change_value = %s,
                change_percent = %s,
                trend = %s
            WHERE simulation_id = %s AND market_type = 'AWAY_WIN'
        """, (
            away_odd,
            previous_away_odd,
            away_change,
            away_change_percent,
            away_trend,
            current_simulation_id
        ))

        # Zapisujemy historię kursów
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
            (%s, %s, 'HOME_WIN', %s, %s, %s),
            (%s, %s, 'AWAY_WIN', %s, %s, %s)
        """, (
            current_simulation_id,
            tick_number,
            home_odd,
            50,
            0.80,

            current_simulation_id,
            tick_number,
            away_odd,
            50,
            0.80
        ))

        # Zapisujemy rozkład zakładów
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
            current_simulation_id,
            tick_number,
            current_sim_state["pool_home"],
            current_sim_state["pool_away"],
            0.00,
            current_sim_state["home_bets_count"],
            current_sim_state["away_bets_count"],
            0,
            home_percent,
            away_percent,
            0.00
        ))

        # grading
        diff = abs(home_percent - (current_sim_state["base_prob_home"] * 100))

        if diff > 30:
            ai_accuracy = 45
            risk_level = "HIGH"
            grade = "C"
            stability_label = "NISKA STABILNOŚĆ"
        elif diff > 15:
            ai_accuracy = 65
            risk_level = "MEDIUM"
            grade = "B"
            stability_label = "ŚREDNIA STABILNOŚĆ"
        else:
            ai_accuracy = 82
            risk_level = "LOW"
            grade = "A"
            stability_label = "WYSOKA STABILNOŚĆ"

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
            current_simulation_id,
            tick_number,
            ai_accuracy,
            grade,
            risk_level,
            stability_label,
            "Ocena stabilności modelu na podstawie różnicy między przewidywaniami a rozkładem zakładów."
        ))

        # Aktualizujemy tick w tabeli simulations
        cursor.execute("""
            UPDATE simulations
            SET current_tick = %s
            WHERE id = %s
        """, (
            tick_number,
            current_simulation_id
        ))

        conn.commit()

        return {
            "status": "in progress",
            "kursy": {
                "gospodarze": home_odd,
                "goscie": away_odd,
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
        print("Błąd podczas aktualizacji statusu symulacji:", e)

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

    cursor.execute("""
        SELECT id, name, short_name, strength_rating, form_rating
        FROM teams
    """)

    teams = cursor.fetchall()

    cursor.close()
    conn.close()

    return teams

@app.get("/api/model/metrics")
def get_model_metrics():
    return ai_brain.get_model_metrics()