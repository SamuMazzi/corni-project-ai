"""
Crea un eventi.csv di prova per la dashboard (strumento per il FORMATORE).

Utile all'inizio della lezione 3: gli studenti hanno subito dei dati da
mostrare in tabella, contatori e grafico, anche senza hardware.

Esempi:
    python tools/genera_eventi_prova.py lezione-3
    python tools/genera_eventi_prova.py lezione-3 --quanti 200 --giorni 7
    python tools/genera_eventi_prova.py lezione-3 --sovrascrivi

Usa solo la libreria standard. Il formato è lo stesso di app.py
(separatore ";", codifica UTF-8 con BOM per Excel).
"""

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

COLONNE_CSV = ["data_ora", "origine", "classe", "confidenza", "mail_inviata", "nota_mail"]

# Origini e classi possibili, con un "peso" (quanto spesso compaiono).
ORIGINI = [("webcam", 6), ("huskylens", 3), ("simulatore", 1)]
CLASSI_WEBCAM = [("intruso", 5), ("sasso", 2), ("forbice", 2)]


def scegli_pesato(coppie, casuale):
    valori = [valore for valore, _ in coppie]
    pesi = [peso for _, peso in coppie]
    return casuale.choices(valori, weights=pesi)[0]


def crea_evento(momento, casuale):
    origine = scegli_pesato(ORIGINI, casuale)
    if origine == "webcam":
        classe = scegli_pesato(CLASSI_WEBCAM, casuale)
        confidenza = f"{casuale.uniform(0.85, 0.99):.2f}"
    else:
        classe = f"intruso ID {casuale.choice([3, 4])}"
        confidenza = ""  # HuskyLens non dà la confidenza
    nota = scegli_pesato([("inviata", 3), ("cooldown", 5), ("prova", 2)], casuale)
    return {
        "data_ora": momento.strftime("%Y-%m-%d %H:%M:%S"),
        "origine": origine,
        "classe": classe,
        "confidenza": confidenza,
        "mail_inviata": "si" if nota == "inviata" else "no",
        "nota_mail": nota,
    }


def main():
    parser = argparse.ArgumentParser(description="Crea un eventi.csv di prova")
    parser.add_argument("cartella", help="cartella della lezione, es. lezione-3")
    parser.add_argument("--quanti", type=int, default=120, help="numero di eventi")
    parser.add_argument("--giorni", type=int, default=3, help="su quanti giorni distribuirli")
    parser.add_argument("--sovrascrivi", action="store_true",
                        help="sostituisce un eventi.csv già presente")
    argomenti = parser.parse_args()

    destinazione = Path(argomenti.cartella) / "eventi.csv"
    if destinazione.exists() and not argomenti.sovrascrivi:
        print(f"{destinazione} esiste già. Usa --sovrascrivi per sostituirlo.")
        sys.exit(1)

    casuale = random.Random(7)
    adesso = datetime.now()
    inizio = adesso - timedelta(days=argomenti.giorni)
    durata = (adesso - inizio).total_seconds()
    momenti = sorted(inizio + timedelta(seconds=casuale.uniform(0, durata))
                     for _ in range(argomenti.quanti))

    with open(destinazione, "w", newline="", encoding="utf-8-sig") as file:
        scrittore = csv.DictWriter(file, fieldnames=COLONNE_CSV, delimiter=";")
        scrittore.writeheader()
        for momento in momenti:
            scrittore.writerow(crea_evento(momento, casuale))
    print(f"Creati {argomenti.quanti} eventi in {destinazione}")


if __name__ == "__main__":
    main()
