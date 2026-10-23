# Missioni della lezione 1

Ogni missione ha un numero. Nel codice trovi un commento `MISSIONE N`
proprio nel punto in cui devi intervenire: cercalo con **Ctrl + F**.

Dopo ogni modifica:

- se hai cambiato un file `.js`, `.css` o `.html`: ricarica la pagina (F5);
- se hai cambiato `config.json`: ricarica la pagina (F5);
- se hai cambiato `app.py`: ferma il server (Ctrl + C) e riavvialo con
  `python app.py`.

Senza webcam apri `http://localhost:8000/?foto` e usa delle foto
(scegli un file, trascinalo o incollalo con Ctrl + V). Per provare le
missioni senza modello apri `http://localhost:8000/?simula` e usa i
pulsanti delle classi.

---

## Livello base

### Missione 1: la soglia di confidenza

- **Obiettivo:** decidere quanto deve essere "sicuro" il modello prima di
  far scattare l'allarme.
- **Dove:** `config.json`, campo `"soglia"` (il commento `MISSIONE 1` in
  `antifurto.js` mostra dove viene usata).
- **Suggerimento:** la soglia è un numero tra 0 e 1. Con 0.5 basta poco
  per far scattare l'allarme, con 0.99 quasi mai. Prova almeno tre valori.
- **Come verificare:** la soglia compare nella riga "Scenario" della
  pagina. Mostra al modello un'immagine "difficile" (per esempio una
  foto scura o un animale che somiglia al beagle) e guarda se l'allarme scatta o no con soglie diverse.

### Missione 2: il suono della sirena

- **Obiettivo:** creare una sirena tutta vostra.
- **Dove:** `antifurto.js`, costanti all'inizio del file (`MISSIONE 2`).
- **Suggerimento:** cambia `FREQUENZA_ALTA`, `FREQUENZA_BASSA`,
  `DURATA_NOTA_MS` e `TIPO_ONDA` (`"sine"`, `"square"`, `"sawtooth"`,
  `"triangle"`). Non superare 0.5 di `VOLUME`, per le orecchie di tutti.
- **Come verificare:** fai scattare l'allarme (anche con `?simula`) e
  ascolta.

### Missione 3: il colore dell'allarme

- **Obiettivo:** cambiare il colore dello schermo lampeggiante.
- **Dove:** `style.css`, variabile `--colore-allarme` (`MISSIONE 3`).
- **Suggerimento:** prova anche a cambiare la velocità del lampeggio:
  cerca `animation: lampeggia 0.5s` e cambia `0.5s`.
- **Come verificare:** fai scattare l'allarme e guarda lo schermo.

### Missione 4: il testo della mail

- **Obiettivo:** scrivere una mail di allarme più utile.
- **Dove:** `app.py`, funzione `componi_mail` (`MISSIONE 4`). È Python:
  modifica solo il testo tra virgolette e le righe indicate.
- **Suggerimento:** aggiungi la confidenza in percentuale
  (`f"{confidenza * 100:.0f}%"`) e l'origine dell'evento. Ogni riga del
  testo finisce con `\n`, che vuol dire "a capo".
- **Come verificare:** riavvia `app.py`, fai scattare l'allarme e leggi
  la mail (o il terminale, se sei in modalità prova).

---

## Livello intermedio

### Missione 5: il contatore degli intrusi

- **Obiettivo:** mostrare nella pagina quanti intrusi sono stati rilevati.
- **Dove:** `index.html` (dove mettere il numero), `antifurto.js` in due
  punti (la variabile e la funzione `avviaAllarme`). Cerca `MISSIONE 5`.
- **Suggerimento:**
  1. in `index.html` aggiungi `<p>Intrusi rilevati: <strong id="contatore">0</strong></p>`;
  2. in `antifurto.js` crea `let intrusi = 0;`;
  3. in `avviaAllarme` aumenta il numero (`intrusi = intrusi + 1;`) e
     scrivilo nella pagina con
     `document.getElementById("contatore").textContent = intrusi;`.
- **Come verificare:** il numero sale di 1 ogni volta che scatta un nuovo
  allarme (non a ogni fotogramma!).

### Missione 6: il ritardo prima dell'allarme

- **Obiettivo:** evitare i falsi allarmi. L'allarme deve scattare solo se
  l'intruso resta visibile **almeno 2 secondi di fila**.
- **Dove:** `antifurto.js`, funzione `valutaPredizioni` (`MISSIONE 6`).
- **Suggerimento:** ti serve una nuova variabile, per esempio
  `let intrusoVistoDa = 0;`, che ricorda **da quando** vedi l'intruso.
  - Quando vedi un intruso e `intrusoVistoDa` è 0, ci metti `Date.now()`.
  - Quando vedi una classe autorizzata (o il modello è incerto) la
    rimetti a 0.
  - L'allarme scatta solo se `Date.now() - intrusoVistoDa >= 2000`
    (sono millisecondi).
- **Come verificare:** con `?simula` clicca "intruso" e poi subito
  "nessuno": l'allarme non deve scattare. Se resti su "intruso" per più di
  2 secondi, invece, scatta.

---

## Livello avanzato

### Missione 7: la password a due gesti

- **Obiettivo:** nello scenario "gesti", l'allarme si disattiva solo con
  una sequenza: per esempio prima **forbice** e poi **sasso**, entro
  5 secondi. È una piccola **macchina a stati**.
- **Dove:** `antifurto.js`, funzione `valutaPredizioni` (`MISSIONE 7`).
  In `config.json` imposta `"scenario": "gesti"`.
- **Suggerimento:** disegna prima su carta gli stati:
  - stato 0: "aspetto il primo gesto";
  - stato 1: "ho visto forbice, aspetto sasso" (e ricordo quando è
    iniziato).

  Le transizioni:
  - in stato 0 vedo forbice: vado in stato 1 e salvo `Date.now()`;
  - in stato 1 vedo sasso entro 5 secondi: disattivo il sistema e torno
    allo stato 0;
  - in stato 1 passano più di 5 secondi: torno allo stato 0.

  Attenzione: il modello vede lo stesso gesto per molti fotogrammi di
  fila. Conviene reagire solo quando la classe **cambia** rispetto al
  fotogramma precedente. Se hai fatto la missione 6, ricorda che un gesto
  breve non fa scattare l'allarme: è proprio quello che ti serve!
- **Come verificare:** con `?simula` clicca forbice e poi sasso entro
  5 secondi: lo stato diventa "DISATTIVATO". Se aspetti più di 5 secondi
  tra i due gesti, o li fai al contrario, non deve succedere.
- **Sfida extra:** metti la sequenza in una lista
  (`const PASSWORD = ["forbice", "sasso", "carta"];`) così funziona con
  qualunque numero di gesti.

---

## Missioni Python

Non serve conoscere Python: il codice da toccare è piccolo e il commento
`MISSIONE N` in `app.py` spiega cosa scrivere. Dopo ogni modifica **ferma
il server (Ctrl + C) e riavvialo** con `python app.py`. Se il terminale
mostra un errore, leggi il numero di riga: di solito è un errore di
battitura o di spazi a inizio riga.

### Missione 8: il messaggio di avvio e la porta

- **Obiettivo:** prendere confidenza con `app.py`.
- **Dove:** `app.py`, costante `PORTA` e funzione `main` (`MISSIONE 8`).
- **Suggerimento:** cambia `PORTA = 8000` in `PORTA = 8080` e scrivi il
  messaggio di benvenuto che preferisci dentro `print("...")`. Con
  `print(f"...")` puoi inserire le variabili tra `{ }`, per esempio
  `{PORTA}`.
- **Come verificare:** all'avvio il terminale mostra il tuo messaggio e la
  pagina si apre su `http://localhost:8080`.

### Missione 9: l'orario di sorveglianza

- **Obiettivo:** di giorno, quando in laboratorio ci siete voi, le mail
  sono solo disturbo. L'antifurto deve mandare la mail solo in un certo
  orario (l'allarme suona e viene registrato comunque).
- **Dove:** `app.py`, costanti `ORA_INIZIO_SORVEGLIANZA` e
  `ORA_FINE_SORVEGLIANZA` in alto, funzione `in_orario_di_sorveglianza`
  (`MISSIONE 9`).
- **Suggerimento:** la funzione deve restituire `True` (sorveglia) o
  `False` (non sorveglia). In Python `8 <= ora < 13` è già `True` o
  `False`: basta scrivere `return` seguito dal confronto, usando le due
  costanti al posto dei numeri.
- **Come verificare:** imposta un orario che **non** comprende l'ora
  attuale, riavvia e fai scattare l'allarme: nella pagina compare "fuori
  dall'orario di sorveglianza". Poi rimetti 0 e 24.
- **Sfida extra:** un antifurto vero sorveglia di notte, per esempio dalle
  22 alle 6. Il tuo confronto funziona? Perché no? Come lo sistemi?
  (Indizio: `or`.)

### Missione 10: il riepilogo nel terminale

- **Obiettivo:** dopo ogni allarme il terminale stampa "Riepilogo di
  oggi: ... allarmi, ... mail inviate". Adesso dice sempre 0: fallo
  contare davvero.
- **Dove:** `app.py`, funzione `stampa_riepilogo` (`MISSIONE 10`).
- **Suggerimento:** il ciclo `for` passa già tutti gli eventi di
  `eventi.csv` uno alla volta. Al posto di `pass` scrivi un `if` che
  controlla se l'evento è di oggi e, se sì, aumenta il contatore. Il
  commento nel codice ti dà i pezzi da usare. Gli spazi a inizio riga
  devono essere multipli di 4.
- **Come verificare:** fai scattare due o tre allarmi (anche con
  `?simula`): il numero cresce. Confrontalo con le righe di `eventi.csv`.
- **Sfida extra:** conta anche quanti allarmi ci sono stati nell'ultima
  ora, oppure stampa la classe dell'evento più recente.
