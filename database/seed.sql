USE insight_betting_simulator;

INSERT INTO teams 
(name, short_name, logo_url, primary_color, secondary_color, strength_rating, form_rating)
VALUES
('Chelsea', 'CHE', NULL, '#034694', '#FFFFFF', 82.50, 76.00),
('Brentford', 'BRE', NULL, '#E30613', '#FFFFFF', 68.00, 64.00),
('Arsenal', 'ARS', NULL, '#EF0107', '#FFFFFF', 85.00, 81.00),
('Liverpool', 'LIV', NULL, '#C8102E', '#FFFFFF', 86.00, 83.00),
('Manchester City', 'MCI', NULL, '#6CABDD', '#FFFFFF', 90.00, 87.00);

INSERT INTO simulations
(home_team_id, away_team_id, players_count, duration_seconds, status, total_ticks, update_speed_ms, volatility)
VALUES
(1, 2, 120, 60, 'CREATED', 60, 1000, 1.20);

INSERT INTO simulation_settings
(simulation_id, initial_home_odd, initial_away_odd, min_stake, max_stake)
VALUES
(1, 1.85, 3.20, 10.00, 2000.00);

INSERT INTO odds
(simulation_id, market_type, current_odd, previous_odd, change_value, change_percent, trend)
VALUES
(1, 'HOME_WIN', 1.85, 1.85, 0.00, 0.00, 'STABLE'),
(1, 'AWAY_WIN', 3.20, 3.20, 0.00, 0.00, 'STABLE');

INSERT INTO odds_history
(simulation_id, tick_number, market_type, odd_value, height_percent, opacity_value)
VALUES
(1, 1, 'HOME_WIN', 1.85, 40, 0.70),
(1, 2, 'HOME_WIN', 1.88, 50, 0.80),
(1, 3, 'HOME_WIN', 1.82, 35, 0.65),
(1, 1, 'AWAY_WIN', 3.20, 60, 0.80),
(1, 2, 'AWAY_WIN', 3.10, 55, 0.75),
(1, 3, 'AWAY_WIN', 3.45, 70, 0.90);

INSERT INTO simulation_bets
(simulation_id, generated_player_name, transaction_id, market_type, stake, odd_at_bet, possible_return)
VALUES
(1, 'Player_#8492', 'TX-0092-FF-18', 'HOME_WIN', 1200.00, 1.85, 2220.00),
(1, 'Player_#3122', 'TX-8102-AP-99', 'HOME_WIN', 850.00, 1.85, 1572.50),
(1, 'Player_#1044', 'TX-5512-KL-32', 'AWAY_WIN', 2000.00, 3.20, 6400.00);

INSERT INTO bet_distribution_snapshots
(simulation_id, tick_number, home_total_amount, away_total_amount, draw_total_amount,
 home_bets_count, away_bets_count, draw_bets_count,
 home_percent, away_percent, draw_percent)
VALUES
(1, 1, 2050.00, 2000.00, 0.00, 2, 1, 0, 50.62, 49.38, 0.00);

INSERT INTO grading_results
(simulation_id, tick_number, confidence_percent, grade, risk_level, stability_label, model_note)
VALUES
(1, 1, 82.00, 'A', 'LOW', 'WYSOKA STABILNOŚĆ', 'Model wykazuje stabilny trend kursów.');

SELECT COUNT(*) FROM teams;

SELECT COUNT(*) FROM historical_matches;

SELECT 
    hm.id,
    hm.match_date,
    ht.name AS home_team,
    at.name AS away_team,
    hm.home_goals,
    hm.away_goals,
    hm.result,
    hm.b365_home_odd,
    hm.b365_draw_odd,
    hm.b365_away_odd
FROM historical_matches hm
JOIN teams ht ON hm.home_team_id = ht.id
JOIN teams at ON hm.away_team_id = at.id
LIMIT 20;

SELECT * FROM simulations ORDER BY id DESC;
SELECT * FROM odds ORDER BY id DESC;
SELECT * FROM odds_history ORDER BY id DESC;
SELECT * FROM grading_results ORDER BY id DESC;