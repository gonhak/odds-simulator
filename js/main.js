const simulationBtn = document.querySelector("#simulationBtn");
const simulationBtnText = document.querySelector("#simulationBtnText");
const resetBtn = document.querySelector("#resetBtn");

const hostsTeam = document.querySelector("#hostsTeam");
const visitorsTeam = document.querySelector("#visitorsTeam");

const hostsPrevBtn = document.querySelector("#hostsPrevBtn");
const hostsNextBtn = document.querySelector("#hostsNextBtn");

const visitorsPrevBtn = document.querySelector("#visitorsPrevBtn");
const visitorsNextBtn = document.querySelector("#visitorsNextBtn");

const hostsStartStake = document.querySelector("#hostsStartStake");
const visitorsStartStake = document.querySelector("#visitorsStartStake");

const premierLeagueClubs = [
  "Arsenal",
  "Aston Villa",
  "Bournemouth",
  "Brentford",
  "Brighton",
  "Burnley",
  "Chelsea",
  "Crystal Palace",
  "Everton",
  "Fulham",
  "Liverpool",
  "Luton",
  "Manchester City",
  "Man United",
  "Newcastle",
  "Nottingham Forest",
  "Nott'm Forest",
  "Sheffield United",
  "Tottenham",
  "West Ham",
  "Wolves",
];

let isSimulationRunning = false;

let hostsIndex = 0;
let visitorsIndex = 6;

let homeOddsHistory = [];
let awayOddsHistory = [];

const homeChartBars = document.querySelectorAll(
  ".main__liveStatsContainer__upperContainer__currentStakeContainer:not(.main__liveStatsContainer__upperContainer__currentStakeContainer--enemy) .main__liveStatsContainer__upperContainer__currentStakeContainer__chart__bar"
);

const awayChartBars = document.querySelectorAll(
  ".main__liveStatsContainer__upperContainer__currentStakeContainer--enemy .main__liveStatsContainer__upperContainer__currentStakeContainer__chart__bar"
);

const updateOddsChart = (bars, history) => {
  if (!bars.length || !history.length) return;

  const minOdd = Math.min(...history);
  const maxOdd = Math.max(...history);

  bars.forEach((bar, index) => {
    const odd = history[index];

    if (odd === undefined) {
      bar.style.setProperty("--height", 10);
      bar.style.setProperty("--opacity", 0.25);
      bar.dataset.odd = "";
      return;
    }

    let height;

    if (maxOdd === minOdd) {
      height = 50;
    } else {
      height = 20 + ((odd - minOdd) / (maxOdd - minOdd)) * 80;
    }

    const opacity = 0.35 + (height / 100) * 0.65;

    bar.style.setProperty("--height", Math.round(height));
    bar.style.setProperty("--opacity", opacity.toFixed(2));
  });
};

const addOddsToHistory = (homeOdd, awayOdd) => {
  homeOddsHistory.push(Number(homeOdd));
  awayOddsHistory.push(Number(awayOdd));

  if (homeOddsHistory.length > 5) homeOddsHistory.shift();
  if (awayOddsHistory.length > 5) awayOddsHistory.shift();

  updateOddsChart(homeChartBars, homeOddsHistory);
  updateOddsChart(awayChartBars, awayOddsHistory);
};

const renderSimulationButton = () => {
  if (isSimulationRunning) {
    simulationBtn.classList.add(
      "main__configurationContainer__upper__buttonsContainer__button--active",
    );

    simulationBtnText.textContent = "STOP";
  } else {
    simulationBtn.classList.remove(
      "main__configurationContainer__upper__buttonsContainer__button--active",
    );

    simulationBtnText.textContent = "START";
  }
};

// stoper do odswiezania
let interval;

const startSimulation = () => {
  // 1. Zbieramy dane do wysłania
  const config = {
      gospodarze: premierLeagueClubs[hostsIndex],
      goscie: premierLeagueClubs[visitorsIndex],
      czas_trwania: 60, // narazie const
      ilosc_graczy: 100
  };

  // 2. polaczenie z backendem
  fetch('http://127.0.0.1:8000/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
  })
  .then(response => response.json())
  .then(data => {
      console.log("Serwer backend:", data.message);

      if (data.initial_odds) {
        console.log("kursy AI:", data.initial_odds);
        hostsStartStake.textContent = data.initial_odds.home.toFixed(2);
        visitorsStartStake.textContent = data.initial_odds.away.toFixed(2);
        
        homeOddsHistory = [];
        awayOddsHistory = [];

        addOddsToHistory(data.initial_odds.home, data.initial_odds.away);
      }

      isSimulationRunning = true;
      renderSimulationButton();

      // Odpalamy stoper sekunde
      interval = setInterval(getStatus, 1000);

      resetUI();
  })
  .catch(error => console.error("Błąd połączenia (START):", error));
};

const stopSimulation = () => {
  // stop do backendu
  fetch('http://127.0.0.1:8000/api/stop', { method: 'POST' })
  .then(response => response.json())
  .then(data => {
      console.log("Serwer backend:", data.message);

      isSimulationRunning = false;
      renderSimulationButton();

      // koniec stoper
      clearInterval(interval);
  })
  .catch(error => console.error("Błąd połączenia (STOP):", error));
};

// funckja pobierajaca dane co sekunde
const getStatus = () => {
    fetch('http://127.0.0.1:8000/api/status')
    .then(response => response.json())
    .then(data => {
        // Sprawdzamy czy symulacja trwa
        if (data.status === "in progress") {

            // aktualizacja UI co sekunde
            const homePercentText = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__row__percent")[0];
            const awayPercentText = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__row__percent")[1];

            if(homePercentText) homePercentText.textContent = data.bets.gospodarze_proc + "%";
            if(awayPercentText) awayPercentText.textContent = data.bets.goscie_proc + "%";

            const homeProgressBar = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__line__progress")[0];
            const awayProgressBar = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__line__progress")[1];

            if(homeProgressBar) homeProgressBar.style.setProperty('--width', data.bets.gospodarze_proc);
            if(awayProgressBar) awayProgressBar.style.setProperty('--width', data.bets.goscie_proc);

            const liveHome = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer:nth-child(1) .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__stake");
            const liveAway = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer--enemy .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__stake");

            if(liveHome) liveHome.textContent = data.kursy.gospodarze.toFixed(2);
            if(liveAway) liveAway.textContent = data.kursy.goscie.toFixed(2);

            addOddsToHistory(data.kursy.gospodarze, data.kursy.goscie);
            const homeTrendBox = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer:nth-child(1) .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__trendBox");
            const awayTrendBox = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer--enemy .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__trendBox");

            const setTrend = (trendBox, trend) => {
                if (!trendBox) return;
                const icon = trendBox.querySelector("svg");
                const text = trendBox.querySelector("p");

                if (trend === "up") {
                    trendBox.style.color = "var(--primary-color, #4edea3)";
                    text.textContent = "Wzrost";
                    icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />';
                } else if (trend === "down") {
                    trendBox.style.color = "var(--error-color, #e74c3c)";
                    text.textContent = "Spadek";
                    icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 4.5 15 15m0 0V8.25m0 11.25H8.25" />';
                } else {
                    trendBox.style.color = "#ccc";
                    text.textContent = "Stabilnie";
                    icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14" />';
                }
            };

            setTrend(homeTrendBox, data.kursy.trend_gospodarze);
            setTrend(awayTrendBox, data.kursy.trend_goscie);

            // generowanie wirtualnych graczy do tabeli
            const tableHeader = document.querySelector(".main__liveStatsContainer__historyContainer__table__header");

            if(tableHeader && data['last transactions']) {
                data['last transactions'].forEach(tx => {
                    const isEnemy = tx.pozycja.includes(visitorsTeam.textContent) ? "main__liveStatsContainer__historyContainer__table__row__position--enemy" : "";
                    const rowHTML = `
                        <div class="main__liveStatsContainer__historyContainer__table__row">
                          <div class="main__liveStatsContainer__historyContainer__table__row__player">
                            <div class="main__liveStatsContainer__historyContainer__table__row__player__iconBox">
                              <svg class="main__liveStatsContainer__historyContainer__table__row__player__iconBox__icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0" />
                              </svg>
                            </div>
                            <p class="main__liveStatsContainer__historyContainer__table__row__player__name">${tx.gracz}</p>
                          </div>
                          <p class="main__liveStatsContainer__historyContainer__table__row__id">${tx.id}</p>
                          <p class="main__liveStatsContainer__historyContainer__table__row__position ${isEnemy}">${tx.pozycja}</p>
                          <p class="main__liveStatsContainer__historyContainer__table__row__stake">${tx.stawka.toFixed(2)} zł</p>
                          <p class="main__liveStatsContainer__historyContainer__table__row__return">${tx.zwrot.toFixed(2)} zł</p>
                        </div>
                    `;
                    tableHeader.insertAdjacentHTML('afterend', rowHTML);
                });

                const allRows = document.querySelectorAll(".main__liveStatsContainer__historyContainer__table__row");
                if (allRows.length > 10) {
                    for(let i = 10; i < allRows.length; i++) {
                        allRows[i].remove();
                    }
                }
            }
        }
    })
    .catch(error => console.error("Błąd pobierania statusu:", error));
};

const toggleSimulation = () => {
  if (isSimulationRunning) {
    stopSimulation();
  } else {
    startSimulation();
  }
};

const resetSimulation = () => {
  stopSimulation();
};

const renderClubs = () => {
  hostsTeam.textContent = premierLeagueClubs[hostsIndex];
  visitorsTeam.textContent = premierLeagueClubs[visitorsIndex];
};
const changeClub = (team, direction) => {
  if (team === "hosts") {
    let nextIndex = hostsIndex;
    do {
      nextIndex += direction;
      if (nextIndex > premierLeagueClubs.length - 1) nextIndex = 0;
      if (nextIndex < 0) nextIndex = premierLeagueClubs.length - 1;
    } while (nextIndex === visitorsIndex);
    hostsIndex = nextIndex;
  }

  if (team === "visitors") {
    let nextIndex = visitorsIndex;
    do {
      nextIndex += direction;
      if (nextIndex > premierLeagueClubs.length - 1) nextIndex = 0;
      if (nextIndex < 0) nextIndex = premierLeagueClubs.length - 1;
    } while (nextIndex === hostsIndex);
    visitorsIndex = nextIndex;
  }
  renderClubs();
};

simulationBtn.addEventListener("click", toggleSimulation);
resetBtn.addEventListener("click", resetSimulation);
hostsPrevBtn.addEventListener("click", () => changeClub("hosts", -1));
hostsNextBtn.addEventListener("click", () => changeClub("hosts", 1));
visitorsPrevBtn.addEventListener("click", () => changeClub("visitors", -1));
visitorsNextBtn.addEventListener("click", () => changeClub("visitors", 1));

const resetUI = () => {
  const homePercentText = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__row__percent")[0];
  const awayPercentText = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__row__percent")[1];
  if(homePercentText) homePercentText.textContent = "50%";
  if(awayPercentText) awayPercentText.textContent = "50%";

  const homeProgressBar = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__line__progress")[0];
  const awayProgressBar = document.querySelectorAll(".main__liveStatsContainer__upperContainer__betsContainer__box__line__progress")[1];
  if(homeProgressBar) homeProgressBar.style.setProperty('--width', 50);
  if(awayProgressBar) awayProgressBar.style.setProperty('--width', 50);

  // Czyszczenie tabeli graczy
  const allRows = document.querySelectorAll(".main__liveStatsContainer__historyContainer__table__row");
  allRows.forEach(row => row.remove());

  // Wyzerowanie kursow na zywo
  const liveHome = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer:nth-child(1) .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__stake");
  const liveAway = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer--enemy .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__stake");
  if(liveHome) liveHome.textContent = "-";
  if(liveAway) liveAway.textContent = "-";

  // Wyzerowanie trendów
  const homeTrendBox = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer:nth-child(1) .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__trendBox");
  const awayTrendBox = document.querySelector(".main__liveStatsContainer__upperContainer__currentStakeContainer--enemy .main__liveStatsContainer__upperContainer__currentStakeContainer__middle__trendBox");

  if(homeTrendBox) {
      homeTrendBox.style.color = "#ccc";
      homeTrendBox.querySelector("p").textContent = "-";
      homeTrendBox.querySelector("svg").innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14" />';
  }
  if(awayTrendBox) {
      awayTrendBox.style.color = "#ccc";
      awayTrendBox.querySelector("p").textContent = "-";
      awayTrendBox.querySelector("svg").innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14" />';
  }

  // Resetowanie kolka z ai
  const aiCircle = document.querySelector(".main__liveStatsContainer__upperContainer__aiContainer__bottom__circle");
  const aiPercentText = document.querySelector(".main__liveStatsContainer__upperContainer__aiContainer__bottom__circle__inside__percent");
  const aiStatusText = document.querySelector(".main__liveStatsContainer__upperContainer__aiContainer__bottom__textBox__text");

  if(aiCircle) {
      aiCircle.style.setProperty('--percent', 0);
      aiCircle.style.setProperty('--circleColor', '#ccc');
  }
  if(aiPercentText) aiPercentText.textContent = "-%";
  if(aiStatusText) aiStatusText.textContent = "Oczekiwanie na start...";
};

renderSimulationButton();
renderClubs();
resetUI();