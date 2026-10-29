// Simulatore: prova l'antifurto SENZA webcam e SENZA modello.
//
// Apri la pagina con l'indirizzo  http://localhost:8000/?simula
// Al posto della webcam compaiono dei pulsanti, uno per classe:
// cliccandoli "fingi" che il modello veda quella classe.
//
// Serve per provare allarme, sirena e mail quando il modello non è ancora
// pronto. Non c'è bisogno di modificare questo file.

// Le classi di ogni scenario: devono essere uguali a quelle di Teachable Machine.
const CLASSI_SIMULATE = {
  animali: ["autorizzato", "intruso", "nessuno"],
  gesti: ["sasso", "carta", "forbice", "nessuno"],
};

// La classe "vista" in questo momento (all'inizio: nessuno).
let classeSimulata = "nessuno";

function modalitaSimulazione() {
  return new URLSearchParams(window.location.search).has("simula");
}

// Un finto modello con gli stessi metodi di quello vero:
// getClassLabels() e predict().
function creaModelloSimulato(scenario) {
  const classi = CLASSI_SIMULATE[scenario] || CLASSI_SIMULATE.animali;
  creaPulsantiSimulazione(classi);
  return {
    getClassLabels: function () {
      return classi;
    },
    predict: async function () {
      // La classe scelta ha il 95%, le altre si dividono il resto.
      const resto = 0.05 / (classi.length - 1);
      return classi.map(function (nome) {
        return { className: nome, probability: nome === classeSimulata ? 0.95 : resto };
      });
    },
  };
}

// Una finta webcam: un riquadro con scritto il nome della classe simulata.
function creaWebcamSimulata() {
  const canvas = document.createElement("canvas");
  canvas.width = 320;
  canvas.height = 320;
  const disegno = canvas.getContext("2d");
  return {
    canvas: canvas,
    update: function () {
      disegno.fillStyle = "#1d2330";
      disegno.fillRect(0, 0, canvas.width, canvas.height);
      disegno.fillStyle = "white";
      disegno.font = "bold 28px sans-serif";
      disegno.textAlign = "center";
      disegno.fillText("SIMULAZIONE", 160, 140);
      disegno.font = "22px sans-serif";
      disegno.fillText("vedo: " + classeSimulata, 160, 185);
    },
  };
}

function creaPulsantiSimulazione(classi) {
  const contenitore = document.querySelector(".pulsanti");
  for (const nome of classi) {
    const pulsante = document.createElement("button");
    pulsante.className = "secondario";
    pulsante.textContent = nome;
    pulsante.addEventListener("click", function () {
      classeSimulata = nome;
    });
    contenitore.appendChild(pulsante);
  }
}
