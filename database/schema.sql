DROP DATABASE IF EXISTS bookie_db;

CREATE DATABASE bookie_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE bookie_db;

CREATE TABLE teams (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(10) NOT NULL,

    CONSTRAINT uq_teams_name
        UNIQUE (name),

    CONSTRAINT uq_teams_short_name
        UNIQUE (short_name)
)
ENGINE = InnoDB;

CREATE TABLE matchups (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    home_team_id INT UNSIGNED NOT NULL,
    away_team_id INT UNSIGNED NOT NULL,

    CONSTRAINT fk_matchups_home_team
        FOREIGN KEY (home_team_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_matchups_away_team
        FOREIGN KEY (away_team_id)
        REFERENCES teams(id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_matchups_teams
        UNIQUE (home_team_id, away_team_id),

    CONSTRAINT chk_matchups_different_teams
        CHECK (home_team_id <> away_team_id)
)
ENGINE = InnoDB;

CREATE TABLE simulations (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    matchup_id INT UNSIGNED NOT NULL,

    base_home_probability DECIMAL(7,6) NOT NULL,
    base_away_probability DECIMAL(7,6) NOT NULL,

    status ENUM(
        'RUNNING',
        'FINISHED'
    ) NOT NULL DEFAULT 'RUNNING',

    started_at DATETIME(3)
        NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    finished_at DATETIME(3) NULL,

    CONSTRAINT fk_simulations_matchup
        FOREIGN KEY (matchup_id)
        REFERENCES matchups(id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_simulations_home_probability
        CHECK (
            base_home_probability BETWEEN 0 AND 1
        ),

    CONSTRAINT chk_simulations_away_probability
        CHECK (
            base_away_probability BETWEEN 0 AND 1
        ),

    CONSTRAINT chk_simulations_probability_sum
        CHECK (
            base_home_probability + base_away_probability
            BETWEEN 0.999900 AND 1.000100
        ),

    CONSTRAINT chk_simulations_status
        CHECK (
            (
                status = 'RUNNING'
                AND finished_at IS NULL
            )
            OR
            (
                status = 'FINISHED'
                AND finished_at IS NOT NULL
            )
        )
)
ENGINE = InnoDB;

CREATE TABLE simulation_ticks (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    simulation_id INT UNSIGNED NOT NULL,
    tick_number INT UNSIGNED NOT NULL,

    home_odd DECIMAL(8,2) NOT NULL,
    away_odd DECIMAL(8,2) NOT NULL,

    created_at DATETIME(3)
        NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_ticks_simulation
        FOREIGN KEY (simulation_id)
        REFERENCES simulations(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_ticks_simulation_number
        UNIQUE (simulation_id, tick_number),

    CONSTRAINT chk_ticks_home_odd
        CHECK (home_odd >= 1.00),

    CONSTRAINT chk_ticks_away_odd
        CHECK (away_odd >= 1.00)
)
ENGINE = InnoDB;

CREATE TABLE bets (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    tick_id INT UNSIGNED NOT NULL,

    market_type ENUM(
        'HOME_WIN',
        'AWAY_WIN'
    ) NOT NULL,

    stake DECIMAL(12,2) NOT NULL,
	odd_at_bet DECIMAL(8,2) NOT NULL,
    
    CONSTRAINT fk_bets_tick
        FOREIGN KEY (tick_id)
        REFERENCES simulation_ticks(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_bets_stake
        CHECK (stake > 0)
)
ENGINE = InnoDB;

SHOW TABLES;
