import pandas as pd
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "..", "premier_league.csv")

df = pd.read_csv(csv_path)
teams = sorted(set(df["HomeTeam"].unique()) | set(df["AwayTeam"].unique()))
for t in teams:
    print(t)