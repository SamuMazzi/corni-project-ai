// Antifurto IA - Arduino UNO R4 WiFi SENZA HuskyLens (LEZIONE 2)
//
// Stessa logica di antifurto_huskylens, ma i volti "visti" sono finti:
//   - ogni pressione del PULSANTE passa all'ID successivo:
//       0 (nessuno) -> 1 (autorizzato) -> 2 (intruso) -> 3 (intruso) -> 0 ...
//   - oppure scrivi un comando (NESSUNO, AUTORIZZATO, INTRUSO, ID=3,
//     ALLARME, STOP) nel Monitor seriale (115200 baud, "A capo") oppure,
//     se app.py è avviato con --seriale, direttamente nel suo terminale.
//
// Serve per provare tutta la catena (Arduino -> app.py -> mail e registro)
// prima di avere HuskyLens funzionante.
//
// ATTENZIONE: il Monitor seriale e app.py non possono usare la porta insieme.
//
// Collegamenti (tutti facoltativi: senza niente collegato funziona lo stesso,
// la sirena lampeggia sulla matrice e sul LED "L"):
//   Pulsante: un piedino -> pin 2, l'altro -> GND (usiamo INPUT_PULLUP).
//     Senza pulsante: un cavetto nel pin 2; toccare GND con l'altro capo
//     è come premere.
//   Buzzer PASSIVO: + -> pin 8,  - -> GND
//
// Librerie: Arduino_LED_Matrix (già inclusa nel pacchetto schede UNO R4).
//
// ATTENZIONE: questo sketch non è ancora stato provato su hardware vero.

#include "Arduino_LED_Matrix.h"

// ---------------------------------------------------------------------------
// Impostazioni
// ---------------------------------------------------------------------------

const int PIN_BUZZER = 8;
const int PIN_PULSANTE = 2;
const int ID_MASSIMO = 3;  // il pulsante gira tra gli ID 0, 1, 2, 3

// L'ID del volto autorizzato.
// MISSIONE 3: aggiungi un secondo volto autorizzato (vedi la funzione
// eAutorizzato più in basso).
const int ID_AUTORIZZATO = 1;

// MISSIONE 1: cambia la melodia della sirena.
// Ogni nota ha una frequenza in Hz (0 = pausa) e una durata in millisecondi.
// Le due liste devono avere lo stesso numero di elementi!
const int NOTE_SIRENA[] = {880, 660, 880, 660};
const int DURATE_SIRENA[] = {300, 300, 300, 300};
const int NUMERO_NOTE = 4;
const int RIPETIZIONI_SIRENA = 3;  // quante volte ripetere la melodia

// ---------------------------------------------------------------------------
// Icone per la matrice LED (8 righe x 12 colonne, 1 = LED acceso)
// ---------------------------------------------------------------------------

byte ICONA_OK[8][12] = {
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0},
  {0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0},
  {0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0},
  {0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0}
};

// MISSIONE 2: disegna un'icona diversa per l'intruso (un teschio, un punto
// esclamativo, una faccina arrabbiata...). Cambia gli 0 e gli 1.
byte ICONA_INTRUSO[8][12] = {
  {0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0},
  {0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0},
  {0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0},
  {0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0},
  {0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0}
};

// Tutti i LED spenti: serve per far lampeggiare la matrice durante la sirena.
byte ICONA_SPENTA[8][12] = {0};

// Nessuno: un trattino al centro, "sto guardando".
byte ICONA_NESSUNO[8][12] = {
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
};

// ---------------------------------------------------------------------------
// Variabili di stato
// ---------------------------------------------------------------------------

ArduinoLEDMatrix matrice;

int idSimulato = 0;              // l'ID "visto" in questo momento
int statoPulsantePrecedente = HIGH;
unsigned long ultimoCambioPulsante = 0;

bool sirenaAccesa = false;
int notaCorrente = 0;
int ripetizioniFatte = 0;
unsigned long inizioNota = 0;

String comandoInArrivo = "";  // i caratteri arrivati dal PC, fino all'a capo

// ---------------------------------------------------------------------------
// setup e loop
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  // INPUT_PULLUP: il pin legge HIGH a riposo e LOW quando premi il pulsante.
  pinMode(PIN_PULSANTE, INPUT_PULLUP);
  matrice.begin();
  matrice.renderBitmap(ICONA_NESSUNO, 8, 12);
  Serial.println("INFO;Antifurto simulato pronto (pulsante sul pin 2)");
  collegaWiFi();  // solo se in wifi_ntfy.ino c'è il canale ntfy
}

void loop() {
  // Il loop non si ferma mai (niente delay lunghi): così possiamo leggere
  // il pulsante, ascoltare il PC e suonare la sirena "contemporaneamente".
  leggiComandiDalPC();
  controllaPulsante();
  aggiornaSirena();
}

// ---------------------------------------------------------------------------
// Simulazione
// ---------------------------------------------------------------------------

// MISSIONE 3: per avere due volti autorizzati crea ID_AUTORIZZATO_2 e
// restituisci true anche quando id è uguale a lui (operatore || = "oppure").
bool eAutorizzato(int id) {
  return id == ID_AUTORIZZATO;
}

void controllaPulsante() {
  int stato = digitalRead(PIN_PULSANTE);
  // 50 ms di "pazienza": un pulsante vero rimbalza e darebbe più pressioni.
  if (stato != statoPulsantePrecedente && millis() - ultimoCambioPulsante > 50) {
    ultimoCambioPulsante = millis();
    statoPulsantePrecedente = stato;
    if (stato == LOW) {  // appena premuto
      int prossimo = idSimulato + 1;
      if (prossimo > ID_MASSIMO) {
        prossimo = 0;
      }
      cambiaId(prossimo);
    }
  }
}

void cambiaId(int id) {
  idSimulato = id;
  nuovoStato(id);
}

// Disegna sulla matrice l'icona giusta per un ID.
void mostraIcona(int id) {
  if (id == 0) {
    matrice.renderBitmap(ICONA_NESSUNO, 8, 12);
  } else if (eAutorizzato(id)) {
    matrice.renderBitmap(ICONA_OK, 8, 12);
  } else {
    matrice.renderBitmap(ICONA_INTRUSO, 8, 12);
  }
}

// Mostra l'icona, avvisa il PC e, se serve, suona.
void nuovoStato(int id) {
  if (id == 0) {
    mostraIcona(id);
    Serial.println("EVENTO;NESSUNO;FONTE=SIMULATORE");
  } else if (eAutorizzato(id)) {
    fermaSirena();
    mostraIcona(id);
    Serial.println("EVENTO;AUTORIZZATO;ID=" + String(id) + ";FONTE=SIMULATORE");
  } else {
    avviaSirena();
    Serial.println("EVENTO;INTRUSO;ID=" + String(id) + ";FONTE=SIMULATORE");
    inviaNotificaWiFi("Intruso davanti all'antifurto (simulatore, ID " + String(id) + ")");
  }
}

// ---------------------------------------------------------------------------
// Comandi dal PC (app.py o Monitor seriale)
// ---------------------------------------------------------------------------

void leggiComandiDalPC() {
  while (Serial.available() > 0) {
    char carattere = Serial.read();
    if (carattere == '\n') {
      eseguiComando(comandoInArrivo);
      comandoInArrivo = "";
    } else if (carattere != '\r') {
      comandoInArrivo += carattere;
    }
  }
}

void eseguiComando(String comando) {
  comando.trim();
  comando.toUpperCase();
  if (comando == "ALLARME") {
    // La webcam del PC ha visto un intruso: suona la sirena fisica.
    avviaSirena();
  } else if (comando == "STOP") {
    fermaSirena();
  } else if (comando == "NESSUNO") {
    cambiaId(0);
  } else if (comando == "AUTORIZZATO") {
    cambiaId(ID_AUTORIZZATO);
  } else if (comando == "INTRUSO") {
    cambiaId(2);
  } else if (comando.startsWith("ID=")) {
    cambiaId(comando.substring(3).toInt());  // es. "ID=3" -> 3
  } else if (comando.length() > 0) {
    Serial.println("INFO;Comando sconosciuto: " + comando);
  }
}

// ---------------------------------------------------------------------------
// Sirena "senza delay": suona una nota alla volta controllando millis()
// ---------------------------------------------------------------------------

void avviaSirena() {
  sirenaAccesa = true;
  notaCorrente = 0;
  ripetizioniFatte = 0;
  suonaNota();
}

void fermaSirena() {
  sirenaAccesa = false;
  noTone(PIN_BUZZER);
  digitalWrite(LED_BUILTIN, LOW);
  mostraIcona(idSimulato);  // finito il lampeggio, torna l'icona giusta
}

void suonaNota() {
  int frequenza = NOTE_SIRENA[notaCorrente];
  if (frequenza > 0) {
    tone(PIN_BUZZER, frequenza);
  } else {
    noTone(PIN_BUZZER);  // 0 = pausa
  }
  // Lampeggio: una nota sì e una no la X è accesa. Così la sirena si vede
  // anche senza buzzer (e il ritmo della melodia diventa visibile).
  if (notaCorrente % 2 == 0) {
    matrice.renderBitmap(ICONA_INTRUSO, 8, 12);
    digitalWrite(LED_BUILTIN, HIGH);
  } else {
    matrice.renderBitmap(ICONA_SPENTA, 8, 12);
    digitalWrite(LED_BUILTIN, LOW);
  }
  inizioNota = millis();
}

void aggiornaSirena() {
  if (!sirenaAccesa) {
    return;
  }
  // La nota non è ancora finita: non facciamo niente.
  if (millis() - inizioNota < (unsigned long) DURATE_SIRENA[notaCorrente]) {
    return;
  }
  notaCorrente++;
  if (notaCorrente >= NUMERO_NOTE) {
    notaCorrente = 0;
    ripetizioniFatte++;
    if (ripetizioniFatte >= RIPETIZIONI_SIRENA) {
      fermaSirena();
      return;
    }
  }
  suonaNota();
}
