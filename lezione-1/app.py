"""
Antifurto con intelligenza artificiale - server della LEZIONE 1

Avvio:      python app.py
Poi apri:   http://localhost:8000  (si apre da solo)
Per fermare il server: premi Ctrl + C nel terminale.

Cosa fa questo programma:
  1. serve i file della cartella (index.html, antifurto.js, ...) al browser;
  2. riceve gli allarmi dalla pagina (POST /api/allarme) e manda una mail;
  3. scrive ogni evento nel file eventi.csv;
  4. restituisce gli eventi in formato JSON (GET /api/eventi).

Usa solo la libreria standard di Python: non serve installare niente.
"""

import argparse
import csv
import json
import smtplib
import ssl
import sys
import threading
import time
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Impostazioni fisse
# ---------------------------------------------------------------------------

# La cartella in cui si trova questo file: tutti i percorsi partono da qui,
# così il programma funziona anche se lo avvii da un'altra cartella.
CARTELLA = Path(__file__).resolve().parent

FILE_CONFIG = CARTELLA / "config.json"
FILE_CONFIG_ESEMPIO = CARTELLA / "config.esempio.json"
FILE_EVENTI = CARTELLA / "eventi.csv"

# MISSIONE 8: cambia la porta del server, per esempio 8080. Poi nel
# browser dovrai usare http://localhost:8080
PORTA = 8000

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
        "gesto_disattivazione": scenario.get("gesto_disattivazione", ""),
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

    # MISSIONE 4: cambia l'oggetto e il testo della mail.
    # Puoi usare le variabili adesso, origine, classe e confidenza.
    # Suggerimento: la confidenza è un numero tra 0 e 1; per mostrarla in
    # percentuale scrivi f"{confidenza * 100:.0f}%".
    oggetto = "ALLARME antifurto"
    testo = (
        "Il sistema antifurto ha riconosciuto un intruso.\n"
        f"Classe: {classe}\n"
        f"Quando: {adesso}\n"
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

    # MISSIONE 9: per ora l'antifurto sorveglia sempre. Fai in modo che
    # restituisca True solo se ora è tra ORA_INIZIO_SORVEGLIANZA (compresa)
    # e ORA_FINE_SORVEGLIANZA (esclusa), e False altrimenti.
    # Suggerimento: in Python si può scrivere  a <= ora < b  e il risultato
    # è già True o False.
    return True


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
        # MISSIONE 10: adesso il riepilogo dice sempre 0. Conta gli eventi
        # di oggi!
        # 1. evento["data_ora"] è un testo come "2026-10-21 15:30:12": è di
        #    oggi se  evento["data_ora"].startswith(oggi)  è vero;
        # 2. se è di oggi, aumenta allarmi_oggi di 1:  allarmi_oggi += 1
        # 3. se in più evento["mail_inviata"] == "si", aumenta mail_oggi.
        # Al posto di "pass" scrivi un if. Attenzione agli spazi a inizio
        # riga: in Python decidono che cosa sta "dentro" l'if e il for.
        pass
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


def main():
    # Su alcuni terminali Windows le lettere accentate danno errore:
    # così, al peggio, vengono sostituite da un punto di domanda.
    sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Server dell'antifurto con IA")
    parser.add_argument("--senza-browser", action="store_true",
                        help="non aprire il browser all'avvio")
    argomenti = parser.parse_args()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORTA), Gestore)
    except OSError:
        print(f"Non riesco a usare la porta {PORTA}.")
        print("Forse app.py e' gia' aperto in un'altra finestra? Chiudila e riprova.")
        return

    indirizzo = f"http://localhost:{PORTA}"
    print(f"Antifurto avviato su {indirizzo}  (Ctrl + C per fermare)")
    # MISSIONE 8: personalizza il messaggio di benvenuto, per esempio con i
    # vostri nomi. Con f"..." puoi inserire variabili tra { }, come sopra.
    print("Benvenuti nell'antifurto con IA!")
    avvisa_sulla_config()
    if not argomenti.senza_browser:
        # Aspettiamo un secondo, così il server è pronto quando il browser chiede la pagina.
        threading.Timer(1.0, webbrowser.open, [indirizzo]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer fermato. Ciao!")


if __name__ == "__main__":
    main()
