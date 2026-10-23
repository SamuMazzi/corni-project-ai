"""
Prepara i dataset per Teachable Machine (strumento per il FORMATORE).

Scarica un dataset pubblico da Hugging Face e crea delle cartelle di
immagini pronte da trascinare nelle classi di Teachable Machine.

Installazione (una volta sola):
    pip install -r tools/requirements.txt

Esempi:
    python tools/prepara_dataset.py razze
    python tools/prepara_dataset.py animali --razza beagle
    python tools/prepara_dataset.py animali --razza beagle --stessa-specie
    python tools/prepara_dataset.py gesti
    python tools/prepara_dataset.py gesti --per-classe 100 --uscita D:/dataset

Risultato (cartella "dataset" accanto a questo file, se non indichi --uscita):
    dataset/animali/autorizzato/     -> classe "autorizzato" in Teachable Machine
    dataset/animali/intruso/         -> classe "intruso"
    dataset/animali/trappole/        -> immagini difficili per mettere alla prova il modello
    dataset/animali/README.md        -> provenienza e licenze
    dataset/gesti/sasso|carta|forbice/, trappole/, README.md

La classe "nessuno" NON è qui: va registrata con la webcam puntata sul banco
vuoto (vedi docs/GUIDA_FORMATORE.md).

La prima esecuzione scarica circa 800 MB (animali) o 230 MB (gesti);
poi i file restano nella cache di Hugging Face.
"""

import argparse
import math
import random
import sys
from datetime import date
from pathlib import Path

try:
    from datasets import load_dataset
    from huggingface_hub import HfApi
    from PIL import ImageEnhance, ImageFilter
except ImportError:
    print("Mancano delle librerie. Installa con:  pip install -r tools/requirements.txt")
    sys.exit(1)

# ---------------------------------------------------------------------------
# I dataset usati e le loro licenze
# ---------------------------------------------------------------------------
#
# "licenza_fonte" è la licenza indicata dagli autori originali, controllata
# a mano (ottobre 2026). Lo script legge anche la licenza dichiarata su
# Hugging Face e le confronta nel README.

DATASET = {
    "animali": {
        "nome": "Oxford-IIIT Pet",
        "repo": "timm/oxford-iiit-pet",
        "fonte": "https://www.robots.ox.ac.uk/~vgg/data/pets/",
        "autori": "O. M. Parkhi, A. Vedaldi, A. Zisserman, C. V. Jawahar (2012)",
        "licenza_fonte": "cc-by-sa-4.0",
        "nota_licenza": (
            "Creative Commons Attribution-ShareAlike 4.0: si può usare e "
            "modificare citando gli autori; le opere derivate vanno "
            "condivise con la stessa licenza."
        ),
    },
    "gesti": {
        "nome": "Rock Paper Scissors",
        "repo": "Javtor/rock-paper-scissors",
        "fonte": "https://laurencemoroney.com/datasets.html",
        "autori": "Laurence Moroney",
        "licenza_fonte": "cc-by-2.0",
        "nota_licenza": (
            "Creative Commons Attribution 2.0: si può usare e modificare "
            "citando l'autore."
        ),
    },
}

# Nel dataset dei gesti le etichette sono numeri: 0 = paper, 1 = rock, 2 = scissors.
GESTI_ITALIANO = {"paper": "carta", "rock": "sasso", "scissors": "forbice"}

# Razze che si assomigliano: le usiamo come "trappole".
RAZZE_SIMILI = {
    "beagle": ["basset_hound", "english_cocker_spaniel"],
    "basset_hound": ["beagle"],
    "american_bulldog": ["american_pit_bull_terrier", "staffordshire_bull_terrier", "boxer"],
    "american_pit_bull_terrier": ["staffordshire_bull_terrier", "american_bulldog"],
    "staffordshire_bull_terrier": ["american_pit_bull_terrier", "american_bulldog"],
    "boxer": ["american_bulldog", "pug"],
    "samoyed": ["great_pyrenees", "keeshond"],
    "great_pyrenees": ["samoyed", "leonberger"],
    "leonberger": ["newfoundland", "saint_bernard"],
    "newfoundland": ["leonberger", "saint_bernard"],
    "saint_bernard": ["leonberger", "newfoundland"],
    "chihuahua": ["miniature_pinscher", "pomeranian"],
    "miniature_pinscher": ["chihuahua"],
    "pomeranian": ["keeshond", "chihuahua", "havanese"],
    "havanese": ["yorkshire_terrier", "japanese_chin"],
    "yorkshire_terrier": ["havanese", "scottish_terrier"],
    "scottish_terrier": ["wheaten_terrier", "yorkshire_terrier"],
    "wheaten_terrier": ["scottish_terrier", "havanese"],
    "shiba_inu": ["keeshond", "pomeranian"],
    "british_shorthair": ["russian_blue", "persian"],
    "russian_blue": ["british_shorthair", "bombay"],
    "bombay": ["russian_blue"],
    "persian": ["ragdoll", "birman", "maine_coon"],
    "ragdoll": ["birman", "persian"],
    "birman": ["ragdoll", "siamese"],
    "siamese": ["birman", "ragdoll"],
    "bengal": ["egyptian_mau", "abyssinian"],
    "egyptian_mau": ["bengal", "abyssinian"],
    "abyssinian": ["bengal", "egyptian_mau"],
    "maine_coon": ["persian", "ragdoll"],
    "sphynx": ["abyssinian", "egyptian_mau"],
}

# Quante immagini mettere in ogni cartella di trappole.
TRAPPOLE_PER_TIPO = 10

# Lato massimo delle immagini salvate: Teachable Machine le riduce comunque
# a 224 pixel, inutile tenerle enormi.
LATO_MASSIMO = 400

# Seme fisso: rilanciando lo script si ottengono le stesse immagini.
casuale = random.Random(42)


# ---------------------------------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------------------------------

def salva_immagine(immagine, percorso):
    """Salva un'immagine in JPEG, ridotta e in RGB."""
    immagine = immagine.convert("RGB")
    immagine.thumbnail((LATO_MASSIMO, LATO_MASSIMO))
    percorso.parent.mkdir(parents=True, exist_ok=True)
    immagine.save(percorso, "JPEG", quality=88)


def scurisci(immagine):
    return ImageEnhance.Brightness(immagine.convert("RGB")).enhance(0.25)


def sfoca(immagine):
    return immagine.convert("RGB").filter(ImageFilter.GaussianBlur(radius=4))


def salva_gruppo(dataset, indici, cartella, prefisso, trasforma=None):
    """Salva le immagini con gli indici dati in una cartella."""
    for numero, indice in enumerate(indici, start=1):
        immagine = dataset[indice]["image"]
        if trasforma:
            immagine = trasforma(immagine)
        salva_immagine(immagine, cartella / f"{prefisso}_{numero:03d}.jpg")
    print(f"  {len(indici):4d} immagini in {cartella}")


def indici_per_etichetta(dataset):
    """Restituisce {etichetta: [indici delle immagini con quell'etichetta]}.

    Leggere solo la colonna "label" è velocissimo: le immagini vere le
    apriamo dopo, solo quelle che servono.
    """
    gruppi = {}
    for indice, etichetta in enumerate(dataset["label"]):
        gruppi.setdefault(etichetta, []).append(indice)
    return gruppi


def scegli(lista, quanti):
    """Sceglie a caso al massimo "quanti" elementi dalla lista."""
    return casuale.sample(lista, min(quanti, len(lista)))


def licenza_su_hugging_face(repo):
    """Legge la licenza dichiarata nella scheda del dataset su Hugging Face."""
    try:
        info = HfApi().dataset_info(repo)
        dati = info.card_data.to_dict() if info.card_data else {}
        licenza = dati.get("license")
        if isinstance(licenza, list):
            licenza = ", ".join(licenza)
        return licenza or "non dichiarata"
    except Exception as errore:
        return f"non verificabile ({errore.__class__.__name__})"


def scrivi_readme(cartella, scenario, righe_extra):
    """Scrive il README con provenienza e licenza del dataset."""
    info = DATASET[scenario]
    licenza_hf = licenza_su_hugging_face(info["repo"])
    if licenza_hf == info["licenza_fonte"]:
        controllo = "coincide con la licenza della fonte originale"
    else:
        controllo = (
            "NON coincide o manca: vale la licenza della fonte originale, "
            "controllala sul sito degli autori prima di pubblicare"
        )
    testo = [
        f"# Dataset {scenario}: {info['nome']}",
        "",
        f"Preparato il {date.today().strftime('%d/%m/%Y')} con tools/prepara_dataset.py.",
        "",
        "## Provenienza e licenza",
        "",
        "| Voce | Valore |",
        "| --- | --- |",
        f"| Dataset | {info['nome']} |",
        f"| Autori | {info['autori']} |",
        f"| Fonte originale | {info['fonte']} |",
        f"| Copia su Hugging Face | https://huggingface.co/datasets/{info['repo']} |",
        f"| Licenza della fonte originale | {info['licenza_fonte']} |",
        f"| Licenza dichiarata su Hugging Face | {licenza_hf} ({controllo}) |",
        "",
        info["nota_licenza"],
        "",
        "Se mostri o condividi queste immagini, cita autori e fonte.",
        "",
        "## Contenuto",
        "",
    ] + righe_extra + [
        "",
        "## La classe \"nessuno\"",
        "",
        "Non è in questa cartella: in Teachable Machine creala con la webcam",
        "puntata sul banco vuoto (circa 100-200 immagini, spostando un po' la",
        "webcam e cambiando la luce). Mai inquadrare volti.",
        "",
    ]
    (cartella / "README.md").write_text("\n".join(testo), encoding="utf-8")
    print(f"  Licenza su Hugging Face: {licenza_hf} -> {controllo}")


# ---------------------------------------------------------------------------
# Scenario animali (Oxford-IIIT Pet)
# ---------------------------------------------------------------------------

def carica_animali():
    print("Scarico Oxford-IIIT Pet da Hugging Face (la prima volta ci vuole un po')...")
    addestramento = load_dataset(DATASET["animali"]["repo"], split="train")
    prova = load_dataset(DATASET["animali"]["repo"], split="test")
    return addestramento, prova


def elenca_razze():
    addestramento, _ = carica_animali()
    nomi = addestramento.features["label"].names
    specie = addestramento.features["label_cat_dog"].names
    # Per sapere se una razza è di gatti o cani guardiamo la prima immagine.
    prima_immagine = {}
    for etichetta, tipo in zip(addestramento["label"], addestramento["label_cat_dog"]):
        prima_immagine.setdefault(etichetta, specie[tipo])
    print("\nRazze disponibili (usa il nome con --razza):")
    for numero, nome in enumerate(nomi):
        print(f"  {nome:28s} {prima_immagine.get(numero, '?')}")


def prepara_animali(razza, per_classe, uscita, stessa_specie):
    addestramento, prova = carica_animali()
    nomi = addestramento.features["label"].names
    if razza not in nomi:
        print(f"Razza '{razza}' non trovata. Elenco: python tools/prepara_dataset.py razze")
        sys.exit(1)
    id_razza = nomi.index(razza)

    gruppi = indici_per_etichetta(addestramento)
    gruppi_prova = indici_per_etichetta(prova)

    # Specie di ogni razza (0 = gatto, 1 = cane), per l'opzione --stessa-specie.
    specie_razza = {}
    for etichetta, tipo in zip(addestramento["label"], addestramento["label_cat_dog"]):
        specie_razza.setdefault(etichetta, tipo)

    altre_razze = [r for r in gruppi if r != id_razza]
    if stessa_specie:
        altre_razze = [r for r in altre_razze if specie_razza[r] == specie_razza[id_razza]]

    # Autorizzato: immagini della razza scelta.
    autorizzati = scegli(gruppi[id_razza], per_classe)

    # Intrusi: lo STESSO numero di immagini, prese in parti uguali dalle
    # altre razze. Classi bilanciate = modello che non "preferisce" nessuno.
    quota = math.ceil(len(autorizzati) / len(altre_razze))
    intrusi = []
    for altra in altre_razze:
        intrusi += scegli(gruppi[altra], quota)
    casuale.shuffle(intrusi)
    intrusi = intrusi[:len(autorizzati)]

    cartella = Path(uscita) / "animali"
    print(f"\nCreo le cartelle in {cartella.resolve()}")
    salva_gruppo(addestramento, autorizzati, cartella / "autorizzato", razza)
    salva_gruppo(addestramento, intrusi, cartella / "intruso", "intruso")

    # Trappole: dallo split di prova, quindi immagini che il modello non ha
    # mai visto in addestramento.
    trappole = cartella / "trappole"
    simili = [nomi.index(r) for r in RAZZE_SIMILI.get(razza, []) if r in nomi]
    if not simili:
        stesse = [r for r in gruppi if r != id_razza and specie_razza[r] == specie_razza[id_razza]]
        simili = casuale.sample(stesse, min(3, len(stesse)))
    candidati_simili = [i for r in simili for i in gruppi_prova.get(r, [])]
    razza_prova = gruppi_prova[id_razza]

    salva_gruppo(prova, scegli(candidati_simili, TRAPPOLE_PER_TIPO),
                 trappole / "razze_simili", "simile")
    salva_gruppo(prova, scegli(razza_prova, TRAPPOLE_PER_TIPO),
                 trappole / "autorizzato_mai_visto", razza)
    salva_gruppo(prova, scegli(razza_prova, TRAPPOLE_PER_TIPO),
                 trappole / "scure", "scura", scurisci)
    salva_gruppo(prova, scegli(razza_prova, TRAPPOLE_PER_TIPO),
                 trappole / "sfocate", "sfocata", sfoca)

    nomi_simili = ", ".join(nomi[r] for r in simili)
    scrivi_readme(cartella, "animali", [
        f"- `autorizzato/`: {len(autorizzati)} immagini della razza **{razza}**.",
        f"- `intruso/`: {len(intrusi)} immagini di altre {len(altre_razze)} razze"
        + (" (solo stessa specie)" if stessa_specie else "") + ", in parti uguali.",
        "- `trappole/`: immagini MAI usate per l'addestramento, per mettere alla prova il modello:",
        f"  - `razze_simili/`: razze che assomigliano a {razza} ({nomi_simili});",
        f"  - `autorizzato_mai_visto/`: altre foto di {razza};",
        f"  - `scure/` e `sfocate/`: foto di {razza} rovinate apposta.",
    ])


# ---------------------------------------------------------------------------
# Scenario gesti (Rock Paper Scissors)
# ---------------------------------------------------------------------------

def prepara_gesti(per_classe, uscita):
    print("Scarico Rock Paper Scissors da Hugging Face...")
    addestramento = load_dataset(DATASET["gesti"]["repo"], split="train")
    prova = load_dataset(DATASET["gesti"]["repo"], split="test")
    nomi = addestramento.features["label"].names   # ["paper", "rock", "scissors"]

    gruppi = indici_per_etichetta(addestramento)
    gruppi_prova = indici_per_etichetta(prova)

    cartella = Path(uscita) / "gesti"
    print(f"\nCreo le cartelle in {cartella.resolve()}")
    righe = []
    for etichetta, nome_inglese in enumerate(nomi):
        italiano = GESTI_ITALIANO[nome_inglese]
        scelti = scegli(gruppi[etichetta], per_classe)
        salva_gruppo(addestramento, scelti, cartella / italiano, italiano)
        righe.append(f"- `{italiano}/`: {len(scelti)} immagini ({nome_inglese}).")

    # Trappole: immagini di prova scurite, sfocate e ruotate.
    tutte_prova = [i for indici in gruppi_prova.values() for i in indici]
    trappole = cartella / "trappole"
    salva_gruppo(prova, scegli(tutte_prova, TRAPPOLE_PER_TIPO), trappole / "scure", "scura", scurisci)
    salva_gruppo(prova, scegli(tutte_prova, TRAPPOLE_PER_TIPO), trappole / "sfocate", "sfocata", sfoca)
    salva_gruppo(prova, scegli(tutte_prova, TRAPPOLE_PER_TIPO), trappole / "ruotate", "ruotata",
                 lambda immagine: immagine.convert("RGB").rotate(90, expand=True))

    righe += [
        "- `trappole/`: immagini MAI usate per l'addestramento (scure, sfocate, ruotate).",
        "",
        "Attenzione: le mani di questo dataset sono generate al computer su",
        "sfondo bianco. Davanti a una webcam vera il modello può sbagliare:",
        "è un ottimo spunto per parlare di dati di addestramento diversi dalla",
        "realtà. Si può migliorare aggiungendo in Teachable Machine qualche",
        "esempio dalla webcam (SOLO mani, mai volti).",
    ]
    scrivi_readme(cartella, "gesti", righe)


# ---------------------------------------------------------------------------
# Avvio
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prepara i dataset per Teachable Machine")
    parser.add_argument("scenario", choices=["animali", "gesti", "razze"],
                        help="animali, gesti, oppure razze (per vedere l'elenco delle razze)")
    parser.add_argument("--razza", default="beagle",
                        help="razza autorizzata nello scenario animali (default: beagle)")
    parser.add_argument("--stessa-specie", action="store_true",
                        help="intrusi solo della stessa specie (più difficile)")
    parser.add_argument("--per-classe", type=int, default=100,
                        help="immagini per classe, al massimo (default: 100)")
    parser.add_argument("--uscita", default=str(Path(__file__).resolve().parent / "dataset"),
                        help="cartella in cui creare il dataset")
    argomenti = parser.parse_args()

    if argomenti.scenario == "razze":
        elenca_razze()
    elif argomenti.scenario == "animali":
        prepara_animali(argomenti.razza, argomenti.per_classe, argomenti.uscita,
                        argomenti.stessa_specie)
    else:
        prepara_gesti(argomenti.per_classe, argomenti.uscita)
    print("\nFatto.")


if __name__ == "__main__":
    main()
