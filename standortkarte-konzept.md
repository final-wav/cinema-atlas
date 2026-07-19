# Standortkarte für ein Unternehmen — Konzept

Eine interaktive Karte aller Firmenstandorte mit Fotos und Detailinfos
(stellv. Leitung, ärztl. Leitung, Telefon, zuständiger Dienstleister),
gespeist aus einer CSV. Aufgebaut nach demselben Muster wie dieses
Cinema-Atlas-Projekt.

**Leitgedanke:** Die Firmendaten sollen so wenig wie möglich mit KI in
Berührung kommen. Das ist technisch sauber lösbar — die KI baut nur die
Maschine (mit Dummy-Daten), die echten Daten laufen ausschließlich lokal.

---

## 1. Grundarchitektur — drei getrennte Teile

| Teil | Was es ist | Wo es läuft |
|------|------------|-------------|
| **Daten** | eine CSV (bzw. Excel-Export) | nur bei dir |
| **Build-Skript** | Python, liest die CSV → erzeugt Datendatei | lokal bei dir |
| **Viewer** | eine `index.html` (Karte, Liste, Suche, Detail) | Browser / interner Server |

Ablauf im Alltag:

```
CSV pflegen  →  Skript einmal ausführen  →  fertige Karte
```

Bei Änderungen: CSV nachziehen, Skript nochmal laufen lassen, fertig.

---

## 2. Datenschutz — wer sieht was

Der wichtigste Punkt, konkret aufgeschlüsselt:

- **KI / Assistent:** sieht ausschließlich den Programmcode und erfundene
  Beispieldaten (z.B. „Standort Nord / Dr. Muster / 040-000"). Die echte
  Personaldaten-CSV bekommt die KI **nie** zu Gesicht.
- **Build-Skript:** rechnet stur nach Regeln (Spalte X → Feld Y). Kein
  „Verstehen", kein Cloud-Dienst, der Inhalte interpretiert. Reine
  Textverarbeitung auf deinem Rechner.
- **Browser/Viewer:** lädt Kartenkacheln von OpenStreetMap. Dabei geht
  **nur der Kartenausschnitt** raus (welcher Bereich angezeigt wird),
  **nie** Namen, Telefonnummern oder Dienstleister — die liegen alle
  lokal in der Datendatei.

**Firmendaten ↔ KI = praktisch null.** Nur der Programmcode entsteht mit KI.

Der einzige Punkt, an dem Daten überhaupt das Haus verlassen *könnten*,
ist das Geocoding (siehe Abschnitt 4) — und das lässt sich abschalten.

---

## 3. Die CSV

Spalten frei wählbar; das Skript wird darauf angepasst. Beispiel für dein
Szenario:

```
name;strasse;plz;ort;lat;lng;telefon;stellv_leitung;aerztl_leitung;dienstleister;foto;notiz
Standort Nord;Beispielweg 1;20095;Hamburg;53.55;9.99;040/123;Frau A;Dr. B;Firma XY;nord.jpg;
Standort Süd;Musterstr. 7;80331;München;48.14;11.58;089/456;Herr C;Dr. D;Firma ZZ;sued.jpg;24h-Dienst
```

- Leere Felder sind erlaubt (nicht jeder Standort hat alles).
- Direkt aus Excel exportierbar als „CSV (Trennzeichen-getrennt)".

---

## 4. Geocoding (Adresse → Punkt auf der Karte)

Die Karte braucht pro Standort Koordinaten. Drei Wege — von „am
privatesten" nach „am bequemsten":

- **A) Koordinaten stehen schon in der CSV**
  Das Skript macht **keinen** Netzaufruf. Daten verlassen den Rechner nie.
  Koordinaten bekommt man z.B. per Rechtsklick in Google/OpenStreetMap →
  „Koordinaten kopieren".
- **B) Skript geocodet automatisch**
  Es schickt pro Standort **nur die Adresse** (Straße, PLZ, Ort — keine
  Personennamen/Telefon) an einen Geocoder (z.B. OpenStreetMap). Bequem;
  Betriebsadressen sind ohnehin meist öffentlich.
- **C) Offline-Geocoding**
  Lokaler Datenbestand, dann geht nichts raus. Aufwändiger, aber möglich,
  wenn selbst Adressen nicht das Haus verlassen sollen.

Das Skript kann kombinieren: **„nimm lat/lng aus der CSV, und nur wo sie
fehlen, frag den Geocoder".**

Empfehlung: **A** für maximale Dichtigkeit, sonst **B** für Komfort.

---

## 5. Fotos

- **Lokaler Ordner** *(empfohlen)* — Bilder in einen `fotos/`-Ordner, in
  der CSV steht nur der Dateiname. Bilder bleiben bei dir / auf eurem
  Server.
- **Eingebettet** — das Skript backt kleine Vorschaubilder direkt in die
  Datendatei. Alles in einer Datei, kein separater Ordner.

---

## 6. Der Viewer — was man sieht

- **Karte** mit allen Standorten als Pins (Cluster bei vielen nah
  beieinander).
- **Liste** links — auf dem Handy als ziehbares Bottom-Sheet (mobile
  Ansicht kommt aus diesem Projekt direkt mit).
- **Suche** nach Standort / Ort / Dienstleister.
- **Filter**, z.B. „nach Dienstleister" oder „nach Region" — so siehst du
  alle Standorte einer Betreuungsfirma auf einen Blick.
- **Detailpanel** pro Standort:
  - Foto
  - Adresse
  - **stellv. Leitung**
  - **ärztl. Leitung**
  - **Telefon** (klickbar → wählt direkt)
  - **zuständiger Dienstleister**
  - Notizen
- Optional **Umkreissuche**: Ort eingeben → Karte fliegt hin, Standorte
  der Umgebung nach Entfernung.

---

## 7. Hosting & DSGVO

Da **Personennamen + Telefonnummern** enthalten sind (personenbezogene
Daten), gehört die Karte in der Regel **nicht** frei ins öffentliche Netz.
Sinnvolle Varianten:

- **Nur lokal / im Intranet** *(am saubersten)* — Datei auf internem
  Server oder Netzlaufwerk, nur Mitarbeiter haben Zugriff.
- **Öffentlich mit Passwort / Login** davor.
- Falls es doch öffentlich sein müsste: dann besser **ohne** die sensiblen
  Personen-/Telefonfelder.

---

## 8. Zusammenarbeit — ohne dass echte Daten zur KI kommen

1. Du nennst die **Spalten** deiner CSV (nur die Überschriften, keine
   echten Werte).
2. Die KI baut **Skript + Viewer** mit **Dummy-Daten** und testet alles.
3. Du bekommst ein kleines Paket, legst deine **echte** CSV rein, lässt
   das Skript **bei dir** laufen → fertige Karte.
4. Spätere Änderungen: CSV pflegen, Skript erneut ausführen.

So entsteht die komplette Maschine mit KI, aber die Fabrik läuft am Ende
mit den echten Daten allein bei dir.

---

## 9. Offene Entscheidungen (bevor es losgeht)

1. **Spalten der CSV** — welche Felder genau, in welcher Reihenfolge?
2. **Geocoding** — Variante **A** (Koordinaten in CSV), **B** (automatisch
   online) oder **C** (offline)?
3. **Fotos** — lokaler Ordner oder eingebettet?
4. **Hosting** — intern/passwortgeschützt oder öffentlich (dann ggf. ohne
   sensible Felder)?

Sobald diese vier geklärt sind, kann ein **lauffähiger Prototyp mit
Beispieldaten** (5–6 Dummy-Standorte, alle Felder) gebaut werden, den man
sofort im Browser anschauen und später mit der echten CSV füttern kann.
