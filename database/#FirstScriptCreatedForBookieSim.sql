USE insight_betting_simulator;

CREATE TABLE teams(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100) NOT NULL,
short_name VARCHAR(20),
logo_url VARCHAR(255),
primary_color VARCHAR(20),
secondary_color VARCHAR(20),
strength_rating DECIMAL(5,2) DEFAULT 50.00,
form_rating DECIMAL(5,2) DEFAULT 50.00,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE simulations (
id INT AUTO_INCREMENT PRIMARY KEY,
home_team_id INT NOT NULL,
away_team_id INT NOT NULL,
players_count INT DEFAULT 100,
duration_seconds INT DEFAULT 60,
status ENUM("CREATED", "RUNNING", "FINISHED", "CANCELED") DEFAULT "CREATED",
current_tick INT DEFAULT 0,
total_ticks INT DEFAULT 60,
update_speed_ms INT DEFAULT 1000,
volatility DECIMAL(5,2) DEFAULT 1.00,
started_at DATETIME NULL,
finished_at DATETIME NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_simulations_home_team
FOREIGN KEY ( home_team_id) REFERENCES teams(id),
CONSTRAINT fk_simulations_away_team
FOREIGN KEY ( away_team_id) REFERENCES teams(id)
);

CREATE TABLE simulation_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_id INT NOT NULL UNIQUE,
    min_odd DECIMAL(6,2) DEFAULT 1.01,
    max_odd DECIMAL(6,2) DEFAULT 10.00,
    initial_home_odd DECIMAL(6,2) DEFAULT 1.80,
    initial_away_odd DECIMAL(6,2) DEFAULT 2.20,
    max_odd_change_per_tick DECIMAL(6,2) DEFAULT 0.10,
    min_stake DECIMAL(10,2) DEFAULT 10.00,
    max_stake DECIMAL(10,2) DEFAULT 2000.00,
    min_opacity DECIMAL(4,2) DEFAULT 0.20,
    max_opacity DECIMAL(4,2) DEFAULT 1.00,
    min_chart_height INT DEFAULT 10,
    max_chart_height INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_settings_simulation
	FOREIGN KEY (simulation_id) REFERENCES simulations(id)
	ON DELETE CASCADE
);


CREATE TABLE odds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_id INT NOT NULL,
    market_type ENUM('HOME_WIN', 'AWAY_WIN', 'DRAW') NOT NULL,
    current_odd DECIMAL(6,2) NOT NULL,
    previous_odd DECIMAL(6,2),
    change_value DECIMAL(6,2),
    change_percent DECIMAL(6,2),
    trend ENUM('UP', 'DOWN', 'STABLE') DEFAULT 'STABLE',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_odds_simulation
	FOREIGN KEY (simulation_id) REFERENCES simulations(id)
	ON DELETE CASCADE,
    CONSTRAINT uq_odds_simulation_market
	UNIQUE (simulation_id, market_type)
);

CREATE TABLE odds_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_id INT NOT NULL,
    tick_number INT NOT NULL,
    market_type ENUM('HOME_WIN', 'AWAY_WIN', 'DRAW') NOT NULL,
    odd_value DECIMAL(6,2) NOT NULL,
    height_percent INT,
    opacity_value DECIMAL(4,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_odds_history_simulation
	FOREIGN KEY (simulation_id) REFERENCES simulations(id)
	ON DELETE CASCADE
);

CREATE TABLE simulation_bets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_id INT NOT NULL,
    generated_player_name VARCHAR(100) NOT NULL,
    transaction_id VARCHAR(100) NOT NULL,
    market_type ENUM('HOME_WIN', 'AWAY_WIN', 'DRAW') NOT NULL,
    stake DECIMAL(10,2) NOT NULL,
    odd_at_bet DECIMAL(6,2) NOT NULL,
    possible_return DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bets_simulation
	FOREIGN KEY (simulation_id) REFERENCES simulations(id)
	ON DELETE CASCADE,
    CONSTRAINT uq_transaction_id
	UNIQUE (transaction_id)
);

CREATE TABLE bet_distribution_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_id INT NOT NULL,
    tick_number INT NOT NULL,
    home_total_amount DECIMAL(12,2) DEFAULT 0.00,
    away_total_amount DECIMAL(12,2) DEFAULT 0.00,
    draw_total_amount DECIMAL(12,2) DEFAULT 0.00,
    home_bets_count INT DEFAULT 0,
    away_bets_count INT DEFAULT 0,
    draw_bets_count INT DEFAULT 0,
    home_percent DECIMAL(5,2) DEFAULT 0.00,
    away_percent DECIMAL(5,2) DEFAULT 0.00,
    draw_percent DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_distribution_simulation
	FOREIGN KEY (simulation_id) REFERENCES simulations(id)
	ON DELETE CASCADE
);

CREATE TABLE grading_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_id INT NOT NULL,
    tick_number INT NOT NULL,
    confidence_percent DECIMAL(5,2) DEFAULT 0.00,
    grade VARCHAR(10),
    risk_level ENUM('LOW', 'MEDIUM', 'HIGH') DEFAULT 'MEDIUM',
    stability_label VARCHAR(100),
    model_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_grading_simulation
	FOREIGN KEY (simulation_id) REFERENCES simulations(id)
	ON DELETE CASCADE
);
SHOW TABLES;

INSERT INTO teams 
(name, short_name, logo_url, primary_color, secondary_color, strength_rating, form_rating)
VALUES
('Chelsea', 'CHE', NULL, '#034694', '#FFFFFF', 82.50, 76.00),
('Brentford', 'BRE', NULL, '#E30613', '#FFFFFF', 68.00, 64.00),
('Arsenal', 'ARS', NULL, '#EF0107', '#FFFFFF', 85.00, 81.00),
('Liverpool', 'LIV', NULL, '#C8102E', '#FFFFFF', 86.00, 83.00),
('Manchester City', 'MCI', NULL, '#6CABDD', '#FFFFFF', 90.00, 87.00);
SELECT * FROM teams;

SELECT * FROM simulations;
ALTER TABLE simulations
CHANGE COLUMN uodate_speed_ms update_speed_ms INT DEFAULT 1000;

INSERT INTO simulations
(home_team_id, away_team_id, players_count, duration_seconds, status, total_ticks, update_speed_ms, volatility)
VALUES
(1, 2, 120, 60, 'CREATED', 60, 1000, 1.20);

INSERT INTO odds
(simulation_id, market_type, current_odd, previous_odd, change_value, change_percent, trend)
VALUES
(1, 'HOME_WIN', 1.85, 1.85, 0.00, 0.00, 'STABLE'),
(1, 'AWAY_WIN', 3.20, 3.20, 0.00, 0.00, 'STABLE');
SELECT * FROM odds;

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

INSERT INTO odds_history
(simulation_id, tick_number, market_type, odd_value, height_percent, opacity_value)
VALUES
(1, 1, 'HOME_WIN', 1.85, 40, 0.70),
(1, 2, 'HOME_WIN', 1.88, 50, 0.80),
(1, 3, 'HOME_WIN', 1.82, 35, 0.65),

(1, 1, 'AWAY_WIN', 3.20, 60, 0.80),
(1, 2, 'AWAY_WIN', 3.10, 55, 0.75),
(1, 3, 'AWAY_WIN', 3.45, 70, 0.90);
SELECT * FROM odds_history;

INSERT INTO simulation_bets
(simulation_id, generated_player_name, transaction_id, market_type, stake, odd_at_bet, possible_return)
VALUES
(1, 'Player_#8492', 'TX-0092-FF-18', 'HOME_WIN', 1200.00, 1.85, 2220.00),
(1, 'Player_#3122', 'TX-8102-AP-99', 'HOME_WIN', 850.00, 1.85, 1572.50),
(1, 'Player_#1044', 'TX-5512-KL-32', 'AWAY_WIN', 2000.00, 3.20, 6400.00);
SELECT * FROM simulation_bets;

INSERT INTO bet_distribution_snapshots
(simulation_id, tick_number, home_total_amount, away_total_amount, draw_total_amount,
 home_bets_count, away_bets_count, draw_bets_count,
 home_percent, away_percent, draw_percent)
VALUES
(1, 1, 2050.00, 2000.00, 0.00, 2, 1, 0, 50.62, 49.38, 0.00);
SELECT * FROM bet_distribution_snapshots;