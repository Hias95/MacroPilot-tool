# Hosting ohne laufende Kosten (Phase D2)

## Empfehlung: statischer Export auf GitHub Pages

Ein Backend, das rund um die Uhr laeuft, kostet entweder Geld oder schlaeft nach Minuten ein (Render, Koyeb) und
braucht dann eine Minute zum Aufwachen. MacroPilot braucht das nicht: die Daten aendern sich taeglich, das Modell
rechnet woechentlich. Deshalb laeuft das Backend einmal am Tag in GitHub Actions, schreibt alles als JSON, und die
Seite ist eine reine statische Next.js-Seite. Kein Server, kein Schlafen, keine Kosten, keine Kaltstarts.

Was der taegliche Lauf tut (`.github/workflows/daily.yml`, 07:40 MESZ, auch von Hand startbar):

1. Quellen laden (FRED, Yahoo, CBOE, Shiller, Treasury), Verlauf rechnen, Tagesbild speichern.
2. Wechsel erkennen (Zone, Phase, Regime-Flags, Marktbestaetigung, Vetos) und per ntfy oder E-Mail melden.
3. `dashboard.json`, `history.json`, `changes.json`, `snapshots.json`, `backtest.json`, `data-quality.json`,
   `explanations.json`, `meta.json` nach `frontend/public/data` schreiben.
4. Zustand (Tagesbilder, Ereignisse) nach `data/state.json` sichern und committen.
5. Frontend statisch bauen (`frontend/.next-static`) und auf GitHub Pages veroeffentlichen.

## Einrichtung (einmalig, etwa 15 Minuten)

1. **Repository anlegen.** Auf github.com ein neues, privates oder oeffentliches Repository erstellen. Lokal im
   Projektordner (`frontend/.git` stammt von create-next-app und muss vorher weg, sonst wird `frontend` zum
   Untermodul):

   ```bash
   rm -r frontend/.git
   git init -b main
   git add .
   git commit -m "MacroPilot"
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin main
   ```

   `.gitignore` haelt `backend/.env`, `backend/data/` und `frontend/public/data/` draussen. Der FRED-Key kommt
   als Secret in GitHub, nie ins Repository.

2. **GitHub Pages einschalten.** Repository, Settings, Pages, Source: "GitHub Actions".

3. **Secrets und Variablen** (Settings, Secrets and variables, Actions):
   - Secret `FRED_API_KEY` (optional, sonst CSV-Export von FRED; empfohlen).
   - Secret `NTFY_TOPIC` fuer Push-Hinweise (siehe unten), optional `SMTP_*` und `ALERT_EMAIL_*` fuer E-Mail.
   - Secret `GEMINI_API_KEY` (optional): dann schreibt Gemini die Erklaerungen im Export; ohne Key regelbasiert.
     Das Gratis-Kontingent von Google AI Studio reicht fuer sechs Texte am Tag; die Pro-Abos decken die API nicht.
   - Variable `BASE_PATH` = `/<repo>` (nur wenn die Seite unter `https://<user>.github.io/<repo>/` liegt; bei
     einer eigenen Domain oder `<user>.github.io` leer lassen).

4. **Ersten Lauf starten.** Actions, "MacroPilot taeglich", "Run workflow". Danach steht die Seite unter der
   Pages-Adresse. Der Zustand beginnt mit diesem Tag; Wechsel gibt es ab dem zweiten Lauf.

## Alternative: Vercel

Vercel Hobby ist ebenfalls kostenlos und baut bei jedem Push. Dafuer im Vercel-Projekt Root Directory `frontend`,
Environment `NEXT_PUBLIC_DATA_MODE=static`, `NEXT_PUBLIC_DATA_URL=/data` setzen und im Workflow den Schritt
"Frontend statisch bauen" plus `deploy` weglassen; stattdessen muss der Lauf `frontend/public/data` committen
(Zeile `git add data/state.json` um `frontend/public/data` ergaenzen und den Ordner aus `.gitignore` nehmen).
GitHub Pages ist einfacher, weil alles in einem Konto bleibt.

## Hinweise bei Regimewechsel (D3)

- **ntfy** (empfohlen, kostenlos, kein Konto): App "ntfy" installieren (Android, iOS) oder ntfy.sh im Browser
  oeffnen, ein Thema abonnieren, etwa `macropilot-k7f2q9x1` (lang und zufaellig: das Thema ist das Passwort).
  Denselben Namen als `NTFY_TOPIC` eintragen (lokal in `backend/.env`, im Hosting als Secret).
- **E-Mail**: eigener SMTP-Zugang, etwa Gmail mit App-Passwort (`SMTP_HOST=smtp.gmail.com`, Port 587).
- Lokal meldet die API beim taeglichen Refresh (07:30, `REFRESH_HOUR`), im Hosting der Workflow. Was gemeldet
  wurde, steht auch im Dashboard unter "Was hat sich geaendert?" (`/api/v1/changes`).

## Statischen Export lokal pruefen

```bash
cd backend && .venv/Scripts/python.exe -m app.export --out ../frontend/public/data --state ../data/state.json --no-explanations
cd ../frontend && NEXT_PUBLIC_DATA_MODE=static npm run build
node scripts/serve-static.mjs 3100 .next-static
```

Dann http://localhost:3100 oeffnen (im Desktop-Vorschau-Tool: Konfiguration "static"). Unter Git Bash auf Windows
`NEXT_PUBLIC_DATA_URL` nicht setzen: die Shell wandelt `/data` in einen Windows-Pfad um; der Standard im Code ist
bereits `/data`.

## Lokal weiter wie bisher

Lokal laeuft FastAPI mit Persistenz: Rohdaten liegen in `backend/data/macropilot.sqlite`, ein Neustart braucht
kein Netz, ein Netzausfall faellt auf die Platte zurueck. Der Refresh laeuft taeglich im Hintergrund oder per
`POST /api/v1/refresh` (Header `X-Refresh-Token`, wenn `REFRESH_TOKEN` gesetzt ist).
