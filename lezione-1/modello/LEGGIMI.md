# Cartella del modello

Qui c'è già il **modello del corso** (classi `Autorizzato` e `Intruso`,
l'animale autorizzato è il beagle): `config.esempio.json` lo usa con
`"modello": "modello/"`, quindi funziona anche senza collegarsi a
Teachable Machine.

Se non vuoi (o non puoi) usare il link "Upload my model" di Teachable
Machine, puoi mettere qui il modello esportato.

1. In Teachable Machine premi **Export Model**.
2. Scegli la scheda **Tensorflow.js** e l'opzione **Download**.
3. Si scarica uno ZIP: estrai qui dentro i tre file
   `model.json`, `metadata.json` e `weights.bin`.
4. In `config.json` scrivi `"modello": "modello/"` nello scenario che usi.

Puoi tenere più modelli in sottocartelle diverse, per esempio
`modello/gesti/` e `modello/animali/`, e scrivere in `config.json`
`"modello": "modello/gesti/"`.
