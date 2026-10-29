"""
Antifurto con intelligenza artificiale - server della LEZIONE 2

Avvio senza Arduino:   python app.py
Avvio con Arduino:     python app.py --seriale COM3
Scegli la porta:       python app.py --seriale      (mostra l'elenco delle porte)
Per fermare il server: premi Ctrl + C nel terminale.

Cosa fa questo programma:
  1. serve i file della cartella (index.html, antifurto.js, ...) al browser;
  2. riceve gli allarmi dalla pagina (POST /api/allarme) e manda una mail;
  3. scrive ogni evento nel file eventi.csv;
  4. restituisce gli eventi in formato JSON (GET /api/eventi);
  5. NOVITA': parla con l'Arduino sulla porta seriale (USB).
     - Gli eventi dell'Arduino (HuskyLens) finiscono in mail e registro,
       proprio come quelli della webcam.
     - Quando scatta l'allarme della webcam, l'Arduino fa suonare il buzzer.

Usa la libreria standard di Python. Solo per l'Arduino serve pyserial:
    pip install pyserial
"""

import argparse
import csv
import json
import smtplib
import ssl
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# pyserial serve solo se usi l'Arduino. Se non è installato, il resto
# del programma funziona lo stesso.
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

# ---------------------------------------------------------------------------
# Impostazioni fisse
# ---------------------------------------------------------------------------

# La cartella in cui si trova questo file: tutti i percorsi partono da qui,
# così il programma funziona anche se lo avvii da un'altra cartella.
CARTELLA = Path(__file__).resolve().parent

FILE_CONFIG = CARTELLA / "config.json"
FILE_CONFIG_ESEMPIO = CARTELLA / "config.esempio.json"
FILE_EVENTI = CARTELLA / "eventi.csv"

PORTA = 8000

# Velocità della seriale: deve essere uguale a Serial.begin(...) nello sketch.
VELOCITA_SERIALE = 115200

# Colonne del file eventi.csv, nell'ordine in cui vengono scritte.
COLONNE_CSV = ["data_ora", "origine", "classe", "confidenza", "mail_inviata", "nota_mail"]

# Il separatore è il punto e virgola: così Excel in italiano apre il file
# già diviso in colonne.
SEPARATORE_CSV = ";"

# Orario in cui l'antifurto manda le mail (ore da 0 a 24, vedi la funzione
# in_orario_di_sorveglianza). Con 0 e 24 sorveglia sempre.
ORA_INIZIO_SORVEGLIANZA = 0
ORA_FINE_SORVEGLIANZA = 24

# Le richieste arrivano in parallelo (il server usa più thread). Il "lucchetto"
# impedisce che due allarmi scrivano nel CSV o controllino il cooldown insieme.
lucchetto = threading.Lock()

# Momento (in secondi) in cui è partita l'ultima mail: serve per il cooldown.
ultima_mail = 0.0

# La connessione con l'Arduino (None se non c'è) e il suo lucchetto per scrivere.
arduino = None
lucchetto_seriale = threading.Lock()


# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

def leggi_config():
    """Legge config.json. Se non esiste usa config.esempio.json.

    La rileggiamo a ogni richiesta: così se modifichi config.json non serve
    riavviare il server, basta ricaricare la pagina.
    """
    percorso = FILE_CONFIG if FILE_CONFIG.exists() else FILE_CONFIG_ESEMPIO
    # "utf-8-sig" accetta anche i file salvati dal Blocco note di Windows,
    # che a volte aggiunge un carattere invisibile all'inizio.
    with open(percorso, encoding="utf-8-sig") as file:
        return json.load(file)


def mail_configurata(config):
    """True se in config.json ci sono tutti i dati per mandare la mail."""
    mail = config.get("mail", {})
    campi = ["mittente", "password_app", "destinatario"]
    return all(str(mail.get(campo, "")).strip() for campo in campi)


def config_per_la_pagina():
    """Prepara le impostazioni da mandare al browser.

    ATTENZIONE: non mandiamo mai la sezione "mail", perché contiene la
    password. La pagina riceve solo quello che le serve.
    """
    config = leggi_config()
    nome_scenario = config.get("scenario", "animali")
    scenario = config.get(nome_scenario, {})
    return {
        "scenario": nome_scenario,
        "soglia": config.get("soglia", 0.85),
        "modello": scenario.get("modello", ""),
        "classi_autorizzate": scenario.get("classi_autorizzate", []),
        "password_gesti": scenario.get("password_gesti", ["forbice", "sasso"]),
        "secondi_password": scenario.get("secondi_password", 5),
        "secondi_disattivazione": scenario.get("secondi_disattivazione", 30),
        "cooldown_mail_secondi": config.get("cooldown_mail_secondi", 60),
        "modalita_prova": not mail_configurata(config),
    }


# ---------------------------------------------------------------------------
# Mail
# ---------------------------------------------------------------------------

def componi_mail(origine, classe, confidenza):
    """Prepara oggetto e testo della mail di allarme."""
    adesso = datetime.now().strftime("%d/%m/%Y alle %H:%M:%S")

    # Lezione 1, missione 4: un testo più completo.
    if confidenza is None:
        sicurezza = "non disponibile"
    else:
        sicurezza = f"{confidenza * 100:.0f}%"
    oggetto = f"ALLARME antifurto: {classe}"
    testo = (
        "Il sistema antifurto ha riconosciuto un intruso.\n"
        "\n"
        f"Classe riconosciuta: {classe}\n"
        f"Sicurezza del modello: {sicurezza}\n"
        f"Rilevato da: {origine}\n"
        f"Quando: {adesso}\n"
        "\n"
        "Messaggio automatico del laboratorio di Informatica.\n"
    )
    return oggetto, testo


def invia_mail(config, oggetto, testo):
    """Manda davvero la mail con Gmail (SMTP con SSL sulla porta 465).

    Se qualcosa va storto (rete bloccata, password sbagliata...) questa
    funzione solleva un'eccezione, che gestiamo in decidi_e_invia_mail.
    """
    mail = config["mail"]
    messaggio = EmailMessage()
    messaggio["Subject"] = oggetto
    messaggio["From"] = mail["mittente"]
    messaggio["To"] = mail["destinatario"]
    messaggio.set_content(testo)

    server = mail.get("server_smtp", "smtp.gmail.com")
    porta = int(mail.get("porta", 465))
    contesto = ssl.create_default_context()
    # timeout=10: se la rete della scuola blocca la posta, dopo 10 secondi
    # ci arrendiamo invece di restare bloccati per sempre.
    with smtplib.SMTP_SSL(server, porta, context=contesto, timeout=10) as smtp:
        # La password per le app di Gmail viene mostrata con degli spazi:
        # li togliamo noi, così funziona anche se la copi così com'è.
        smtp.login(mail["mittente"], mail["password_app"].replace(" ", ""))
        smtp.send_message(messaggio)


def stampa_mail_nel_terminale(oggetto, testo, motivo):
    """Modalità prova: invece di mandare la mail la mostriamo qui."""
    print()
    print("=" * 60)
    print(f"MODALITA' PROVA ({motivo})")
    print("La mail NON e' stata inviata. Ecco cosa avrebbe contenuto:")
    print(f"Oggetto: {oggetto}")
    print(testo)
    print("=" * 60)


def in_orario_di_sorveglianza():
    """True se in questo momento l'antifurto deve mandare le mail.

    Di giorno, quando in laboratorio ci siamo noi, le mail sarebbero solo
    disturbo: l'antifurto serve quando non c'è nessuno.
    """
    ora = datetime.now().hour  # un numero da 0 a 23

    # Lezione 1, missione 9.
    if ORA_INIZIO_SORVEGLIANZA <= ORA_FINE_SORVEGLIANZA:
        return ORA_INIZIO_SORVEGLIANZA <= ora < ORA_FINE_SORVEGLIANZA
    # Orario che passa la mezzanotte, per esempio dalle 22 alle 6.
    return ora >= ORA_INIZIO_SORVEGLIANZA or ora < ORA_FINE_SORVEGLIANZA


def decidi_e_invia_mail(config, origine, classe, confidenza):
    """Decide se mandare la mail (orario e cooldown) e la manda o la stampa.

    Restituisce un dizionario che la pagina usa per mostrare lo stato:
      esito = "inviata" | "cooldown" | "prova" | "fuori_orario"
    """
    global ultima_mail

    # Fuori dall'orario di sorveglianza l'evento finisce comunque nel
    # registro (lo fa gestisci_allarme), ma la mail no.
    if not in_orario_di_sorveglianza():
        return {
            "esito": "fuori_orario",
            "messaggio": "Mail non inviata: siamo fuori dall'orario di sorveglianza",
        }

    cooldown = float(config.get("cooldown_mail_secondi", 60))
    adesso = time.time()
    attesa = cooldown - (adesso - ultima_mail)

    # Cooldown: se è passato troppo poco tempo dall'ultima mail non ne
    # mandiamo un'altra, altrimenti la casella si riempie in un minuto.
    if attesa > 0:
        return {
            "esito": "cooldown",
            "messaggio": f"Mail non inviata: attendi ancora {attesa:.0f} secondi",
            "secondi_rimanenti": round(attesa),
        }

    ultima_mail = adesso
    oggetto, testo = componi_mail(origine, classe, confidenza)
    # La notifica sul telefono parte sempre, anche in modalità prova.
    invia_notifica(config, oggetto, testo)

    if not mail_configurata(config):
        motivo = "config.json mancante o senza dati della mail"
        stampa_mail_nel_terminale(oggetto, testo, motivo)
        return {"esito": "prova", "messaggio": f"Modalità prova: {motivo}"}

    try:
        invia_mail(config, oggetto, testo)
    except Exception as errore:
        # Qualunque errore: non ci fermiamo, passiamo alla modalità prova.
        motivo = f"invio fallito: {errore}"
        stampa_mail_nel_terminale(oggetto, testo, motivo)
        return {"esito": "prova", "messaggio": f"Modalità prova: {motivo}"}

    print(f"Mail inviata a {config['mail']['destinatario']}")
    return {"esito": "inviata", "messaggio": "Mail inviata"}


# ---------------------------------------------------------------------------
# Notifica sul telefono con ntfy (NOVITA' della lezione 2)
# ---------------------------------------------------------------------------
#
# ntfy (https://ntfy.sh) manda notifiche al telefono senza account: installi
# l'app "ntfy", ti iscrivi a un canale con un nome inventato e tutto quello
# che viene "pubblicato" su quel canale ti arriva come notifica.
# Chiunque conosca il nome del canale legge i messaggi: scegli un nome
# difficile da indovinare e non mandare mai dati personali.

def ntfy_configurato(config):
    """True se in config.json c'è il nome del canale ntfy."""
    return bool(str(config.get("ntfy", {}).get("canale", "")).strip())


def invia_notifica(config, oggetto, testo):
    """Manda la notifica al canale ntfy. Se non è configurato non fa niente.

    Se qualcosa va storto (rete bloccata...) lo scriviamo nel terminale e
    andiamo avanti: la notifica non deve mai fermare l'antifurto.
    """
    if not ntfy_configurato(config):
        return
    ntfy = config["ntfy"]
    # MISSIONE 5: personalizza la notifica.
    #   "priority": da 1 (minima, nessun suono) a 5 (urgente, vibra a lungo).
    #   "tags": nomi di emoji che compaiono accanto al titolo, per esempio
    #   ["rotating_light"] (sirena), ["warning"], ["dog"].
    #   L'elenco completo: https://docs.ntfy.sh/emojis/
    notifica = {
        "topic": ntfy["canale"].strip(),
        "title": oggetto,
        "message": testo,
        "priority": 3,
        "tags": [],
    }
    richiesta = urllib.request.Request(
        ntfy.get("server", "https://ntfy.sh"),
        data=json.dumps(notifica).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        # timeout=5: se la rete blocca ntfy non restiamo bloccati.
        urllib.request.urlopen(richiesta, timeout=5).close()
    except Exception as errore:
        print(f"Notifica ntfy NON inviata: {errore}")
        return
    print(f"Notifica inviata sul canale ntfy '{notifica['topic']}'")


# ---------------------------------------------------------------------------
# Registro degli eventi (eventi.csv)
# ---------------------------------------------------------------------------

def registra_evento(origine, classe, confidenza, esito_mail):
    """Aggiunge una riga in fondo a eventi.csv (lo crea se non esiste)."""
    nuovo_file = not FILE_EVENTI.exists()
    riga = {
        "data_ora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "origine": origine,
        "classe": classe,
        "confidenza": "" if confidenza is None else f"{confidenza:.2f}",
        "mail_inviata": "si" if esito_mail["esito"] == "inviata" else "no",
        "nota_mail": esito_mail["esito"],
    }
    # "a" = append: aggiunge in fondo senza cancellare le righe precedenti.
    with open(FILE_EVENTI, "a", newline="", encoding="utf-8-sig") as file:
        scrittore = csv.DictWriter(file, fieldnames=COLONNE_CSV, delimiter=SEPARATORE_CSV)
        if nuovo_file:
            scrittore.writeheader()
        scrittore.writerow(riga)
    print(f"[{riga['data_ora']}] EVENTO da {origine}: {classe} ({riga['confidenza']}) mail: {riga['nota_mail']}")


def leggi_eventi(ultimi=None):
    """Legge eventi.csv e restituisce una lista di dizionari."""
    if not FILE_EVENTI.exists():
        return []
    with open(FILE_EVENTI, newline="", encoding="utf-8-sig") as file:
        eventi = list(csv.DictReader(file, delimiter=SEPARATORE_CSV))
    for evento in eventi:
        # Nel CSV è tutto testo: trasformiamo la confidenza in numero.
        try:
            evento["confidenza"] = float(evento["confidenza"])
        except (TypeError, ValueError):
            evento["confidenza"] = None
    if ultimi:
        eventi = eventi[-ultimi:]
    return eventi


def stampa_riepilogo():
    """Stampa nel terminale quanti allarmi e quante mail ci sono stati oggi."""
    oggi = datetime.now().strftime("%Y-%m-%d")  # per esempio "2026-10-21"
    allarmi_oggi = 0
    mail_oggi = 0
    for evento in leggi_eventi():
        # Lezione 1, missione 10.
        if evento["data_ora"].startswith(oggi):
            allarmi_oggi += 1
            if evento["mail_inviata"] == "si":
                mail_oggi += 1
    print(f"Riepilogo di oggi: {allarmi_oggi} allarmi, {mail_oggi} mail inviate")


def gestisci_allarme(origine, classe, confidenza):
    """Il cuore del sistema: ogni allarme passa da qui, da dovunque arrivi."""
    config = leggi_config()
    with lucchetto:
        esito = decidi_e_invia_mail(config, origine, classe, confidenza)
        registra_evento(origine, classe, confidenza, esito)
        stampa_riepilogo()
    return esito


# ---------------------------------------------------------------------------
# Ponte seriale con l'Arduino
# ---------------------------------------------------------------------------
#
# L'Arduino e il PC si scambiano righe di testo, una per messaggio.
#
# Dall'Arduino al PC:
#   EVENTO;INTRUSO;ID=2;FONTE=HUSKYLENS       un intruso davanti a HuskyLens
#   EVENTO;AUTORIZZATO;ID=1;FONTE=HUSKYLENS   l'oggetto autorizzato
#   EVENTO;NESSUNO;FONTE=HUSKYLENS            non vede niente
#   INFO;qualunque testo                      messaggi da mostrare e basta
#
# Dal PC all'Arduino:
#   ALLARME                                   la webcam ha visto un intruso: suona!
#   (e tutto quello che scrivi nel terminale di app.py, per esempio INTRUSO)

def scegli_porta():
    """Mostra le porte seriali disponibili e chiede quale usare."""
    porte = list(serial.tools.list_ports.comports())
    if not porte:
        print("Nessuna porta seriale trovata: l'Arduino e' collegato con il cavo USB?")
        return None
    print("Porte seriali disponibili:")
    for numero, porta in enumerate(porte, start=1):
        print(f"  {numero}) {porta.device}  {porta.description}")
    scelta = input("Scrivi il numero della porta dell'Arduino (Invio = nessuna): ").strip()
    if scelta.isdigit() and 1 <= int(scelta) <= len(porte):
        return porte[int(scelta) - 1].device
    return None


def apri_seriale(porta):
    """Apre la porta seriale. Restituisce la connessione oppure None."""
    try:
        # timeout=1: readline() aspetta al massimo 1 secondo una riga.
        connessione = serial.Serial(porta, VELOCITA_SERIALE, timeout=1)
    except serial.SerialException as errore:
        print(f"Non riesco ad aprire {porta}: {errore}")
        print("Controlla che il Monitor seriale dell'IDE Arduino sia CHIUSO.")
        return None
    print(f"Arduino collegato su {porta}")
    return connessione


def interpreta_riga_seriale(riga):
    """Trasforma una riga dell'Arduino in un dizionario.

    Esempio: "EVENTO;INTRUSO;ID=2;FONTE=HUSKYLENS" diventa
    {"tipo": "EVENTO", "stato": "INTRUSO", "ID": "2", "FONTE": "HUSKYLENS"}
    """
    pezzi = riga.split(";")
    messaggio = {"tipo": pezzi[0], "stato": pezzi[1] if len(pezzi) > 1 else ""}
    for pezzo in pezzi[2:]:
        if "=" in pezzo:
            chiave, valore = pezzo.split("=", 1)
            messaggio[chiave] = valore
    return messaggio


def gestisci_messaggio_arduino(messaggio):
    """Decide cosa fare di un messaggio arrivato dall'Arduino."""
    if messaggio["tipo"] != "EVENTO":
        print(f"Arduino dice: {';'.join(messaggio.values())}")
        return

    # Solo gli intrusi diventano allarmi (mail + registro).
    if messaggio["stato"] != "INTRUSO":
        print(f"Arduino: {messaggio['stato']} (nessun allarme)")
        return

    # MISSIONE 4: ora l'origine è sempre "arduino". Usa il campo FONTE
    # (messaggio.get("FONTE", "arduino")) per scrivere nel registro se
    # l'evento viene da "huskylens" o dal "simulatore".
    # Suggerimento: .lower() trasforma il testo in minuscolo.
    origine = "arduino"

    classe = f"intruso ID {messaggio.get('ID', '?')}"
    # HuskyLens non dice quanto è sicuro: la confidenza resta vuota (None).
    gestisci_allarme(origine, classe, None)


def ascolta_arduino(porta):
    """Gira in un thread separato: legge le righe che arrivano dall'Arduino.

    Se il cavo si stacca, riprova a collegarsi ogni 3 secondi.
    """
    global arduino
    while True:
        if arduino is None:
            arduino = apri_seriale(porta)
            if arduino is None:
                time.sleep(3)
                continue
        try:
            riga = arduino.readline().decode("utf-8", errors="ignore").strip()
        except (serial.SerialException, OSError):
            print("Arduino scollegato! Riprovo tra 3 secondi...")
            arduino = None
            time.sleep(3)
            continue
        if riga:
            gestisci_messaggio_arduino(interpreta_riga_seriale(riga))


def invia_ad_arduino(comando):
    """Manda un comando (una riga di testo) all'Arduino, se è collegato."""
    if arduino is None:
        return
    with lucchetto_seriale:
        try:
            arduino.write((comando + "\n").encode("utf-8"))
        except (serial.SerialException, OSError):
            print("Non riesco a scrivere all'Arduino.")


def comandi_dal_terminale():
    """Gira in un thread separato: quello che scrivi nel terminale va all'Arduino.

    Utile senza pulsante: scrivi INTRUSO, AUTORIZZATO, NESSUNO, ID=3...
    """
    while True:
        try:
            comando = input().strip()
        except EOFError:
            return  # nessun terminale (per esempio app.py avviato da un altro programma)
        if comando:
            invia_ad_arduino(comando)


def avvia_ponte_seriale(porta):
    """Collega l'Arduino (se richiesto con --seriale) in un thread separato."""
    if serial is None:
        print("Per usare l'Arduino installa pyserial:  pip install pyserial")
        return
    if not porta:
        porta = scegli_porta()
    if not porta:
        print("Continuo senza Arduino.")
        return
    # daemon=True: il thread si chiude da solo quando chiudi il programma.
    threading.Thread(target=ascolta_arduino, args=(porta,), daemon=True).start()
    threading.Thread(target=comandi_dal_terminale, daemon=True).start()
    print("Puoi scrivere qui i comandi per l'Arduino (es. INTRUSO, ID=3) e premere Invio.")


# ---------------------------------------------------------------------------
# Server web
# ---------------------------------------------------------------------------

class Gestore(SimpleHTTPRequestHandler):
    """Risponde alle richieste del browser."""

    def __init__(self, *args, **kwargs):
        # directory=CARTELLA: serviamo i file di questa cartella.
        super().__init__(*args, directory=str(CARTELLA), **kwargs)

    def end_headers(self):
        # Diciamo al browser di non tenere copie vecchie dei file:
        # se modifichi antifurto.js basta ricaricare la pagina.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_request(self, code="-", size="-"):
        # Per non riempire il terminale mostriamo solo le richieste con errori.
        if str(code).isdigit() and int(code) >= 400:
            super().log_request(code, size)

    def rispondi_json(self, dati, codice=200):
        corpo = json.dumps(dati, ensure_ascii=False).encode("utf-8")
        self.send_response(codice)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def file_vietato(self):
        """True se il browser chiede config.json, che contiene la password."""
        percorso = Path(self.translate_path(self.path))
        return percorso.name.lower() == "config.json"

    def do_GET(self):
        indirizzo = urlparse(self.path)
        if indirizzo.path == "/api/config":
            self.rispondi_json(config_per_la_pagina())
        elif indirizzo.path == "/api/eventi":
            parametri = parse_qs(indirizzo.query)
            ultimi = parametri.get("ultimi", [""])[0]
            self.rispondi_json(leggi_eventi(int(ultimi) if ultimi.isdigit() else None))
        elif self.file_vietato():
            self.send_error(403, "config.json contiene la password: non lo mostriamo")
        else:
            super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/allarme":
            self.send_error(404)
            return
        try:
            lunghezza = int(self.headers.get("Content-Length", 0))
            evento = json.loads(self.rfile.read(lunghezza) or b"{}")
            classe = str(evento.get("classe", "sconosciuta"))
            origine = str(evento.get("origine", "webcam"))
            confidenza = evento.get("confidenza")
            confidenza = None if confidenza is None else float(confidenza)
        except (ValueError, TypeError, AttributeError):
            self.rispondi_json({"errore": "dati dell'evento non validi"}, 400)
            return
        # La pagina ha visto un intruso: facciamo suonare anche l'Arduino.
        invia_ad_arduino("ALLARME")
        self.rispondi_json(gestisci_allarme(origine, classe, confidenza))


# ---------------------------------------------------------------------------
# Avvio
# ---------------------------------------------------------------------------

def avvisa_sulla_config():
    """Stampa all'avvio in che modalità stiamo lavorando."""
    if not FILE_CONFIG.exists():
        print("ATTENZIONE: config.json non trovato, uso config.esempio.json.")
        print("Copia config.esempio.json in config.json e completalo.")
    if mail_configurata(leggi_config()):
        print("Mail: configurata (Gmail).")
    else:
        print("Mail: MODALITA' PROVA, le mail verranno stampate qui.")
    config = leggi_config()
    if ntfy_configurato(config):
        canale = config["ntfy"]["canale"].strip()
        print(f"Notifiche ntfy: canale '{canale}' (nell'app ntfy iscriviti a questo nome).")
    else:
        print("Notifiche ntfy: spente (scrivi il nome del canale in config.json).")


def main():
    # Su alcuni terminali Windows le lettere accentate danno errore:
    # così, al peggio, vengono sostituite da un punto di domanda.
    sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Server dell'antifurto con IA")
    parser.add_argument("--senza-browser", action="store_true",
                        help="non aprire il browser all'avvio")
    # nargs="?": puoi scrivere "--seriale COM3" oppure solo "--seriale"
    # (in quel caso const="" e ti mostriamo l'elenco delle porte).
    parser.add_argument("--seriale", nargs="?", const="", default=None,
                        metavar="PORTA", help="porta dell'Arduino, es. COM3")
    argomenti = parser.parse_args()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORTA), Gestore)
    except OSError:
        print(f"Non riesco a usare la porta {PORTA}.")
        print("Forse app.py e' gia' aperto in un'altra finestra? Chiudila e riprova.")
        return

    indirizzo = f"http://localhost:{PORTA}"
    print(f"Antifurto avviato su {indirizzo}  (Ctrl + C per fermare)")
    # Lezione 1, missione 8.
    print(f"Benvenuti nell'antifurto con IA! Sorveglianza dalle {ORA_INIZIO_SORVEGLIANZA} alle {ORA_FINE_SORVEGLIANZA}.")
    avvisa_sulla_config()
    if argomenti.seriale is not None:
        avvia_ponte_seriale(argomenti.seriale)
    if not argomenti.senza_browser:
        # Aspettiamo un secondo, così il server è pronto quando il browser chiede la pagina.
        threading.Timer(1.0, webbrowser.open, [indirizzo]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer fermato. Ciao!")


if __name__ == "__main__":
    main()
