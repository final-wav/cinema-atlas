# Cinema Atlas

Ein durchsuch- und filterbares Verzeichnis von Kinosälen nach **Premium-Format** —
IMAX weltweit (mit Leinwandmaßen), dazu Dolby Cinema, ScreenX, 4DX, iSense,
Dolby Atmos und D-BOX (aktuell für Deutschland). Karte + Liste synchron,
Bearbeiten pro Eintrag, eigene Fotos, Event-/Vermietungs-Infos.

**Live:** https://final-wav.github.io/cinema-atlas/
**Anleitung:** [`anleitung.html`](anleitung.html) — Formate, Einträge bearbeiten/hinzufügen, Koordinaten, Updates.

## Architektur

Statisches Frontend (`index.html` + `cinema-data.js`) auf **GitHub Pages**, plus
ein optionaler **Cloudflare Worker** für das öffentliche Meldeformular ("Fehler
melden" → legt ein GitHub Issue an). Die App selbst braucht keinen Server —
sie ruft im Betrieb nichts Fremdes per `fetch()` auf (Kartenkacheln laufen über
`<img>`-Tags, PDFs über `<iframe>`, eigene Fotos/Korrekturen liegen lokal im
Browser via IndexedDB/localStorage).

| Datei/Ordner | Zweck |
|---|---|
| `index.html` | die App (Karte, Liste, Filter, Bearbeiten, Melde-Formular) |
| `anleitung.html` | ausführliche Anleitung |
| `cinema-data.js` | generierte Daten (von `update.py` erzeugt — nicht von Hand ändern) |
| `cinema_extra_de.csv` | von Hand gepflegte Premium-Format-Säle |
| `corrections.json` | von Hand kuratierte Korrekturen (überleben jedes Update) |
| `update.py` / `update.bat` | lokales Update-/Scrape-Skript (IMAX-Quelle, OpenStreetMap, Event-Locations) |
| `config.js` | trägt die Worker-URL fürs Meldeformular |
| `worker/` | Cloudflare Worker: Meldung → GitHub Issue (siehe `worker/README.md`) |

## Daten aktualisieren

```bash
python update.py     # oder update.bat doppelklicken
```
Zieht die IMAX-Community-Datenbank ([r-imax/imaxguide](https://github.com/r-imax/imaxguide))
neu, holt alle Kinos aus OpenStreetMap (Overpass), reichert deutsche Kinos mit
Event-/Vermietungsdaten an (Säle, Sitzplätze, Fotos, PDF-Datenblatt) und schreibt
`cinema-data.js` neu. Details siehe `anleitung.html`, Abschnitt 6–7.

## Hosting einrichten

1. **GitHub Pages**: Repo-Settings → Pages → Source: `main` / `/ (root)`.
2. **Melde-Worker** (optional, aber empfohlen): siehe [`worker/README.md`](worker/README.md).
   Ohne ihn läuft die Seite normal, nur "Fehler melden" ist inaktiv.

Beides ist im kostenlosen Tarif nutzbar (GitHub Pages + Cloudflare Workers Free).

## Lokal ansehen

Einfach `index.html` im Browser öffnen (kein Build-Schritt nötig), oder z. B.:
```bash
python -m http.server 8765
```
