CREATE DATABASE IF NOT EXISTS insight_betting_simulator
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE insight_betting_simulator;

DROP TABLE IF EXISTS grading_results;
DROP TABLE IF EXISTS bet_distribution_snapshots;
DROP TABLE IF EXISTS simulation_bets;
DROP TABLE IF EXISTS odds_history;
DROP TABLE IF EXISTS odds;
DROP TABLE IF EXISTS simulation_settings;
DROP TABLE IF EXISTS simulations;
DROP TABLE IF EXISTS teams;

CREATE TABLE teams (
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

    status ENUM('CREATED', 'RUNNING', 'FINISHED', 'CANCELED') DEFAULT 'CREATED',

    current_tick INT DEFAULT 0,
    total_ticks INT DEFAULT 60,
    update_speed_ms INT DEFAULT 1000,

    volatility DECIMAL(5,2) DEFAULT 1.00,

    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_simulations_home_team
        FOREIGN KEY (home_team_id) REFERENCES teams(id),

    CONSTRAINT fk_simulations_away_team
        FOREIGN KEY (away_team_id) REFERENCES teams(id)
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