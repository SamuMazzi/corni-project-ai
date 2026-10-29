# Missioni della lezione 2

In questa lezione l'antifurto esce dal computer: Arduino UNO R4 WiFi,
HuskyLens (una telecamera con l'intelligenza artificiale a bordo, che
riconosce i volti), un buzzer e la matrice LED della scheda.

Buzzer e pulsante sono **facoltativi**. Senza buzzer la sirena si vede:
la X lampeggia sulla matrice e il LED "L" della scheda lampeggia a tempo.
Senza pulsante, scrivi i comandi (`INTRUSO`, `AUTORIZZATO`, `NESSUNO`,
`ID=3`) nel terminale di `app.py` e premi Invio.

Il codice della pagina web è la versione completa della lezione 1: le
soluzioni sono segnate con commenti `Lezione 1, missione N`.

Nel codice delle nuove missioni trovi un commento `MISSIONE N`: cercalo con
**Ctrl + F**.

Per provare le missioni sull'Arduino:

1. apri lo sketch nell'IDE Arduino;
2. **chiudi** `app.py` (Ctrl + C), perché l'IDE e `app.py` non possono
   usare la porta USB insieme;
3. carica lo sketch;
4. riavvia `python app.py --seriale COM3` (con la tua porta).

In classe c'è **una sola HuskyLens**, che gira tra i banchi. Fino al
vostro turno lavorate con lo sketch `arduino/antifurto_senza_huskylens`:
finge di vedere un volto diverso a ogni pressione del pulsante sul pin 2
(0 nessuno, 1 autorizzato, 2 e 3 intrusi). Al posto del pulsante va bene un
cavetto nel pin 2: tocca GND con l'altro capo. Le missioni sono uguali nei
due sketch.

**Il giro della HuskyLens (circa 8 minuti a coppia).** Prima del turno:

1. ricopiate le vostre missioni 1, 2 e 3 in `arduino/antifurto_huskylens`
   (le parti con `MISSIONE N` sono uguali) e premete **Verifica** nell'IDE:
   deve compilare anche senza HuskyLens collegata;
2. quando arriva la HuskyLens: chiudete `app.py`, **staccate il cavo USB**,
   collegate i 4 fili (T -> SDA, R -> SCL, - -> GND, + -> 5V), ricollegate
   il cavo e caricate lo sketch;
3. riavviate `app.py --seriale`, insegnate il vostro volto (ID 1), fate
   scattare un allarme con un volto sconosciuto e controllate registro e
   notifica ntfy;
4. a fine turno **cancellate i volti imparati** (*Forget*), staccate il
   cavo USB e passate la HuskyLens alla coppia successiva.

**HuskyLens e i volti.** Lo sketch mette HuskyLens in *Face Recognition*.
Per insegnarle un volto inquadralo e premi il pulsante *learning*: il primo
volto imparato è l'ID 1 (autorizzato). Un volto mai visto ha ID 0 ed è un
intruso. Le immagini restano dentro la HuskyLens: al PC arriva solo un
numero.

---

## Missione 1 (base): la melodia della sirena

- **Obiettivo:** creare una sirena riconoscibile, solo vostra.
- **Dove:** sketch Arduino, liste `NOTE_SIRENA` e `DURATE_SIRENA`
  (`MISSIONE 1`).
- **Suggerimento:** ogni posizione delle due liste è una nota: frequenza
  in Hz e durata in millisecondi. `0` come frequenza è una pausa. Alcune
  note: Do 523, Re 587, Mi 659, Fa 698, Sol 784, La 880, Si 988.
  Se aggiungi note ricordati di aggiornare `NUMERO_NOTE`.
- **Come verificare:** carica lo sketch e fai vedere un intruso (o scrivi
  `INTRUSO`). Anche un allarme della webcam fa suonare la nuova melodia.
  Senza buzzer guarda la matrice: lampeggia una nota sì e una no, quindi
  si vede il ritmo della melodia.

## Missione 2 (base): l'icona dell'intruso

- **Obiettivo:** disegnare un'icona diversa sulla matrice LED.
- **Dove:** sketch Arduino, `ICONA_INTRUSO` (`MISSIONE 2`).
- **Suggerimento:** la matrice ha 8 righe e 12 colonne: `1` = LED acceso.
  Disegnala prima su un foglio a quadretti. Puoi anche usare l'editor
  online di Arduino per la matrice LED e copiare i numeri.
- **Come verificare:** quando arriva un intruso compare la tua icona.

## Missione 3 (intermedio): un secondo volto autorizzato

- **Obiettivo:** due persone devono essere "di casa" (per esempio i due
  componenti della coppia).
- **Dove:** sketch Arduino, costante `ID_AUTORIZZATO` e funzione
  `eAutorizzato` (`MISSIONE 3`).
- **Suggerimento:**
  1. aggiungi `const int ID_AUTORIZZATO_2 = 2;`;
  2. in `eAutorizzato` scrivi
     `return id == ID_AUTORIZZATO || id == ID_AUTORIZZATO_2;`
     (`||` vuol dire "oppure").

  Con HuskyLens: per imparare più volti attiva *Learn Multiple* (tieni
  premuta la rotella su *Face Recognition*, poi *Learn Multiple* > ON),
  poi insegnale il secondo volto come ID 2. Nello sketch senza HuskyLens
  l'ID 2 diventa autorizzato e resta intruso solo l'ID 3.
- **Come verificare:** con l'ID 2 compare il segno di ok e non suona
  niente; con un volto sconosciuto (o con l'ID 3) scatta l'allarme.

## Missione 4 (intermedio): da dove arriva l'evento?

- **Obiettivo:** nel registro `eventi.csv` la colonna `origine` deve dire
  se l'allarme viene dalla `webcam`, da `huskylens` o dal `simulatore`.
  Ora gli eventi dell'Arduino sono tutti `arduino`.
- **Dove:** `app.py`, funzione `gestisci_messaggio_arduino`
  (`MISSIONE 4`). È Python: devi cambiare **una sola riga**.
- **Suggerimento:** gli sketch mandano già il campo `FONTE`, per esempio
  `EVENTO;INTRUSO;ID=2;FONTE=HUSKYLENS`. Nel dizionario `messaggio` lo
  trovi con `messaggio.get("FONTE", "arduino")`. Aggiungi `.lower()` per
  avere il testo in minuscolo, come `webcam`.
- **Come verificare:** riavvia `app.py --seriale ...`, fai scattare un
  allarme con la webcam e uno con l'Arduino. Apri `eventi.csv` (o
  `http://localhost:8000/api/eventi`): l'origine deve essere diversa.

## Missione 5 (base): l'antifurto ti scrive sul telefono

- **Obiettivo:** a ogni allarme arriva una notifica sul telefono, con
  [ntfy](https://ntfy.sh): niente account e niente password.
- **Dove:** `config.json` (sezione `"ntfy"`) e `app.py`, funzione
  `invia_notifica` (`MISSIONE 5`).
- **Passi:**
  1. inventate un nome di canale difficile da indovinare, per esempio
     `antifurto-coppia3-k7q2`. Chi conosce il nome legge le notifiche:
     niente nomi, cognomi o dati personali;
  2. in `config.json` scrivetelo in `"canale"` dentro `"ntfy"` e riavviate
     `app.py`: nel terminale compare il nome del canale;
  3. sul telefono installate l'app **ntfy**, premete **+** e scrivete lo
     stesso nome. Senza telefono aprite nel browser
     `https://ntfy.sh/` seguito dal nome del canale;
  4. in `invia_notifica` cambiate `"priority"` e `"tags"` (le emoji
     accanto al titolo, per esempio `["rotating_light"]`).
- **Come verificare:** fate scattare un allarme (webcam, HuskyLens o
  `INTRUSO` nel terminale): arriva la notifica con la vostra emoji. Ricorda
  il cooldown: tra due notifiche passano almeno 60 secondi.

## Missione 6 (extra): l'Arduino fa da solo, via WiFi

- **Obiettivo:** la notifica ntfy la manda direttamente l'Arduino con il
  suo WiFi, anche senza PC (alimentato da un caricatore USB).
- **Dove:** sketch Arduino, scheda (tab) `wifi_ntfy` in alto nell'IDE
  (`MISSIONE 6`).
- **Passi:**
  1. accendete l'hotspot di un telefono (rete a **2,4 GHz**: il WiFi della
     scuola di solito non va bene);
  2. scrivete `WIFI_NOME`, `WIFI_PASSWORD` e `NTFY_CANALE`;
  3. caricate lo sketch: sul Monitor seriale (o nel terminale di `app.py`)
     compare `WiFi collegato`;
  4. cambiate titolo, priorità ed emoji della richiesta.
- **Come verificare:** fate scattare un intruso: arriva la notifica
  "ALLARME dall'Arduino" e compare `INFO;Notifica ntfy: HTTP/1.1 200 OK`.
  Se anche `config.json` ha lo stesso canale arrivano due notifiche: una
  dal PC e una dall'Arduino.
- **Attenzione:** non condividete lo sketch con la password del WiFi.

---

## Sfida extra

Quando il volto autorizzato torna davanti a HuskyLens, l'allarme della
webcam dovrebbe fermarsi anche sull'Arduino? Oggi `app.py` sa mandare
`ALLARME` e lo sketch capisce anche `STOP`. Prova a far mandare `STOP`
quando nella pagina premi "Ferma allarme" (serve una nuova richiesta
al server: chiedi aiuto al formatore).
