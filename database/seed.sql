USE bookie_db;

INSERT IGNORE INTO teams (name, short_name)
VALUES
('Arsenal', 'ARS'),
('Aston Villa', 'AVL'),
('Bournemouth', 'BOU'),
('Brentford', 'BRE'),
('Brighton', 'BHA'),
('Burnley', 'BUR'),
('Chelsea', 'CHE'),
('Crystal Palace', 'CRY'),
('Everton', 'EVE'),
('Fulham', 'FUL'),
('Liverpool', 'LIV'),
('Luton', 'LUT'),
('Manchester City', 'MCI'),
('Manchester United', 'MUN'),
('Newcastle', 'NEW'),
('Nottingham Forest', 'NFO'),
('Sheffield United', 'SHU'),
('Tottenham', 'TOT'),
('West Ham', 'WHU'),
('Wolves', 'WOL');

SET @home_team_id = (
    SELECT id
    FROM teams
    WHERE name = 'Chelsea'
);

SET @away_team_id = (
    SELECT id
    FROM teams
    WHERE name = 'Brentford'
);


INSERT IGNORE INTO matchups (
    home_team_id,
    away_team_id
)
VALUES (
    @home_team_id,
    @away_team_id
);

SET @matchup_id = (
    SELECT id
    FROM matchups
    WHERE home_team_id = @home_team_id
      AND away_team_id = @away_team_id
);

INSERT INTO simulations (
    matchup_id,
    base_home_probability,
    base_away_probability,
    status
)
VALUES (
    @matchup_id,
    0.620000,
    0.380000,
    'RUNNING'
);

SET @simulation_id = LAST_INSERT_ID();

INSERT INTO simulation_ticks (
    simulation_id,
    tick_number,
    home_odd,
    away_odd
)
VALUES (
    @simulation_id,
    0,
    1.53,
    2.50
);

INSERT INTO simulation_ticks (
    simulation_id,
    tick_number,
    home_odd,
    away_odd
)
VALUES (
    @simulation_id,
    1,
    1.55,
    2.45
);

SET @tick_1_id = LAST_INSERT_ID();

INSERT INTO bets (
    tick_id,
    market_type,
    stake
)
VALUES
(@tick_1_id, 'HOME_WIN', 1200.00),
(@tick_1_id, 'HOME_WIN', 850.00),
(@tick_1_id, 'AWAY_WIN', 2000.00);

UPDATE simulations
SET
    status = 'FINISHED',
    finished_at = CURRENT_TIMESTAMP(3)
WHERE id = @simulation_id;

SELECT * FROM teams;

SELECT * FROM matchups;

SELECT * FROM simulations;

SELECT * FROM simulation_ticks
ORDER BY simulation_id, tick_number;

SELECT * FROM bets
ORDER BY id;

SELECT
    s.id AS simulation_id,
    home_team.name AS home_team,
    away_team.name AS away_team,
    s.base_home_probability,
    s.base_away_probability,
    s.status,
    s.started_at,
    s.finished_at
FROM simulations s
JOIN matchups m
    ON m.id = s.matchup_id
JOIN teams home_team
    ON home_team.id = m.home_team_id
JOIN teams away_team
    ON away_team.id = m.away_team_id
ORDER BY s.id DESC;

SELECT
    st.id AS tick_id,
    st.simulation_id,
    st.tick_number,
    st.home_odd,
    st.away_odd,
    st.created_at
FROM simulation_ticks st
ORDER BY st.simulation_id, st.tick_number;

SELECT
    b.id AS bet_id,
    st.simulation_id,
    st.tick_number,
    b.market_type,
    b.stake,
    st.created_at AS tick_time
FROM bets b
JOIN simulation_ticks st
    ON st.id = b.tick_id
ORDER BY st.simulation_id, st.tick_number, b.id;