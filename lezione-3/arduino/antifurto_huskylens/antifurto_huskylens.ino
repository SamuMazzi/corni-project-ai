// Antifurto IA - Arduino UNO R4 WiFi + HuskyLens (LEZIONE 3)
//
// Versione completa della lezione 2: le soluzioni delle missioni sono
// segnate con commenti "Lezione 2, missione N".
//
// Cosa fa:
//   - chiede a HuskyLens (collegata in I2C) quali volti vede;
//   - il volto imparato come ID 1 è AUTORIZZATO; un volto sconosciuto
//     (ID 0) o imparato con un altro ID è un INTRUSO;
//   - sulla matrice LED mostra un segno di ok o una X;
//   - per gli intrusi suona il buzzer e fa lampeggiare la matrice e il LED "L"
//     (così l'allarme si vede anche senza buzzer);
//   - manda al PC righe di testo come "EVENTO;INTRUSO;ID=2;FONTE=HUSKYLENS";
//   - se dal PC arriva "ALLARME" (la webcam ha visto un intruso) suona.
//
// Collegamenti:
//   HuskyLens (cavo a 4 fili, protocollo I2C):
//     T (SDA) -> SDA      R (SCL) -> SCL      - -> GND      + -> 5V
//     Usa i pin SDA/SCL vicino ad AREF (NON il connettore Qwiic).
//     Sulla HuskyLens: General Settings > Protocol Type > I2C.
//   Buzzer PASSIVO: + -> pin 8,  - -> GND  (facoltativo)
//
// Per insegnare un volto: inquadralo e premi il pulsante "learning" della
// HuskyLens. Il primo volto imparato diventa ID 1, il secondo ID 2...
// I volti restano solo dentro la HuskyLens: nessuna immagine arriva al PC.
// A fine lezione cancellali (pulsante "learning" quando non c'è nessun volto
// imparato davanti, oppure General Settings > Forget).
//
// Librerie (Sketch > Include library > Manage libraries / Add .ZIP):
//   - HUSKYLENS di DFRobot (ZIP da https://github.com/HuskyLens/HUSKYLENSArduino)
//   - Arduino_LED_Matrix (già inclusa nel pacchetto schede UNO R4)
//
// ATTENZIONE: questo sketch non è ancora stato provato su hardware vero.

#include <Wire.h>
#include "HUSKYLENS.h"
#include "Arduino_LED_Matrix.h"

// ---------------------------------------------------------------------------
// Impostazioni
// ---------------------------------------------------------------------------

const int PIN_BUZZER = 8;

// Gli ID dei volti autorizzati.
// Lezione 2, missione 3: due volti autorizzati.
const int ID_AUTORIZZATO = 1;
const int ID_AUTORIZZATO_2 = 2;

// Cosa può "vedere" HuskyLens:
//   NESSUNO = nessun volto, 0 = volto sconosciuto, 1, 2, ... = volti imparati.
const int NESSUNO = -1;
const int ID_SCONOSCIUTO = 0;

// Quante letture uguali di fila servono prima di cambiare stato:
// evita che un'immagine "tremolante" faccia scattare falsi allarmi.
const int LETTURE_STABILI = 5;
const unsigned long PAUSA_LETTURE_MS = 100;  // 10 letture al secondo

// Lezione 2, missione 1: la melodia della sirena (Do-Mi-Sol-Do acuto, pausa).
// Ogni nota ha una frequenza in Hz (0 = pausa) e una durata in millisecondi.
// Le due liste devono avere lo stesso numero di elementi!
const int NOTE_SIRENA[] = {523, 659, 784, 1047, 0};
const int DURATE_SIRENA[] = {150, 150, 150, 300, 200};
const int NUMERO_NOTE = 5;
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

// Lezione 2, missione 2: un punto esclamativo dentro un triangolo.
byte ICONA_INTRUSO[8][12] = {
  {0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0},
  {0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0},
  {0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0},
  {0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0},
  {0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0},
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
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

HUSKYLENS huskylens;
ArduinoLEDMatrix matrice;

int idAttuale = NESSUNO;   // l'ID "ufficiale"
int idCandidato = NESSUNO; // l'ultimo ID letto
int lettureUguali = 0;     // quante volte di fila abbiamo letto idCandidato
unsigned long ultimaLettura = 0;

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
  matrice.begin();
  matrice.renderBitmap(ICONA_NESSUNO, 8, 12);

  Wire.begin();
  // Finché HuskyLens non risponde, lo diciamo al PC e riproviamo.
  while (!huskylens.begin(Wire)) {
    Serial.println("INFO;HuskyLens non trovata: controlla cavi e protocollo I2C");
    delay(1000);
  }
  // Riconoscimento dei volti: tutto avviene dentro la HuskyLens.
  huskylens.writeAlgorithm(ALGORITHM_FACE_RECOGNITION);
  Serial.println("INFO;Antifurto HuskyLens pronto (Face Recognition)");
  collegaWiFi();  // solo se in wifi_ntfy.ino c'è il canale ntfy
}

void loop() {
  // Il loop non si ferma mai (niente delay lunghi): così possiamo leggere
  // HuskyLens, ascoltare il PC e suonare la sirena "contemporaneamente".
  leggiComandiDalPC();
  aggiornaSirena();
  if (millis() - ultimaLettura >= PAUSA_LETTURE_MS) {
    ultimaLettura = millis();
    controllaHuskyLens();
  }
}

// ---------------------------------------------------------------------------
// HuskyLens
// ---------------------------------------------------------------------------

// Lezione 2, missione 3: || vuol dire "oppure".
bool eAutorizzato(int id) {
  return id == ID_AUTORIZZATO || id == ID_AUTORIZZATO_2;
}

// Chiede a HuskyLens cosa vede e restituisce un ID (NESSUNO = nessun volto).
// Se vede più volti, un intruso "vince" sugli autorizzati.
// Se HuskyLens non risponde restituisce idCandidato: una lettura persa non
// cambia niente.
int leggiIdHuskyLens() {
  if (!huskylens.request()) {
    return idCandidato;
  }
  int idScelto = NESSUNO;
  while (huskylens.available()) {
    HUSKYLENSResult risultato = huskylens.read();
    if (risultato.command != COMMAND_RETURN_BLOCK) {
      continue;  // i volti arrivano come riquadri (block)
    }
    int id = risultato.ID;
    if (!eAutorizzato(id)) {
      return id;  // un intruso: inutile guardare il resto
    }
    idScelto = id;
  }
  return idScelto;
}

void controllaHuskyLens() {
  int id = leggiIdHuskyLens();

  // Contiamo quante volte di fila leggiamo lo stesso ID.
  if (id == idCandidato) {
    lettureUguali++;
  } else {
    idCandidato = id;
    lettureUguali = 1;
  }

  // Cambiamo stato solo se l'ID è nuovo ed è "stabile".
  if (lettureUguali >= LETTURE_STABILI && id != idAttuale) {
    idAttuale = id;
    nuovoStato(id);
  }
}

// Disegna sulla matrice l'icona giusta per un ID.
void mostraIcona(int id) {
  if (id == NESSUNO) {
    matrice.renderBitmap(ICONA_NESSUNO, 8, 12);
  } else if (eAutorizzato(id)) {
    matrice.renderBitmap(ICONA_OK, 8, 12);
  } else {
    matrice.renderBitmap(ICONA_INTRUSO, 8, 12);
  }
}

// Mostra l'icona, avvisa il PC e, se serve, suona.
void nuovoStato(int id) {
  if (id == NESSUNO) {
    mostraIcona(id);
    Serial.println("EVENTO;NESSUNO;FONTE=HUSKYLENS");
  } else if (eAutorizzato(id)) {
    fermaSirena();
    mostraIcona(id);
    Serial.println("EVENTO;AUTORIZZATO;ID=" + String(id) + ";FONTE=HUSKYLENS");
  } else {
    avviaSirena();
    Serial.println("EVENTO;INTRUSO;ID=" + String(id) + ";FONTE=HUSKYLENS");
    inviaNotificaWiFi("Intruso davanti all'antifurto (HuskyLens, ID " + String(id) + ")");
  }
}

// ---------------------------------------------------------------------------
// Comandi dal PC (app.py)
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
  if (comando == "ALLARME") {
    // La webcam del PC ha visto un intruso: suona la sirena fisica.
    avviaSirena();
  } else if (comando == "STOP") {
    fermaSirena();
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
  mostraIcona(idAttuale);  // finito il lampeggio, torna l'icona giusta
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
