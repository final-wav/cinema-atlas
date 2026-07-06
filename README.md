# Cinema Atlas

Ein durchsuch- und filterbares Verzeichnis von Kinosälen nach **Premium-Format** —
IMAX weltweit (mit Leinwandmaßen), dazu Dolby Cinema, ScreenX, 4DX, iSense,
Dolby Atmos und D-BOX (aktuell für Deutschland). Karte + Liste synchron,
bearbeitbare Einträge, eigene Fotos, Event-/Vermietungs-Infos.

**Live:** https://final-wav.github.io/cinema-atlas/
**Anleitung:** [`anleitung.html`](anleitung.html) — Formate, Einträge bearbeiten/hinzufügen, Koordinaten, Updates.

## Architektur

Statisches Frontend (`index.html` + `cinema-data.js`) auf **GitHub Pages**, plus
ein optionaler **Cloudflare Worker** für zwei Formulare ("Fehler melden" und
"Änderung vorschlagen" → jeweils ein GitHub Issue) sowie eine separate,
nirgends verlinkte Seite `admin.html` zum Prüfen und Übernehmen offener
Vorschläge. Übernommene Korrekturen landen in `corrections.json`, die
`index.html` bei jedem Aufruf zusätzlich zu `cinema-data.js` live nachlädt —
neben diesem einen, gleichen-Repo-Abruf ruft die App im laufenden Betrieb
nichts Fremdes per `fetch()` auf (Kartenkacheln laufen über `<img>`-Tags,
PDFs über `<iframe>`, eigene Fotos/Entwürfe liegen lokal im Browser via
IndexedDB/localStorage).

| Datei/Ordner | Zweck |
|---|---|
| `index.html` | die öffentliche App (Karte, Liste, Filter, Änderungen vorschlagen) — ohne jeglichen Admin-Code |
| `admin.html` | separate, nicht verlinkte Seite zum Prüfen/Übernehmen von Vorschlägen |
| `anleitung.html` | ausführliche Nutzungsanleitung |
| `cinema-data.js` | generierte Daten (von `update.py` erzeugt — nicht von Hand ändern) |
| `cinema_extra_de.csv` | gepflegte Liste der Premium-Format-Säle |
| `corrections.json` | bestätigte Korrekturen — wird sowohl live von `index.html` geladen als auch von `update.py` beim Neubauen angewendet |
| `update.py` / `update.bat` | Update-/Scrape-Skript (IMAX-Quelle, OpenStreetMap, Event-Locations) |
| `config.js` | enthält die Worker-URL für Formulare & Admin-Seite |
| `worker/` | Cloudflare Worker: Meldungen/Vorschläge → GitHub Issue, Admin-Endpunkte → `corrections.json` (siehe `worker/README.md`) |

## Datenquellen

- **IMAX weltweit** — Community-Datenbank [r-imax/imaxguide](https://github.com/r-imax/imaxguide) (Leinwandmaße, Projektortyp).
- **Alle übrigen Kinos** — [OpenStreetMap](https://www.openstreetmap.org) (Overpass API), aktuell Deutschland.
- **Premium-Formate** (Dolby Cinema, ScreenX, 4DX, iSense, Dolby Atmos, D-BOX) — recherchiert bei den großen Kinoketten (u. a. CineStar, UCI, Cineplex, Kinopolis), gepflegt in `cinema_extra_de.csv`; einzelne Kinos zusätzlich auf Anfrage recherchiert und ergänzt.
- **Event-/Vermietungsdaten** (Säle, Sitzplätze, Fotos, Datenblatt) — [red-carpet-event.de](https://www.red-carpet-event.de), soweit vorhanden.
- **Geocoding** — Stadtnamen ↔ Koordinaten über die [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) und (zur Ergänzung fehlender Stadtnamen aus OpenStreetMap) [BigDataCloud](https://www.bigdatacloud.com/reverse-geocoding-api).

## Daten aktualisieren

```bash
python update.py     # oder update.bat per Doppelklick
```
Zieht die IMAX-Community-Datenbank neu, holt alle Kinos aus OpenStreetMap,
reichert deutsche Kinos mit Event-/Vermietungsdaten an und schreibt
`cinema-data.js` neu. Details in `anleitung.html`, Abschnitt 6–7.

## Selbst hosten

1. Repository forken oder klonen.
2. **GitHub Pages** aktivieren: Repo-Settings → Pages → Source: `main` / `/ (root)`.
3. **Formulare & Admin-Prüfung** (optional): Cloudflare Worker einrichten, siehe
   [`worker/README.md`](worker/README.md). Ohne Worker läuft die Seite normal,
   nur „Fehler melden"/„Vorschlagen" sowie der Login auf `admin.html` sind inaktiv.

Beides ist im kostenlosen Tarif nutzbar (GitHub Pages + Cloudflare Workers Free).

## Lokal ansehen

`index.html` direkt im Browser öffnen (kein Build-Schritt nötig), oder z. B.:
```bash
python -m http.server 8765
```

## Mitmachen

Fehlende oder falsche Einträge lassen sich über das Meldeformular auf der Seite
melden, oder direkt als [GitHub Issue](https://github.com/final-wav/cinema-atlas/issues)
einreichen. Pull Requests für `cinema_extra_de.csv` oder Ergänzungen in
`update.py` sind willkommen.

## Lizenz

Datenquellen unterliegen ihren jeweiligen Lizenzen (u. a. OpenStreetMap: ODbL).
Der Code dieses Repos darf frei verwendet und angepasst werden.
