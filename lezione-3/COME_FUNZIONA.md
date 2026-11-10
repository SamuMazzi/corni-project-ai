# Come funziona l'antifurto

Il progetto ha **due programmi** che parlano tra loro:

```
   BROWSER (antifurto.js)                    PC (app.py)
 ┌─────────────────────────┐            ┌──────────────────────┐
 │ webcam -> modello IA    │   "ALLARME!"│ manda la mail        │
 │ decide: intruso o no?   │ ──────────> │ scrive eventi.csv    │
 │ sirena, schermo rosso   │ <────────── │ risponde "mail ok"   │
 └─────────────────────────┘  risposta   └──────────────────────┘
```

- **antifurto.js** (JavaScript) gira **nel browser**: guarda la webcam,
  chiede al modello cosa vede e decide se far scattare l'allarme.
- **app.py** (Python) gira **nel terminale**: è il "server". Dà al
  browser le pagine, manda la mail e tiene il registro degli eventi.

Perché due programmi? Il browser non può mandare mail né scrivere file sul
PC (per sicurezza). Il server sì, ma non vede la webcam. Così ognuno fa la
sua parte.

---

## Se conosci C o Java

Non devi imparare due linguaggi nuovi: devi solo **leggerli**. Quasi tutto
è uguale a quello che conosci già.

| Cosa | C / Java | JavaScript | Python |
| --- | --- | --- | --- |
| Variabile | `int x = 5;` | `let x = 5;` | `x = 5` |
| Costante | `final int X = 5;` | `const X = 5;` | `X = 5` (maiuscolo per convenzione) |
| Funzione | `void f(int a) { ... }` | `function f(a) { ... }` | `def f(a):` |
| Blocchi | `{ ... }` | `{ ... }` | **i rientri** (4 spazi) |
| If | `if (a > b) { ... }` | `if (a > b) { ... }` | `if a > b:` |
| E / oppure / non | `&&` `\|\|` `!` | `&&` `\|\|` `!` | `and` `or` `not` |
| Vero / falso | `true` `false` | `true` `false` | `True` `False` |
| "Niente" | `null` | `null` | `None` |
| Stampa | `printf` / `System.out.println` | `console.log(...)` | `print(...)` |
| Commento | `// ...` | `// ...` | `# ...` |
| Fine istruzione | `;` | `;` | niente |

Le differenze principali:

- **Niente tipi.** Non si scrive `int` o `String`: la variabile prende il
  tipo del valore che ci metti.
- **In Python i rientri contano.** Non ci sono graffe: quello che è
  "dentro" un `if` o una funzione è spostato a destra di 4 spazi. Se
  sbagli gli spazi, il programma non parte.
- **Liste e dizionari.** `[1, 2, 3]` è una lista (come un array).
  `{"classe": "intruso", "confidenza": 0.9}` è un dizionario (JavaScript
  lo chiama oggetto): coppie nome/valore, come una piccola struct.
- **Testi con variabili dentro.** In Python `f"Classe: {classe}"` mette
  il valore di `classe` nel testo. In JavaScript si usa
  `"Classe: " + classe`.

---

## antifurto.js: il programma nel browser

Si legge dall'alto in basso in quattro parti.

**1. Le impostazioni** (inizio del file). Costanti come `FREQUENZA_ALTA`
o `VOLUME` e variabili come `allarmeAttivo`. Qui si fanno le prime
missioni.

**2. L'avvio: `avvia()`.** Parte quando premi il pulsante **Avvia**:

1. chiede le impostazioni al server (`leggiConfig`);
2. scarica il modello di Teachable Machine (`caricaModello`);
3. accende la webcam (`accendiWebcam`);
4. fa partire il ciclo.

Vedrai la parola `await`: vuol dire "aspetta che questa operazione
finisca" (scaricare un file o accendere la webcam richiede tempo).

Senza webcam si usa `?foto` (file `foto.js`): al posto della telecamera
c'è una foto, ma il resto del programma è identico.

**3. Il ciclo: `ciclo()`.** È come il `loop()` di Arduino o un
`while (true)`: si ripete circa 30 volte al secondo.

```js
async function ciclo() {
  webcam.update();                                   // nuovo fotogramma
  const predizioni = await modello.predict(webcam.canvas);  // cosa vedi?
  aggiornaBarre(predizioni);                         // disegna le barre
  valutaPredizioni(predizioni);                      // intruso o no?
  ...
  requestAnimationFrame(ciclo);                      // e si ricomincia
}
```

`predizioni` è una lista con una probabilità per ogni classe, per esempio
autorizzato 0.05, intruso 0.93, nessuno 0.02.

**4. La decisione: `valutaPredizioni()`.** È il cervello dell'antifurto.
Prende la classe più probabile e controlla, in ordine:

1. è sotto la **soglia**? Il modello è incerto: non fare niente;
2. è una **classe autorizzata**? Tutto tranquillo;
3. altrimenti è un **intruso**: `avviaAllarme()`.

`avviaAllarme()` accende la sirena, colora lo schermo di rosso e avvisa il
server con `inviaAllarmeAlServer()`.

---

## app.py: il programma nel terminale

Il server **aspetta richieste** dal browser e risponde. Le funzioni da
conoscere:

| Funzione | Cosa fa |
| --- | --- |
| `main()` | parte quando scrivi `python app.py`: accende il server e apre il browser |
| `leggi_config()` | legge `config.json` |
| `gestisci_allarme()` | **il cuore**: ogni allarme passa da qui |
| `decidi_e_invia_mail()` | decide se mandare la mail (cooldown) e la manda |
| `componi_mail()` | prepara il testo della mail (missione 4) |
| `registra_evento()` | aggiunge una riga in `eventi.csv` |

Il server capisce tre "indirizzi" (si chiamano **API**):

- `GET /api/config`: il browser chiede le impostazioni;
- `POST /api/allarme`: il browser dice "ho visto un intruso!";
- `GET /api/eventi`: chi vuole legge il registro (lo userà la dashboard
  della lezione 3). Provalo: apri `http://localhost:8000/api/eventi`.

---

## Il viaggio di un allarme

1. La webcam vede un gatto (ma l'animale di casa è il beagle).
2. `ciclo()` chiede al modello: risposta "intruso, 93%".
3. `valutaPredizioni()`: 93% è sopra la soglia e "intruso" non è
   autorizzato, quindi chiama `avviaAllarme()`.
4. Sirena e schermo rosso. `inviaAllarmeAlServer()` manda al server:
   `{"classe": "intruso", "confidenza": 0.93, "origine": "webcam"}`.
5. In `app.py`, `gestisci_allarme()` controlla il cooldown, chiama
   `componi_mail()` e manda la mail (o la stampa nel terminale in
   modalità prova). Poi `registra_evento()` scrive in `eventi.csv`.
6. Il server risponde "mail inviata" e la pagina lo mostra.

---

## Consigli per non perdersi

- Usa **Ctrl + F** per cercare un nome di funzione o `MISSIONE`.
- Non serve capire ogni riga: leggi i **nomi delle funzioni** e i
  **commenti**, raccontano già quasi tutto.
- Se la pagina non funziona, premi **F12** e guarda la scheda
  **Console**: gli errori di JavaScript compaiono lì, con il numero di
  riga.
- Se `app.py` non parte, leggi l'ultima riga dell'errore nel terminale:
  dice il file, la riga e cosa non va.
