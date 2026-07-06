# Melde-Worker (Cloudflare Worker)

Nimmt Meldungen aus dem "Fehler melden"-Formular auf der Cinema-Atlas-Seite entgegen
und legt daraus automatisch ein **GitHub Issue** in diesem Repo an. Es wird dabei
**nichts automatisch in `cinema-data.js` übernommen** — du siehst das Issue, prüfst
es und trägst die Korrektur wie gewohnt über `cinema_extra_de.csv` / `update.py` /
`corrections.json` ein (siehe `anleitung.html`, Abschnitte 6 und 9).

Ohne diesen Worker läuft die Seite trotzdem ganz normal — nur der Melde-Button zeigt
dann einen Hinweis, dass die Funktion noch nicht eingerichtet ist.

## 1) GitHub-Token erstellen (einmalig)

Ein **Fine-grained Personal Access Token**, das **nur** dieses Repo und **nur**
"Issues" betreffen darf — kein Zugriff auf Code, keine anderen Repos:

1. https://github.com/settings/personal-access-tokens/new
2. **Resource owner:** final-wav
3. **Repository access:** Only select repositories → `cinema-atlas`
4. **Permissions:** Repository permissions → **Issues: Read and write** (alles
   andere auf "No access" lassen)
5. Token generieren, Wert kopieren (wird nur einmal angezeigt).

## 2) Worker deployen

### Variante A — Dashboard (kein Tooling nötig)
1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker**.
2. Namen vergeben (z. B. `cinema-atlas-report`) → **Deploy**.
3. **Edit code** → den kompletten Inhalt von [`worker.js`](worker.js) einfügen → **Deploy**.
4. **Settings → Variables**:
   - Environment Variable `GH_REPO` = `final-wav/cinema-atlas` (Text, nicht verschlüsselt)
   - Environment Variable `GH_TOKEN` = der Token aus Schritt 1 → **Encrypt** anklicken
5. Die Worker-URL kopieren, z. B. `https://cinema-atlas-report.deinname.workers.dev`.

### Variante B — Wrangler CLI
```bash
npm install -g wrangler
cd worker
wrangler login
wrangler secret put GH_TOKEN        # Token aus Schritt 1 einfügen
wrangler deploy
```
`GH_REPO` steht schon in `wrangler.toml`. Am Ende gibt Wrangler die Worker-URL aus.

## 3) Worker-URL eintragen

In **`../config.js`**:
```js
window.CINEMA_WORKER_BASE = "https://cinema-atlas-report.deinname.workers.dev";
```
Committen & pushen (bzw. `gh api` / GitHub-Web-UI direkt bearbeiten) — fertig.
Nach dem nächsten GitHub-Pages-Deploy funktioniert "Fehler melden" auf der Live-Seite.

## Test
```bash
curl -X POST https://cinema-atlas-report.deinname.workers.dev/report \
  -H "Content-Type: application/json" \
  -d '{"cinema":"Test-Kino","city":"Teststadt","kind":"sonstiges","message":"Testmeldung"}'
```
Sollte `{"ok":true}` liefern und ein neues Issue (Label `user-report`) im Repo anlegen.

## Spam-Schutz
Aktuell: ein verstecktes Honeypot-Feld (Bots füllen es aus, Menschen sehen es nicht)
plus serverseitige Längenprüfung. Reicht das nicht, lässt sich kostenlos
[Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/) vor das Formular
schalten (CAPTCHA ohne Google/reCAPTCHA).
