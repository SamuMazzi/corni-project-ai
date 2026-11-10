// Dashboard dell'antifurto (LEZIONE 3)
//
// Ogni pochi secondi chiediamo al server la lista degli eventi
// (GET /api/eventi) e aggiorniamo la pagina.
//
// Ogni evento è un oggetto fatto così:
//   {
//     data_ora: "2026-10-21 10:30:05",
//     origine: "webcam",           // oppure "huskylens", "simulatore"
//     classe: "intruso",
//     confidenza: 0.93,            // null se l'evento viene da HuskyLens
//     mail_inviata: "si",          // oppure "no"
//     nota_mail: "inviata"         // oppure "cooldown", "prova"
//   }
//
// Lo scheletro funziona già: scarica gli eventi e mostra l'ultimo in fondo
// alla pagina. Il resto lo completate voi con le missioni (cerca MISSIONE).

const OGNI_QUANTI_SECONDI = 3;

// Se l'ultimo evento è più recente di così, il sistema è "in allarme".
const SECONDI_ALLARME = 30;

let tuttiGliEventi = [];   // gli eventi ricevuti dal server, dal più vecchio
let grafico = null;        // il grafico di Chart.js (lo creiamo una volta sola)

// ---------------------------------------------------------------------------
// Avvio e aggiornamento periodico
// ---------------------------------------------------------------------------

document.getElementById("filtro-origine").addEventListener("change", ridisegna);
document.getElementById("filtro-periodo").addEventListener("change", ridisegna);
document.getElementById("esporta").addEventListener("click", esportaCSV);

aggiorna();
setInterval(aggiorna, OGNI_QUANTI_SECONDI * 1000);

async function aggiorna() {
  try {
    const risposta = await fetch("/api/eventi");
    tuttiGliEventi = await risposta.json();
    mostraCollegamento(true);
  } catch (errore) {
    mostraCollegamento(false);
    return;
  }
  ridisegna();
}

// Ridisegna tutte le parti della pagina con gli eventi filtrati.
function ridisegna() {
  const eventi = applicaFiltri(tuttiGliEventi);
  document.getElementById("numero-eventi").textContent = eventi.length;
  mostraUltimoEvento(tuttiGliEventi);

  // Lo stato del sistema guarda TUTTI gli eventi, non solo quelli filtrati.
  mostraStato(tuttiGliEventi);
  disegnaTabella(eventi);
  aggiornaContatori(eventi);
  aggiornaGrafico(eventi);
}

// ---------------------------------------------------------------------------
// Già pronto
// ---------------------------------------------------------------------------

function mostraCollegamento(funziona) {
  const pill = document.getElementById("collegamento");
  if (funziona) {
    pill.textContent = "Aggiornato alle " + new Date().toLocaleTimeString("it-IT");
    pill.className = "pill attivo";
  } else {
    pill.textContent = "Server non raggiungibile";
    pill.className = "pill allarme";
  }
}

function mostraUltimoEvento(eventi) {
  if (eventi.length === 0) {
    return;
  }
  const ultimo = eventi[eventi.length - 1];
  // JSON.stringify con 2 spazi: stampa l'oggetto in modo leggibile.
  document.getElementById("ultimo-evento").textContent = JSON.stringify(ultimo, null, 2);
}

// Trasforma "2026-10-21 10:30:05" in un oggetto Date di JavaScript.
// Ti serve per le missioni 2 e 5.
function leggiData(evento) {
  return new Date(evento.data_ora.replace(" ", "T"));
}

// ---------------------------------------------------------------------------
// MISSIONE 1 (base): tabella degli ultimi eventi
// ---------------------------------------------------------------------------

function disegnaTabella(eventi) {
  // Obiettivo: mostrare gli ultimi 20 eventi, il più recente in alto.
  // 1. prendi gli ultimi 20: eventi.slice(-20)
  // 2. girali: .reverse()
  // 3. per ogni evento crea una riga <tr> con 5 celle <td>
  //    (data_ora, origine, classe, confidenza in %, mail_inviata)
  // 4. svuota il <tbody id="tabella-eventi"> e aggiungi le righe.
  // Attenzione: la confidenza può essere null (eventi di HuskyLens).
}

// ---------------------------------------------------------------------------
// MISSIONE 2 (base): stato del sistema
// ---------------------------------------------------------------------------

function mostraStato(eventi) {
  // Obiettivo: nel riquadro "stato-sistema" scrivere
  //   - "ALLARME" (sfondo rosso) se l'ultimo evento è di meno di
  //     SECONDI_ALLARME secondi fa;
  //   - "ATTIVO" (sfondo verde) altrimenti.
  // Suggerimento: Date.now() - leggiData(ultimo) dà i millisecondi passati.
  // In dashboard.css trovi già le classi "stato-grande" e "stato-grande allarme".
}

// ---------------------------------------------------------------------------
// MISSIONE 3 (intermedio): contatori per classe
// ---------------------------------------------------------------------------

function aggiornaContatori(eventi) {
  // Obiettivo: per ogni classe, un riquadro con il numero di eventi.
  // Suggerimento: usa un oggetto come "contachilometri":
  //   const conteggi = {};
  //   per ogni evento: conteggi[evento.classe] = (conteggi[evento.classe] || 0) + 1;
  // Poi crea un <div class="contatore"> per ogni classe, con dentro
  //   <span class="numero">5</span> intruso
}

// ---------------------------------------------------------------------------
// MISSIONE 4 (intermedio): grafico degli eventi nel tempo (Chart.js)
// ---------------------------------------------------------------------------

function aggiornaGrafico(eventi) {
  // Obiettivo: un grafico a barre con il numero di eventi per ogni ora.
  // 1. raggruppa per ora: evento.data_ora.slice(0, 13) dà "2026-10-21 10"
  //    (usa lo stesso trucco dei conteggi della missione 3);
  // 2. etichette = Object.keys(conteggi), valori = Object.values(conteggi);
  // 3. la prima volta crea il grafico:
  //      grafico = new Chart(document.getElementById("grafico"), {
  //        type: "bar",
  //        data: { labels: etichette, datasets: [{ label: "Eventi", data: valori }] },
  //        options: { maintainAspectRatio: false },
  //      });
  //    le volte successive aggiorna i dati e chiama grafico.update();
  // 4. nascondi il testo "grafico-vuoto".
}

// ---------------------------------------------------------------------------
// MISSIONE 5 (avanzato): filtri per origine e periodo
// ---------------------------------------------------------------------------

function applicaFiltri(eventi) {
  // Obiettivo: restituire solo gli eventi che rispettano i filtri scelti.
  // Leggi il valore dei due <select>:
  //   document.getElementById("filtro-origine").value  ("tutte", "webcam", ...)
  //   document.getElementById("filtro-periodo").value  ("tutto", "ora", "oggi", "settimana")
  // Suggerimento: eventi.filter(function (evento) { return ...; })
  // Per il periodo calcola un "da quando" in millisecondi e confrontalo con
  // leggiData(evento).getTime().
  return eventi;  // per ora nessun filtro
}

// ---------------------------------------------------------------------------
// MISSIONE 6 (avanzato): esportazione CSV
// ---------------------------------------------------------------------------

function esportaCSV() {
  // Obiettivo: scaricare un file .csv con gli eventi FILTRATI.
  // 1. const eventi = applicaFiltri(tuttiGliEventi);
  // 2. costruisci il testo: una riga di intestazione e una riga per evento,
  //    con i valori separati da ";" e le righe da "\n";
  // 3. crea il file e scaricalo:
  //      const file = new Blob([testo], { type: "text/csv" });
  //      const link = document.createElement("a");
  //      link.href = URL.createObjectURL(file);
  //      link.download = "eventi_filtrati.csv";
  //      link.click();
  alert("MISSIONE 6: esportazione non ancora fatta!");
}
