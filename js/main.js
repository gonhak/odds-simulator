const simulationBtn = document.querySelector("#simulationBtn");
const simulationBtnText = document.querySelector("#simulationBtnText");
const resetBtn = document.querySelector("#resetBtn");

const hostsTeam = document.querySelector("#hostsTeam");
const visitorsTeam = document.querySelector("#visitorsTeam");

const hostsPrevBtn = document.querySelector("#hostsPrevBtn");
const hostsNextBtn = document.querySelector("#hostsNextBtn");

const visitorsPrevBtn = document.querySelector("#visitorsPrevBtn");
const visitorsNextBtn = document.querySelector("#visitorsNextBtn");

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
  "Leeds United",
  "Liverpool",
  "Manchester City",
  "Manchester United",
  "Newcastle United",
  "Nottingham Forest",
  "Sunderland",
  "Tottenham",
  "West Ham",
  "Wolves",
];

let isSimulationRunning = false;

let hostsIndex = 0;
let visitorsIndex = 6;

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

      isSimulationRunning = true;
      renderSimulationButton();

      // Odpalamy stoper sekunde
      interval = setInterval(getStatus, 1000);
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
    .then(dane => {
        console.log("LIVE STATUS:", dane);
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

      if (nextIndex > premierLeagueClubs.length - 1) {
        nextIndex = 0;
      }

      if (nextIndex < 0) {
        nextIndex = premierLeagueClubs.length - 1;
      }
    } while (nextIndex === visitorsIndex);

    hostsIndex = nextIndex;
  }

  if (team === "visitors") {
    let nextIndex = visitorsIndex;

    do {
      nextIndex += direction;

      if (nextIndex > premierLeagueClubs.length - 1) {
        nextIndex = 0;
      }

      if (nextIndex < 0) {
        nextIndex = premierLeagueClubs.length - 1;
      }
    } while (nextIndex === hostsIndex);

    visitorsIndex = nextIndex;
  }

  renderClubs();
};

simulationBtn.addEventListener("click", toggleSimulation);

resetBtn.addEventListener("click", resetSimulation);

hostsPrevBtn.addEventListener("click", () => {
  changeClub("hosts", -1);
});

hostsNextBtn.addEventListener("click", () => {
  changeClub("hosts", 1);
});

visitorsPrevBtn.addEventListener("click", () => {
  changeClub("visitors", -1);
});

visitorsNextBtn.addEventListener("click", () => {
  changeClub("visitors", 1);
});

renderSimulationButton();
renderClubs();
