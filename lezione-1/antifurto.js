// Antifurto IA - il codice della pagina (LEZIONE 1)
//
// Come funziona, in breve:
//   1. chiediamo le impostazioni al server (/api/config);
//   2. carichiamo il modello di Teachable Machine e accendiamo la webcam;
//   3. a ogni fotogramma il modello dice "quanto è sicuro" per ogni classe;
//   4. se vede con sicurezza una classe NON autorizzata, scatta l'allarme:
//      schermo rosso, sirena e una chiamata al server che manda la mail.

// ---------------------------------------------------------------------------
// Impostazioni e variabili di stato
// ---------------------------------------------------------------------------

// Se per 3 secondi non vediamo più l'intruso, l'allarme si spegne da solo.
const SECONDI_FINE_ALLARME = 3;

// MISSIONE 2: cambia il suono della sirena.
// TIPO_ONDA può essere "sine", "square", "sawtooth" o "triangle".
const FREQUENZA_ALTA = 880;   // in Hz: più è alta, più il suono è acuto
const FREQUENZA_BASSA = 660;
const DURATA_NOTA_MS = 300;   // quanto dura ogni nota prima di cambiare
const TIPO_ONDA = "square";
const VOLUME = 0.2;           // da 0 (muto) a 1 (massimo)

let config = null;           // impostazioni ricevute dal server
let modello = null;          // il modello di Teachable Machine
let webcam = null;           // la webcam (gestita dalla libreria tmImage)
let allarmeAttivo = false;
let ultimoIntrusoVisto = 0;  // quando abbiamo visto l'ultimo intruso (in ms)
let disattivatoFinoA = 0;    // scenario gesti: fino a quando il sistema è spento
let audio = null;            // il "motore audio" del browser (Web Audio API)
let sirena = null;           // la sirena in funzione (o null se è spenta)

// MISSIONE 5: crea qui una variabile per contare gli intrusi, che parte da 0.

// ---------------------------------------------------------------------------
// Avvio
// ---------------------------------------------------------------------------

document.getElementById("avvia").addEventListener("click", avvia);
document.getElementById("ferma").addEventListener("click", fermaAllarme);

async function avvia() {
  const pulsante = document.getElementById("avvia");
  pulsante.disabled = true;
  try {
    config = await leggiConfig();
    mostraScenario();

    // Il browser permette di suonare solo dopo un clic dell'utente:
    // per questo creiamo il motore audio qui, dentro il clic su "Avvia".
    audio = new AudioContext();

    if (modalitaSimulazione()) {
      // simulatore.js: pulsanti al posto di webcam e modello (vedi README)
      modello = creaModelloSimulato(config.scenario);
      webcam = creaWebcamSimulata();
    } else {
      modello = await caricaModello(config.modello);
      webcam = await accendiWebcam();
    }

    const contenitore = document.getElementById("webcam");
    contenitore.innerHTML = "";
    contenitore.appendChild(webcam.canvas);

    creaBarre(modello.getClassLabels());
    impostaStato("ATTIVO", "attivo");
    requestAnimationFrame(ciclo);
  } catch (errore) {
    mostraErrore(errore.message);
    pulsante.disabled = false;
  }
}

async function leggiConfig() {
  try {
    const risposta = await fetch("/api/config");
    return await risposta.json();
  } catch (errore) {
    throw new Error("Non riesco a parlare con il server. Hai avviato python app.py?");
  }
}

async function caricaModello(indirizzo) {
  // Il link di Teachable Machine deve finire con "/"
  if (!indirizzo.endsWith("/")) {
    indirizzo = indirizzo + "/";
  }
  try {
    return await tmImage.load(indirizzo + "model.json", indirizzo + "metadata.json");
  } catch (errore) {
    throw new Error(
      "Modello non trovato in \"" + indirizzo + "\". " +
      "Controlla il campo \"modello\" in config.json (link di Teachable Machine o cartella locale)."
    );
  }
}

async function accendiWebcam() {
  // 320x320 pixel, true = immagine a specchio (più naturale da guardare)
  const nuovaWebcam = new tmImage.Webcam(320, 320, true);
  try {
    await nuovaWebcam.setup();
  } catch (errore) {
    throw new Error("Webcam non disponibile: controlla di aver dato il permesso al browser.");
  }
  await nuovaWebcam.play();
  return nuovaWebcam;
}

// ---------------------------------------------------------------------------
// Il ciclo principale: gira circa 30 volte al secondo
// ---------------------------------------------------------------------------

async function ciclo() {
  webcam.update();                                   // nuovo fotogramma
  const predizioni = await modello.predict(webcam.canvas);
  aggiornaBarre(predizioni);
  valutaPredizioni(predizioni);
  controllaFineAllarme();
  aggiornaStatoDisattivato();
  requestAnimationFrame(ciclo);                      // e si ricomincia
}

// Restituisce la predizione con la probabilità più alta.
function trovaMigliore(predizioni) {
  let migliore = predizioni[0];
  for (const predizione of predizioni) {
    if (predizione.probability > migliore.probability) {
      migliore = predizione;
    }
  }
  return migliore;
}

// Qui si decide se far scattare l'allarme.
function valutaPredizioni(predizioni) {
  const migliore = trovaMigliore(predizioni);
  document.getElementById("classe").textContent = migliore.className;

  // MISSIONE 1: la soglia si cambia in config.json ("soglia": 0.85).
  // Sotto la soglia il modello è "incerto": meglio non fare niente.
  if (migliore.probability < config.soglia) {
    return;
  }

  // Scenario gesti: se il sistema è stato disattivato, ignoriamo tutto.
  if (Date.now() < disattivatoFinoA) {
    return;
  }

  // Scenario gesti: il gesto giusto disattiva l'allarme.
  // MISSIONE 7: sostituisci questo controllo con la "password a due gesti".
  if (config.scenario === "gesti" && migliore.className === config.gesto_disattivazione) {
    disattivaSistema();
    return;
  }

  // Classe autorizzata: tutto tranquillo.
  if (config.classi_autorizzate.includes(migliore.className)) {
    return;
  }

  // Se arriviamo qui, è un intruso!
  // MISSIONE 6: fai scattare l'allarme solo se l'intruso resta
  // almeno 2 secondi di fila.
  ultimoIntrusoVisto = Date.now();
  if (!allarmeAttivo) {
    avviaAllarme(migliore);
  }
}

// ---------------------------------------------------------------------------
// Allarme
// ---------------------------------------------------------------------------

function avviaAllarme(predizione) {
  allarmeAttivo = true;
  document.body.classList.add("allarme");   // lo schermo lampeggia (vedi style.css)
  impostaStato("ALLARME", "allarme");
  avviaSirena();
  inviaAllarmeAlServer(predizione);

  // MISSIONE 5: aumenta il contatore degli intrusi e mostralo nella pagina.
}

function fermaAllarme() {
  allarmeAttivo = false;
  document.body.classList.remove("allarme");
  fermaSirena();
  if (modello) {
    impostaStato("ATTIVO", "attivo");
  }
}

// Se l'intruso non si vede più da qualche secondo, spegniamo l'allarme.
function controllaFineAllarme() {
  const passati = (Date.now() - ultimoIntrusoVisto) / 1000;
  if (allarmeAttivo && passati > SECONDI_FINE_ALLARME) {
    fermaAllarme();
  }
}

// Scenario gesti: spegne l'allarme e ignora tutto per qualche secondo.
function disattivaSistema() {
  fermaAllarme();
  disattivatoFinoA = Date.now() + config.secondi_disattivazione * 1000;
}

// Mostra il conto alla rovescia mentre il sistema è disattivato.
function aggiornaStatoDisattivato() {
  if (disattivatoFinoA === 0) {
    return;
  }
  const rimanenti = Math.ceil((disattivatoFinoA - Date.now()) / 1000);
  if (rimanenti > 0) {
    impostaStato("DISATTIVATO (" + rimanenti + " s)", "disattivato");
  } else {
    disattivatoFinoA = 0;
    impostaStato("ATTIVO", "attivo");
  }
}

// ---------------------------------------------------------------------------
// Sirena con la Web Audio API (nessun file audio: il suono lo generiamo noi)
// ---------------------------------------------------------------------------

function avviaSirena() {
  if (sirena) {
    return;  // suona già
  }
  const oscillatore = audio.createOscillator();  // genera l'onda sonora
  const volume = audio.createGain();             // regola il volume
  oscillatore.type = TIPO_ONDA;
  volume.gain.value = VOLUME;
  oscillatore.connect(volume);
  volume.connect(audio.destination);             // destination = casse del PC
  oscillatore.start();

  // Ogni DURATA_NOTA_MS alterniamo nota alta e nota bassa: "nii-no nii-no"
  let alta = true;
  const timer = setInterval(function () {
    oscillatore.frequency.value = alta ? FREQUENZA_ALTA : FREQUENZA_BASSA;
    alta = !alta;
  }, DURATA_NOTA_MS);

  sirena = { oscillatore: oscillatore, timer: timer };
}

function fermaSirena() {
  if (!sirena) {
    return;
  }
  clearInterval(sirena.timer);
  sirena.oscillatore.stop();
  sirena = null;
}

// ---------------------------------------------------------------------------
// Comunicazione con il server
// ---------------------------------------------------------------------------

async function inviaAllarmeAlServer(predizione) {
  const evento = {
    classe: predizione.className,
    confidenza: predizione.probability,
    origine: "webcam",
  };
  mostraStatoMail("Invio dell'allarme al server...");
  try {
    const risposta = await fetch("/api/allarme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(evento),
    });
    const esito = await risposta.json();
    mostraEsitoMail(esito);
  } catch (errore) {
    mostraStatoMail("Server non raggiungibile: hai avviato python app.py?");
  }
}

function mostraEsitoMail(esito) {
  const ora = new Date().toLocaleTimeString("it-IT");
  if (esito.esito === "inviata") {
    mostraStatoMail("Mail inviata alle " + ora + ".");
  } else if (esito.esito === "cooldown") {
    mostraStatoMail("Mail in cooldown: " + esito.messaggio + ".");
  } else if (esito.esito === "prova") {
    mostraStatoMail(esito.messaggio + " (la mail è stampata nel terminale).");
  } else {
    // Altri casi decisi dal server, per esempio fuori orario di sorveglianza.
    mostraStatoMail(esito.messaggio + ".");
  }
}

// ---------------------------------------------------------------------------
// Aggiornamento della pagina
// ---------------------------------------------------------------------------

// Crea una riga "nome / barra / percentuale" per ogni classe del modello.
function creaBarre(nomiClassi) {
  const contenitore = document.getElementById("barre");
  contenitore.innerHTML = "";
  for (const nome of nomiClassi) {
    const riga = document.createElement("div");
    riga.className = "barra";
    if (config.classi_autorizzate.includes(nome)) {
      riga.classList.add("autorizzata");
    }
    riga.innerHTML =
      '<span class="nome"></span>' +
      '<div class="fondo"><div class="riempimento"></div></div>' +
      '<span class="valore">0%</span>';
    riga.querySelector(".nome").textContent = nome;
    contenitore.appendChild(riga);
  }
}

function aggiornaBarre(predizioni) {
  const righe = document.querySelectorAll("#barre .barra");
  predizioni.forEach(function (predizione, i) {
    const percentuale = Math.round(predizione.probability * 100) + "%";
    righe[i].querySelector(".riempimento").style.width = percentuale;
    righe[i].querySelector(".valore").textContent = percentuale;
  });
}

function impostaStato(testo, classeCss) {
  const stato = document.getElementById("stato");
  stato.textContent = testo;
  stato.className = "pill " + classeCss;
}

function mostraScenario() {
  let testo = "Scenario: " + config.scenario +
    " | soglia: " + Math.round(config.soglia * 100) + "%" +
    " | autorizzate: " + config.classi_autorizzate.join(", ");
  if (config.scenario === "gesti") {
    testo += " | gesto che disattiva: " + config.gesto_disattivazione;
  }
  if (config.modalita_prova) {
    testo += " | mail in MODALITÀ PROVA";
  }
  document.getElementById("scenario").textContent = testo;
}

function mostraStatoMail(testo) {
  document.getElementById("stato-mail").textContent = testo;
}

function mostraErrore(testo) {
  const contenitore = document.getElementById("webcam");
  contenitore.innerHTML = "";
  const messaggio = document.createElement("p");
  messaggio.className = "errore";
  messaggio.textContent = testo;
  contenitore.appendChild(messaggio);
}
