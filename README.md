# Antifurto con intelligenza artificiale

Un progetto in 3 lezioni per costruire un antifurto che **riconosce** chi
è autorizzato e chi no, usando l'intelligenza artificiale:

1. **Lezione 1:** l'antifurto nel browser, con la webcam e un modello
   addestrato con Teachable Machine.
2. **Lezione 2:** l'antifurto esce dal computer: Arduino UNO R4 WiFi,
   HuskyLens, buzzer e matrice LED.
3. **Lezione 3:** la dashboard con tabelle, contatori e grafici.

Privacy prima di tutto: **non inquadriamo mai volti**. I modelli si
addestrano con immagini di animali (da un dataset pubblico), gesti della
mano e oggetti.

## Scaricare il progetto

1. In alto in questa pagina di GitHub premi il pulsante verde **Code**.
2. Scegli **Download ZIP**.
3. Estrai lo ZIP (tasto destro > *Estrai tutto*) in una cartella tua,
   per esempio sul Desktop.

## Cosa serve

- **Python 3.9 o più recente** (nel terminale: `python --version`).
- Un browser recente (Chrome o Edge) e una webcam.
- Solo dalla lezione 2: l'IDE Arduino e la libreria `pyserial`
  (`pip install pyserial`).

## Avviare l'antifurto

1. Apri la cartella della lezione del giorno, per esempio `lezione-1`.
2. Copia `config.esempio.json` e rinomina la copia in **`config.json`**.
3. Apri `config.json` e incolla il link del vostro modello di Teachable
   Machine nel campo `"modello"` (vedi sotto).
4. Apri un terminale **in quella cartella** (in Esplora file: clic sulla
   barra dell'indirizzo, scrivi `cmd` e premi Invio) e scrivi:

   ```
   python app.py
   ```

5. Si apre il browser su `http://localhost:8000`. Premi **Avvia** e
   consenti l'uso della webcam.

Per fermare il server: **Ctrl + C** nel terminale.

**Non hai la webcam?** Apri `http://localhost:8000/?foto`: il modello
analizza una foto invece del video. Premi **Scegli foto**, trascina
un'immagine nel riquadro oppure copiala dal web (tasto destro > *Copia
immagine*) e premi **Ctrl + V**.

**Non hai ancora un modello?** Apri `http://localhost:8000/?simula`: al
posto della webcam compaiono dei pulsanti per fingere di vedere ogni classe.

**La mail:** se `config.json` non ha i dati della mail (o la rete blocca
la posta), l'antifurto funziona lo stesso in **modalità prova**: la mail
viene stampata nel terminale invece di essere spedita. I dati della mail
del corso li dà il formatore. Non pubblicare mai `config.json`: contiene
una password.

## Il file config.json

| Campo | Cosa vuol dire |
| --- | --- |
| `scenario` | `"animali"` oppure `"gesti"` |
| `soglia` | quanto deve essere sicuro il modello (da 0 a 1) per far scattare l'allarme |
| `modello` | il link di Teachable Machine ("Upload my model") oppure `"modello/"` se hai scaricato i file nella cartella `modello` |
| `classi_autorizzate` | le classi che NON fanno scattare l'allarme. I nomi devono essere uguali a quelli di Teachable Machine |
| `gesto_disattivazione` | (scenario gesti, lezione 1) il gesto che disattiva l'allarme |
| `password_gesti` | (scenario gesti, dalla lezione 2) la sequenza di gesti che disattiva l'allarme |
| `secondi_disattivazione` | per quanti secondi il sistema resta disattivato |
| `mail` | i dati di Gmail (li completa il formatore) |
| `cooldown_mail_secondi` | tempo minimo tra due mail |

**I due scenari:**

- **animali**: classi `autorizzato`, `intruso`, `nessuno`. L'animale "di
  casa" è autorizzato, gli altri sono intrusi.
- **gesti**: classi `sasso`, `carta`, `forbice`, `nessuno`. Il gesto giusto
  disattiva l'allarme, gli altri lo fanno scattare.

## Cosa c'è in ogni cartella

```
lezione-1/                 antifurto nel browser
  app.py                   il server: pagine, mail, registro eventi
  index.html               la pagina dell'antifurto
  antifurto.js             il codice della pagina (webcam, modello, allarme)
  simulatore.js            i pulsanti di ?simula (non serve modificarlo)
  foto.js                  la modalità ?foto, senza webcam (non serve modificarlo)
  style.css                l'aspetto della pagina
  config.esempio.json      modello di config.json
  modello/                 dove mettere il modello scaricato (facoltativo)
  MISSIONI.md              le missioni della lezione
  COME_FUNZIONA.md         spiegazione di app.py e antifurto.js

lezione-2/                 come lezione-1 (completa) + Arduino e HuskyLens
  arduino/antifurto_huskylens/        sketch con HuskyLens
  arduino/antifurto_senza_huskylens/  sketch con un pulsante al posto di HuskyLens
  requirements.txt                    pyserial

lezione-3/                 come lezione-2 (completa) + dashboard
  dashboard.html, dashboard.js, dashboard.css

```

Ogni cartella `lezione-N` funziona da sola e parte dalla versione completa
della lezione precedente. `app.py` crea, durante l'uso, il file
`eventi.csv` con tutti gli allarmi (si apre anche con Excel).

## Con l'Arduino (lezione 2 e 3)

```
pip install pyserial
python app.py --seriale COM3
```

Al posto di `COM3` metti la porta del tuo Arduino. Se non la sai, scrivi
solo `python app.py --seriale` e scegli dall'elenco. Prima di avviare
`app.py` chiudi il Monitor seriale dell'IDE Arduino.

## Problemi?

- **"python" non è riconosciuto**: prova `py app.py`.
- **Porta 8000 occupata**: `app.py` è già aperto in un'altra finestra.
- **Modello non trovato**: controlla il link in `config.json` (deve finire
  con `/`).
- **La webcam non parte**: controlla il permesso del browser (icona a
  sinistra dell'indirizzo) e che nessun altro programma la stia usando.
