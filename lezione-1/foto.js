// Modalità foto: l'antifurto SENZA webcam, ma con il modello vero.
//
// Apri la pagina con l'indirizzo  http://localhost:8000/?foto
// Al posto della webcam compare un riquadro in cui mettere una foto:
//   - con il pulsante "Scegli foto";
//   - trascinando un'immagine nel riquadro;
//   - copiando un'immagine (tasto destro > Copia immagine) e premendo Ctrl + V.
// Il modello di Teachable Machine analizza la foto come se fosse la webcam.
//
// Non c'è bisogno di modificare questo file.

const LATO_FOTO = 320;  // come la webcam: un quadrato di 320x320 pixel

// La foto mostrata in questo momento (null = nessuna foto).
let fotoAttuale = null;

function modalitaFoto() {
  return new URLSearchParams(window.location.search).has("foto");
}

// Una finta webcam con gli stessi "pezzi" di quella vera: canvas e update().
// Invece dei fotogrammi della telecamera disegna sempre la foto scelta.
function creaWebcamFoto() {
  const canvas = document.createElement("canvas");
  canvas.width = LATO_FOTO;
  canvas.height = LATO_FOTO;
  const disegno = canvas.getContext("2d");
  creaComandiFoto();
  return {
    canvas: canvas,
    update: function () {
      if (fotoAttuale === null) {
        disegnaRiquadroVuoto(disegno);
      } else {
        disegnaFotoQuadrata(disegno, fotoAttuale);
      }
    },
  };
}

// Quando non c'è nessuna foto il modello non deve "indovinare" niente
// (vedrebbe un riquadro scuro e potrebbe scambiarlo per un intruso):
// rispondiamo noi con 0% per tutte le classi, così non scatta niente.
function avvolgiModelloFoto(modelloVero) {
  return {
    getClassLabels: function () {
      return modelloVero.getClassLabels();
    },
    predict: async function (immagine) {
      if (fotoAttuale === null) {
        return modelloVero.getClassLabels().map(function (nome) {
          return { className: nome, probability: 0 };
        });
      }
      return modelloVero.predict(immagine);
    },
  };
}

function disegnaRiquadroVuoto(disegno) {
  disegno.fillStyle = "#1d2330";
  disegno.fillRect(0, 0, LATO_FOTO, LATO_FOTO);
  disegno.fillStyle = "white";
  disegno.textAlign = "center";
  disegno.font = "bold 22px sans-serif";
  disegno.fillText("Nessuna foto", LATO_FOTO / 2, 145);
  disegno.font = "16px sans-serif";
  disegno.fillText("Scegli, trascina qui", LATO_FOTO / 2, 180);
  disegno.fillText("o incolla (Ctrl + V) una foto", LATO_FOTO / 2, 205);
}

// Ritaglia il quadrato centrale della foto, come fa Teachable Machine:
// così una foto rettangolare non viene schiacciata.
function disegnaFotoQuadrata(disegno, foto) {
  const lato = Math.min(foto.width, foto.height);
  const x = (foto.width - lato) / 2;
  const y = (foto.height - lato) / 2;
  disegno.drawImage(foto, x, y, lato, lato, 0, 0, LATO_FOTO, LATO_FOTO);
}

// Trasforma un file immagine in una foto da disegnare.
function caricaFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    return;
  }
  const foto = new Image();
  foto.onload = function () {
    fotoAttuale = foto;
  };
  foto.src = URL.createObjectURL(file);
}

// Pulsanti "Scegli foto" e "Togli foto", trascinamento e Ctrl + V.
function creaComandiFoto() {
  const pulsanti = document.querySelector(".pulsanti");

  const scelta = document.createElement("input");
  scelta.type = "file";
  scelta.accept = "image/*";
  scelta.hidden = true;
  scelta.addEventListener("change", function () {
    caricaFile(scelta.files[0]);
    scelta.value = "";  // così si può scegliere di nuovo lo stesso file
  });

  const scegli = document.createElement("button");
  scegli.textContent = "Scegli foto";
  scegli.addEventListener("click", function () {
    scelta.click();
  });

  const togli = document.createElement("button");
  togli.textContent = "Togli foto";
  togli.className = "secondario";
  togli.addEventListener("click", function () {
    fotoAttuale = null;
  });

  pulsanti.append(scelta, scegli, togli);

  const riquadro = document.getElementById("webcam");
  riquadro.addEventListener("dragover", function (evento) {
    evento.preventDefault();  // serve per permettere il "drop"
  });
  riquadro.addEventListener("drop", function (evento) {
    evento.preventDefault();
    caricaFile(evento.dataTransfer.files[0]);
  });

  document.addEventListener("paste", function (evento) {
    for (const elemento of evento.clipboardData.items) {
      if (elemento.type.startsWith("image/")) {
        caricaFile(elemento.getAsFile());
        return;
      }
    }
  });
}
