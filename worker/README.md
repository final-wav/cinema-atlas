# Melde- und Vorschlags-Worker (Cloudflare Worker)

Nimmt zwei Arten von Nutzer-Eingaben aus der Cinema-Atlas-Seite entgegen:

- **Fehlermeldungen** ("Fehler melden", freier Text) → GitHub Issue, Label `user-report`.
- **Änderungsvorschläge** ("bearbeiten" → "Vorschlagen", strukturierter Feld-Diff) → GitHub
  Issue, Label `edit-suggestion`.

Beides landet zunächst nur als Issue — **nichts wird automatisch in die Daten übernommen**.
Erst über die separate, nirgends öffentlich verlinkte Seite **`admin.html`** lassen sich offene
Änderungsvorschläge ansehen und mit einem Klick **übernehmen** (schreibt `corrections.json` im
Repository per Commit — `index.html` liest diese Datei bei jedem Aufruf live mit) oder
**ablehnen**.

Ohne diesen Worker läuft `index.html` trotzdem normal — nur "Fehler melden" und "Vorschlagen"
zeigen dann einen Hinweis, dass die Funktion noch nicht eingerichtet ist. `admin.html` zeigt
denselben Hinweis beim Login-Versuch.

## Endpunkte

| Endpunkt | Zugriff | Zweck |
|---|---|---|
| `POST /report` | öffentlich | Fehlermeldung → Issue (Label `user-report`) |
| `POST /suggest` | öffentlich | Änderungsvorschlag → Issue (Label `edit-suggestion`) |
| `GET /admin/suggestions` | Admin | offene `edit-suggestion`-Issues auflisten |
| `POST /admin/approve` | Admin | Vorschlag übernehmen → `corrections.json` aktualisieren, Issue schließen |
| `POST /admin/reject` | Admin | Vorschlag ablehnen → Issue schließen, keine Datenänderung |
| `POST /admin/patch` | Admin | Direkte Korrektur ohne Issue (z. B. für schnelle eigene Korrekturen) |

Admin-Endpunkte erfordern den Header `X-Admin-Key: <ADMIN_KEY>`.

## 1) GitHub-Token erstellen (einmalig)

Ein **Fine-grained Personal Access Token**, das **nur** dieses Repository betreffen darf:

1. https://github.com/settings/personal-access-tokens/new
2. **Resource owner:** Konto/Organisation, unter dem das Repo liegt
3. **Repository access:** Only select repositories → das jeweilige Repo (z. B. `cinema-atlas`)
4. **Permissions:** Repository permissions →
   - **Issues: Read and write** (für Melde-/Vorschlagsfunktion)
   - **Contents: Read and write** (damit `/admin/approve` und `/admin/patch` `corrections.json` committen können)
5. Token generieren, Wert kopieren (wird nur einmal angezeigt).

## 2) Admin-Schlüssel festlegen

Ein frei gewähltes, ausreichend langes Passwort (z. B. per Passwortmanager generiert) —
dies wird als zweites Secret (`ADMIN_KEY`) hinterlegt und schützt alle `/admin/*`-Endpunkte
sowie den Login auf `admin.html`. Das ist die eigentliche Absicherung — nicht der Umstand,
dass `admin.html` nirgends verlinkt ist.

## 3) Worker deployen

### Variante A — Dashboard (kein Tooling nötig)
1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker**.
2. Namen vergeben (z. B. `cinema-atlas-report`) → **Deploy**.
3. **Edit code** → den kompletten Inhalt von [`worker.js`](worker.js) einfügen → **Deploy**.
4. **Settings → Variables**:
   - Environment Variable `GH_REPO` = `<konto>/<repo>` (Text, nicht verschlüsselt)
   - Environment Variable `GH_TOKEN` = der Token aus Schritt 1 → **Encrypt** anklicken
   - Environment Variable `ADMIN_KEY` = der Schlüssel aus Schritt 2 → **Encrypt** anklicken
5. Die Worker-URL notieren, z. B. `https://cinema-atlas-report.<subdomain>.workers.dev`.

### Variante B — Wrangler CLI
```bash
npm install -g wrangler
cd worker
wrangler login
wrangler secret put GH_TOKEN
wrangler secret put ADMIN_KEY
wrangler deploy
```
`GH_REPO` steht bereits in `wrangler.toml` (Wert bei Bedarf anpassen).

## 4) Worker-URL eintragen

In `../config.js`:
```js
window.CINEMA_WORKER_BASE = "https://cinema-atlas-report.<subdomain>.workers.dev";
```
Commit & Push — anschließend funktionieren "Fehler melden", "Vorschlagen" auf `index.html`
sowie der Login auf `admin.html`.

## Test
```bash
# Fehlermeldung
curl -X POST https://cinema-atlas-report.<subdomain>.workers.dev/report \
  -H "Content-Type: application/json" \
  -d '{"cinema":"Test-Kino","city":"Teststadt","kind":"sonstiges","message":"Testmeldung"}'

# Änderungsvorschlag
curl -X POST https://cinema-atlas-report.<subdomain>.workers.dev/suggest \
  -H "Content-Type: application/json" \
  -d '{"id":"abc123","cinema":"Test-Kino","city":"Teststadt","original":{"ci":"Teststadt"},"patch":{"ci":"Musterstadt"}}'

# Admin: offene Vorschläge (ADMIN_KEY ersetzen)
curl https://cinema-atlas-report.<subdomain>.workers.dev/admin/suggestions \
  -H "X-Admin-Key: <ADMIN_KEY>"
```
`/report` und `/suggest` sollten `{"ok":true}` liefern und ein Issue anlegen; `/admin/suggestions`
liefert eine JSON-Liste offener Vorschläge.

## Sicherheitsmodell
- `admin.html` ist eine gewöhnliche, öffentlich abrufbare statische Datei (nichts auf GitHub
  Pages lässt sich wirklich verstecken) — sie ist nur **nirgends verlinkt**, damit normale
  Besucher nicht darüber stolpern.
- Der eigentliche Schutz ist der `ADMIN_KEY`-Vergleich **serverseitig im Worker**. Ohne
  korrekten Schlüssel liefert jeder `/admin/*`-Aufruf `401`, unabhängig davon, ob jemand die
  Seite kennt oder nicht.
- `index.html` (die öffentliche Seite) enthält bewusst **keinerlei** Admin-Code — weder Button
  noch Funktionen —, damit im ausgelieferten Quelltext der Hauptseite nichts auf die
  Admin-Funktion hindeutet.

## Spam-Schutz
Aktuell: ein verstecktes Honeypot-Feld (Bots füllen es aus, Menschen sehen es nicht)
plus serverseitige Längenprüfung, bei `/report` und `/suggest`. Reicht das nicht, lässt sich
kostenlos [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/) vor die
Formulare schalten (CAPTCHA ohne Google/reCAPTCHA).
