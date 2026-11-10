# Missioni della lezione 3

In questa lezione costruiamo la **dashboard**: una pagina che mostra a colpo
d'occhio cosa è successo, leggendo gli eventi dal server.

- Avvia `python app.py` (con `--seriale COM3` se hai l'Arduino).
- Apri `http://localhost:8000/dashboard.html` (c'è anche il link in alto
  nella pagina dell'antifurto).
- Tutto il lavoro si fa in `dashboard.js` (e un po' in `dashboard.html`):
  cerca i commenti `MISSIONE N`.
- Dopo ogni modifica ricarica la pagina con F5.

**Servono degli eventi!** Fai scattare qualche allarme (anche con
`http://localhost:8000/?simula` oppure con il pulsante dell'Arduino),
oppure chiedi al formatore il file di eventi di prova.

Per vedere com'è fatto un evento guarda in fondo alla dashboard il riquadro
"Ultimo evento ricevuto", oppure apri `http://localhost:8000/api/eventi`.

Il codice dell'antifurto e degli sketch è la versione completa della
lezione 2: le soluzioni sono segnate con commenti `Lezione 2, missione N`.

---

## Livello base

### Missione 1: la tabella degli ultimi eventi

- **Obiettivo:** una tabella con gli ultimi 20 eventi, il più recente in
  alto.
- **Dove:** `dashboard.js`, funzione `disegnaTabella`.
- **Suggerimento:** `eventi.slice(-20).reverse()` prende gli ultimi 20 e li
  gira. Per ogni evento crea una riga:
  ```js
  const riga = document.createElement("tr");
  riga.innerHTML = "<td>" + evento.data_ora + "</td><td>" + ... + "</td>";
  ```
  Prima di aggiungere le righe svuota il corpo della tabella con
  `tbody.innerHTML = "";`. Per la confidenza: se è `null` scrivi `-`,
  altrimenti `Math.round(evento.confidenza * 100) + "%"`.
- **Come verificare:** fai scattare un allarme: dopo pochi secondi la nuova
  riga compare in cima, senza ricaricare la pagina.

### Missione 2: lo stato del sistema

- **Obiettivo:** un riquadro grande che dice **ATTIVO** (verde) o
  **ALLARME** (rosso) se c'è stato un evento negli ultimi 30 secondi.
- **Dove:** `dashboard.js`, funzione `mostraStato`.
- **Suggerimento:**
  ```js
  const ultimo = eventi[eventi.length - 1];
  const secondi = (Date.now() - leggiData(ultimo).getTime()) / 1000;
  ```
  Attenzione al caso in cui non ci sono eventi (`eventi.length === 0`).
  Per il colore usa le classi CSS già pronte: `stato-grande` e
  `stato-grande allarme`.
- **Come verificare:** fai scattare un allarme: il riquadro diventa rosso e
  torna verde dopo circa 30 secondi.

---

## Livello intermedio

### Missione 3: i contatori per classe

- **Obiettivo:** un riquadro per ogni classe con il numero di eventi
  (es. "12 intruso", "3 intruso ID 2").
- **Dove:** `dashboard.js`, funzione `aggiornaContatori`.
- **Suggerimento:** un oggetto usato come "contachilometri":
  ```js
  const conteggi = {};
  for (const evento of eventi) {
    conteggi[evento.classe] = (conteggi[evento.classe] || 0) + 1;
  }
  ```
  Poi per ogni chiave di `conteggi` crea un
  `<div class="contatore"><span class="numero">12</span>intruso</div>`.
- **Come verificare:** i numeri sommati devono fare il totale di "Eventi
  mostrati".

### Missione 4: il grafico degli eventi nel tempo

- **Obiettivo:** un grafico a barre con il numero di eventi per ogni ora,
  fatto con **Chart.js** (già caricato nella pagina).
- **Dove:** `dashboard.js`, funzione `aggiornaGrafico`.
- **Suggerimento:** raggruppa con lo stesso trucco della missione 3, usando
  come chiave `evento.data_ora.slice(0, 13)` (data e ora, senza minuti).
  Il grafico va creato **una volta sola**: se `grafico` è `null` crealo
  con `new Chart(...)`, altrimenti aggiorna
  `grafico.data.labels`, `grafico.data.datasets[0].data` e chiama
  `grafico.update()`. Nel commento della funzione trovi il codice per
  crearlo.
- **Come verificare:** fai scattare qualche allarme: la barra dell'ora
  attuale cresce.

---

## Livello avanzato

### Missione 5: i filtri

- **Obiettivo:** far funzionare i due menu "Origine" e "Periodo": tabella,
  contatori e grafico mostrano solo gli eventi scelti.
- **Dove:** `dashboard.js`, funzione `applicaFiltri`.
- **Suggerimento:**
  ```js
  const origine = document.getElementById("filtro-origine").value;
  return eventi.filter(function (evento) {
    return origine === "tutte" || evento.origine === origine;
  });
  ```
  Per il periodo calcola il momento di inizio in millisecondi:
  ultima ora = `Date.now() - 60 * 60 * 1000`; oggi = mezzanotte di oggi
  (`new Date()` e poi `.setHours(0, 0, 0, 0)`); settimana = 7 giorni fa.
  Un evento passa il filtro se `leggiData(evento).getTime() >= inizio`.
- **Come verificare:** scegli "huskylens": restano solo gli eventi
  dell'Arduino e il numero "Eventi mostrati" scende.

### Missione 6: esportare in CSV

- **Obiettivo:** il pulsante "Esporta CSV" scarica un file con gli eventi
  **filtrati**, da aprire con Excel.
- **Dove:** `dashboard.js`, funzione `esportaCSV`.
- **Suggerimento:** costruisci il testo riga per riga, con i valori
  separati da `;` (Excel in italiano lo apre già diviso in colonne) e le
  righe separate da `"\n"`. Nel commento della funzione trovi il codice per
  far partire il download. Togli l'`alert`!
- **Come verificare:** scegli un filtro, premi il pulsante e apri il file:
  deve contenere solo le righe filtrate.

---

## Sfida extra

- Colora in rosso le righe della tabella con mail non inviata.
- Nel grafico, una serie di barre per ogni origine (webcam, huskylens...).
- Mostra da quanti minuti non arriva un evento ("tutto tranquillo da 12
  minuti").
