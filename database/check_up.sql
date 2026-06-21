USE bookie_db;

#очищают от предыдущих данных
SET SQL_SAFE_UPDATES = 0;

DELETE FROM bets;
DELETE FROM simulation_ticks;
DELETE FROM simulations;
DELETE FROM matchups;

SET SQL_SAFE_UPDATES = 1;

/*
проверка через сваггер пост старт, отправляем 
{
  "gospodarze": "Arsenal",
  "goscie": "Chelsea",
  "czas_trwania": 60,
  "ilosc_graczy": 100
}
*/
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM matchups;
SELECT COUNT(*) FROM simulations;
SELECT COUNT(*) FROM simulation_ticks;
SELECT COUNT(*) FROM bets;

SELECT
    s.id AS simulation_id,
    ht.name AS home_team,
    at.name AS away_team,
    s.base_home_probability,
    s.base_away_probability,
    s.status,
    s.started_at,
    s.finished_at
FROM simulations s
JOIN matchups m
    ON m.id = s.matchup_id
JOIN teams ht
    ON ht.id = m.home_team_id
JOIN teams at
    ON at.id = m.away_team_id;
    
#проверка тиков (через сваггер апи статус)
SELECT
    id,
    simulation_id,
    tick_number,
    home_odd,
    away_odd,
    created_at
FROM simulation_ticks
ORDER BY tick_number;


# остановка симуляции
SELECT
    id,
    status,
    started_at,
    finished_at
FROM simulations
ORDER BY id DESC;

#проверка ставки без существующего тика (должно вернуть нолик)
SELECT COUNT(*) AS orphan_bets
FROM bets b
LEFT JOIN simulation_ticks st
    ON st.id = b.tick_id
WHERE st.id IS NULL;

#повторяющиеся номера тиков (должно вернуть пустой результат)
SELECT 
    simulation_id, tick_number, COUNT(*) AS amount
FROM
    simulation_ticks
GROUP BY simulation_id , tick_number
HAVING COUNT(*) > 1;

#проверОчка суммы вероятностей
SELECT
    id,
    base_home_probability,
    base_away_probability,
    base_home_probability + base_away_probability AS probability_sum
FROM simulations;

#проверка что ставки не относяться к тику 0 
SELECT COUNT(*) AS bets_on_tick_zero
FROM bets b
JOIN simulation_ticks st
    ON st.id = b.tick_id
WHERE st.tick_number = 0;

#запустить тоже ещё раз через свеггер и проверить будет ли несколько симуляций но один матчап
SELECT COUNT(*) FROM matchups;
SELECT COUNT(*) FROM simulations;