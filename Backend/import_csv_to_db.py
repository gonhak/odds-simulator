import pandas as pd
from db import get_connection


CSV_PATH = "../premier_league.csv"


def safe_int(value):
    """Zamienia wartość na int albo zwraca None, jeśli wartość jest pusta."""
    if pd.isna(value):
        return None
    return int(value)


def safe_float(value):
    """Zamienia wartość na float albo zwraca None, jeśli wartość jest pusta."""
    if pd.isna(value):
        return None
    return float(value)


def main():
    df = pd.read_csv(CSV_PATH)

    # Kolumny wymagane do importu danych historycznych
    required_columns = [
        "Date", "HomeTeam", "AwayTeam",
        "FTHG", "FTAG", "FTR",
        "HS", "AS", "HST", "AST",
        "B365H", "B365D", "B365A"
    ]

    # Sprawdzamy, czy wszystkie potrzebne kolumny istnieją w pliku CSV
    for col in required_columns:
        if col not in df.columns:
            raise Exception(f"Brakuje kolumny w CSV: {col}")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Dodajemy drużyny z pliku CSV do tabeli teams
    teams = sorted(set(df["HomeTeam"]).union(set(df["AwayTeam"])))

    for team in teams:
        short_name = team[:3].upper()

        cursor.execute("""
            INSERT IGNORE INTO teams (name, short_name, strength_rating, form_rating)
            VALUES (%s, %s, %s, %s)
        """, (team, short_name, 50.00, 50.00))

    conn.commit()

    # Pobieramy id drużyn z bazy danych
    cursor.execute("SELECT id, name FROM teams")
    team_rows = cursor.fetchall()

    team_ids = {}
    for row in team_rows:
        team_ids[row["name"]] = row["id"]

    # Dodajemy historyczne mecze do tabeli historical_matches
    inserted_count = 0

    for _, row in df.iterrows():
        home_team = row["HomeTeam"]
        away_team = row["AwayTeam"]

        home_team_id = team_ids.get(home_team)
        away_team_id = team_ids.get(away_team)

        # Jeśli którejś drużyny nie ma w bazie, pomijamy ten mecz
        if home_team_id is None or away_team_id is None:
            print(f"Nie znaleziono drużyny: {home_team} vs {away_team}")
            continue

        # Zamieniamy datę z CSV na format daty zrozumiały dla MySQL
        match_date = pd.to_datetime(row["Date"], dayfirst=True, errors="coerce")

        # Jeśli data jest niepoprawna, pomijamy ten mecz
        if pd.isna(match_date):
            print(f"Niepoprawna data: {row['Date']}")
            continue

        cursor.execute("""
            INSERT IGNORE INTO historical_matches (
                match_date,
                home_team_id,
                away_team_id,
                home_goals,
                away_goals,
                result,
                home_shots,
                away_shots,
                home_shots_target,
                away_shots_target,
                b365_home_odd,
                b365_draw_odd,
                b365_away_odd
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            match_date.date(),
            home_team_id,
            away_team_id,
            safe_int(row["FTHG"]),
            safe_int(row["FTAG"]),
            row["FTR"],
            safe_int(row["HS"]),
            safe_int(row["AS"]),
            safe_int(row["HST"]),
            safe_int(row["AST"]),
            safe_float(row["B365H"]),
            safe_float(row["B365D"]),
            safe_float(row["B365A"])
        ))

        inserted_count += cursor.rowcount

    conn.commit()

    cursor.close()
    conn.close()

    print(f"Liczba drużyn z CSV: {len(teams)}")
    print(f"Liczba zaimportowanych meczów historycznych: {inserted_count}")


if __name__ == "__main__":
    main()