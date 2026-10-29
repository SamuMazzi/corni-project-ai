// Notifiche ntfy direttamente dall'Arduino, via WiFi (facoltativo)
//
// La UNO R4 WiFi ha il WiFi a bordo: può mandare la notifica al telefono
// da sola, anche senza PC (basta alimentarla con un caricatore USB).
//
// Per accenderlo scrivi qui sotto nome e password della rete e il canale
// ntfy. Lasciando vuoto NTFY_CANALE l'Arduino non usa il WiFi.
//
// ATTENZIONE:
//   - la scheda vede solo reti a 2,4 GHz; il WiFi della scuola con nome
//     utente e password personali (o con la pagina di login) non funziona:
//     usate l'hotspot di un telefono;
//   - non pubblicare mai questo file con la password del WiFi dentro;
//   - se anche app.py ha lo stesso canale in config.json, arrivano due
//     notifiche per ogni allarme (una dal PC e una dall'Arduino).

#include <WiFiS3.h>

const char WIFI_NOME[] = "";
const char WIFI_PASSWORD[] = "";
const char NTFY_CANALE[] = "";  // es. "antifurto-coppia3-k7q2"

const char NTFY_SERVER[] = "ntfy.sh";
const unsigned long PAUSA_NOTIFICHE_MS = 60000;  // al massimo una al minuto

bool primaNotifica = true;
unsigned long ultimaNotifica = 0;

bool wifiAcceso() {
  return strlen(NTFY_CANALE) > 0;
}

// Si collega al WiFi. Ci prova per qualche secondo, poi rinuncia: il resto
// dell'antifurto (sirena, matrice, seriale) funziona lo stesso.
bool collegaWiFi() {
  if (!wifiAcceso()) {
    return false;
  }
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }
  Serial.println("INFO;Mi collego al WiFi " + String(WIFI_NOME) + "...");
  WiFi.begin(WIFI_NOME, WIFI_PASSWORD);
  for (int tentativo = 0; tentativo < 20 && WiFi.status() != WL_CONNECTED; tentativo++) {
    delay(500);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("INFO;WiFi non collegato: controlla nome e password (rete a 2,4 GHz)");
    return false;
  }
  Serial.println("INFO;WiFi collegato, indirizzo " + WiFi.localIP().toString());
  return true;
}

// Manda una notifica al canale ntfy con una richiesta HTTP POST:
// sono righe di testo, proprio come i messaggi sulla seriale.
void inviaNotificaWiFi(String testo) {
  if (!wifiAcceso()) {
    return;
  }
  if (!primaNotifica && millis() - ultimaNotifica < PAUSA_NOTIFICHE_MS) {
    return;  // cooldown: niente raffica di notifiche
  }
  if (!collegaWiFi()) {
    return;
  }
  primaNotifica = false;
  ultimaNotifica = millis();

  WiFiClient client;
  if (!client.connect(NTFY_SERVER, 80)) {
    Serial.println("INFO;ntfy non raggiungibile");
    return;
  }
  // MISSIONE 6 (extra): cambia il titolo, la priorità (da 1 a 5) e le emoji.
  // Nelle intestazioni (Title, Tags...) niente lettere accentate.
  client.println("POST /" + String(NTFY_CANALE) + " HTTP/1.1");
  client.println("Host: " + String(NTFY_SERVER));
  client.println("Title: ALLARME dall'Arduino");
  client.println("Priority: 4");
  client.println("Tags: rotating_light");
  client.println("Content-Type: text/plain; charset=utf-8");
  client.println("Content-Length: " + String(testo.length()));
  client.println("Connection: close");
  client.println();  // riga vuota: finite le intestazioni, arriva il testo
  client.print(testo);

  // La prima riga della risposta dice se è andata bene ("HTTP/1.1 200 OK").
  unsigned long inizio = millis();
  while (!client.available() && millis() - inizio < 3000) {
    delay(10);
  }
  String risposta = client.readStringUntil('\n');
  client.stop();
  risposta.trim();
  Serial.println("INFO;Notifica ntfy: " + risposta);
}
