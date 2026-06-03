USE insight_betting_simulator;

SELECT * FROM teams;

SELECT 
    s.id AS simulation_id,
    ht.name AS home_team,
    at.name AS away_team,
    s.status,
    s.players_count,
    s.duration_seconds
FROM simulations s
JOIN teams ht ON s.home_team_id = ht.id
JOIN teams at ON s.away_team_id = at.id;

SELECT * FROM odds WHERE simulation_id = 1;

SELECT * FROM odds_history WHERE simulation_id = 1;

SELECT * FROM simulation_bets WHERE simulation_id = 1;

SELECT * FROM bet_distribution_snapshots WHERE simulation_id = 1;

SELECT * FROM grading_results WHERE simulation_id = 1;