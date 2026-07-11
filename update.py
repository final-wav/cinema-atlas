# -*- coding: utf-8 -*-
"""
Cinema Atlas — Update/Scrape-Skript.
Zieht die IMAX-Quelldatenbank (r-imax/imaxguide) per git neu, liest die
gepflegte Premium-Format-Datei (cinema_extra_de.csv), geocodet die Städte
(open-meteo, mit Cache) und erzeugt cinema-data.js für die Webseite.

Aufruf:  python update.py    (oder update.bat doppelklicken)
Voraussetzung: git + Python 3 + Internet.
"""
import csv, glob, os, json, re, subprocess, sys, urllib.request, urllib.parse, time, hashlib

HERE   = os.path.dirname(os.path.abspath(__file__))
CACHE  = os.path.join(HERE, ".cache")
REPODIR= os.path.join(CACHE, "imaxguide")
GEO    = os.path.join(CACHE, "geocache.json")
REVCACHE = os.path.join(CACHE, "revcache.json")
EXTRA  = os.path.join(HERE, "cinema_extra_de.csv")
OUT    = os.path.join(HERE, "cinema-data.js")
os.makedirs(CACHE, exist_ok=True)

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
def log(*a): print(*a, flush=True)

# ---------------------------------------------------------------- 1) IMAX-Quelle ziehen
def sync_repo():
    if os.path.isdir(os.path.join(REPODIR, ".git")):
        log("• imaxguide: git pull …")
        r=subprocess.run(["git","-C",REPODIR,"pull","--depth","1"],capture_output=True,text=True)
        if r.returncode!=0:
            log("  (pull fehlgeschlagen, nutze vorhandenen Stand)\n  ",r.stderr.strip()[:200])
    else:
        log("• imaxguide: git clone …")
        r=subprocess.run(["git","clone","--depth","1","https://github.com/r-imax/imaxguide.git",REPODIR],
                         capture_output=True,text=True)
        if r.returncode!=0:
            log("  FEHLER beim Klonen:\n  ",r.stderr.strip()[:400]);
            if not os.path.isdir(REPODIR): sys.exit(1)

# slug -> (Name, ISO2, Region, lat, lng)
C = {
 "aruba":("Aruba","AW","Lateinamerika & Karibik",12.52,-69.98),"australia":("Australien","AU","Ozeanien",-25,133),
 "austria":("Österreich","AT","Europa",47.6,14.1),"bahamas":("Bahamas","BS","Lateinamerika & Karibik",25.0,-77.4),
 "bahrain":("Bahrain","BH","Asien & Naher Osten",26.0,50.55),"belgium":("Belgien","BE","Europa",50.6,4.6),
 "brazil":("Brasilien","BR","Lateinamerika & Karibik",-14,-51),"canada":("Kanada","CA","Nordamerika",56,-106),
 "china":("China","CN","Asien & Naher Osten",35,105),"colombia":("Kolumbien","CO","Lateinamerika & Karibik",4.6,-74),
 "curacao":("Curaçao","CW","Lateinamerika & Karibik",12.17,-69.0),"czechia":("Tschechien","CZ","Europa",49.8,15.5),
 "denmark":("Dänemark","DK","Europa",56,10),"ecuador":("Ecuador","EC","Lateinamerika & Karibik",-1.8,-78),
 "finland":("Finnland","FI","Europa",64,26),"france":("Frankreich","FR","Europa",46.6,2.4),
 "germany":("Deutschland","DE","Europa",51.1,10.4),"hongkong":("Hongkong","HK","Asien & Naher Osten",22.32,114.17),
 "hungary":("Ungarn","HU","Europa",47.1,19.5),"india":("Indien","IN","Asien & Naher Osten",22,79),
 "indonesia":("Indonesien","ID","Asien & Naher Osten",-2.5,118),"ireland":("Irland","IE","Europa",53.4,-8.0),
 "italy":("Italien","IT","Europa",42.8,12.8),"japan":("Japan","JP","Asien & Naher Osten",36,138),
 "kuwait":("Kuwait","KW","Asien & Naher Osten",29.3,47.8),"latvia":("Lettland","LV","Europa",56.9,24.6),
 "luxembourg":("Luxemburg","LU","Europa",49.8,6.1),"malaysia":("Malaysia","MY","Asien & Naher Osten",4.2,101.9),
 "mexico":("Mexiko","MX","Nordamerika",23.6,-102.5),"morocco":("Marokko","MA","Afrika",31.8,-7.1),
 "netherlands":("Niederlande","NL","Europa",52.1,5.3),"newzealand":("Neuseeland","NZ","Ozeanien",-41,174),
 "norway":("Norwegen","NO","Europa",61,8),"oman":("Oman","OM","Asien & Naher Osten",21,57),
 "peru":("Peru","PE","Lateinamerika & Karibik",-9.2,-75),"philippines":("Philippinen","PH","Asien & Naher Osten",12.9,121.8),
 "poland":("Polen","PL","Europa",52,19),"portugal":("Portugal","PT","Europa",39.4,-8.2),
 "qatar":("Katar","QA","Asien & Naher Osten",25.3,51.2),"romania":("Rumänien","RO","Europa",45.9,24.9),
 "saudiarabia":("Saudi-Arabien","SA","Asien & Naher Osten",24,45),"serbia":("Serbien","RS","Europa",44,21),
 "singapore":("Singapur","SG","Asien & Naher Osten",1.35,103.82),"slovakia":("Slowakei","SK","Europa",48.7,19.5),
 "southafrica":("Südafrika","ZA","Afrika",-29,24),"southkorea":("Südkorea","KR","Asien & Naher Osten",36.5,127.8),
 "spain":("Spanien","ES","Europa",40.2,-3.7),"sweden":("Schweden","SE","Europa",62,15),
 "switzerland":("Schweiz","CH","Europa",46.8,8.2),"taiwan":("Taiwan","TW","Asien & Naher Osten",23.7,121),
 "thailand":("Thailand","TH","Asien & Naher Osten",15.0,101),"ukraine":("Ukraine","UA","Europa",49,32),
 "unitedarabemirates":("VAE","AE","Asien & Naher Osten",24,54),"unitedkingdom":("UK","GB","Europa",54,-2.5),
 "unitedstates":("USA","US","Nordamerika",39.5,-98.35),"vietnam":("Vietnam","VN","Asien & Naher Osten",16,108),
}
US_STATES={"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut",
 "DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
 "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan",
 "MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire",
 "NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
 "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee",
 "TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin",
 "WY":"Wyoming","DC":"District of Columbia"}

def num(s):
    if not s: return None
    m=re.search(r"[-\d.]+",s)
    if not m: return None
    v=float(m.group()); return v if v>0 else None

def classify_imax(ar,dp,fp):
    ar=(ar or "").strip();dp=(dp or "").strip();fp=(fp or "").strip()
    film="15/70" in fp
    if ar.startswith("Dome"): cat="dome"
    elif ar.startswith("1.43"): cat="film143" if film else "laser143"
    elif ar.startswith("1.90"):
        cat={"IMAX GT Laser":"gtxt190","IMAX Laser XT":"gtxt190","IMAX CoLa":"cola190","IMAX Digital":"xenon190"}.get(dp,"other190")
    else: cat="other"
    return cat,film

PREMIUM={"dolby_cinema","screenx","fourdx","isense","atmos","dbox"}
# Quelle (Label, URL) je Premium-Format
SRC={
 "dolby_cinema":("Dolby","https://www.dolby.com/de/film-tv/dolby-cinema/"),
 "screenx":("DigitaleLeinwand","https://digitaleleinwand.de/screenx/"),
 "fourdx":("DigitaleLeinwand","https://digitaleleinwand.de/4dx/"),
 "isense":("Teufel Blog","https://blog.teufel.de/uebersicht-dolby-atmos-kinos-in-deutschland/"),
 "atmos":("Teufel Blog","https://blog.teufel.de/uebersicht-dolby-atmos-kinos-in-deutschland/"),
 "dbox":("DigitaleLeinwand","https://digitaleleinwand.de/d-box/"),
}
# Länder, für die ALLE Kinos aus OpenStreetMap geladen werden (ISO-2 -> slug)
OSM_COUNTRIES=[("DE","germany")]

# ---------------------------------------------------------------- 2) Daten laden
def load():
    rows=[]
    for f in glob.glob(os.path.join(REPODIR,"data","**","*.csv"),recursive=True):
        slug=os.path.splitext(os.path.basename(f))[0]
        if slug not in C: log("  WARN unbekanntes Land:",slug); continue
        nm,iso,reg,clat,clng=C[slug]
        with open(f,encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                cat,film=classify_imax(r.get("Screen Aspect Ratio (AR)",""),r.get("Digital Projector",""),r.get("Film Projector",""))
                rows.append({"n":(r.get("Location Name") or "").strip(),"ci":(r.get("City") or "").strip(),
                  "st":(r.get("State") or "").strip(),"co":nm,"slug":slug,"reg":reg,
                  "ar":(r.get("Screen Aspect Ratio (AR)") or "").strip(),"cat":cat,"film":film,
                  "dp":(r.get("Digital Projector") or "").strip(),"fp":(r.get("Film Projector") or "").strip(),
                  "w":num(r.get("Width")),"h":num(r.get("Height")),
                  "com":(r.get("Commercial films shown?","").strip().lower()=="yes"),
                  "tier":"imax","url":"","src":"imaxguide","srcurl":"https://github.com/r-imax/imaxguide","note":""})
    # verifizierte IMAX-Ergänzungen (in der Quelle (noch) nicht enthalten)
    def imax_extra(slug,city,name,ar,dp,w,h,note="",lat=None,lng=None):
        nm,iso,reg,clat,clng=C[slug];cat,film=classify_imax(ar,dp,"No")
        r={"n":name,"ci":city,"st":"","co":nm,"slug":slug,"reg":reg,"ar":ar,"cat":cat,"film":film,
          "dp":dp,"fp":"No","w":w,"h":h,"com":True,
          "tier":"imax","url":"","src":"Betreiber-Angaben","srcurl":"","note":note}
        if lat is not None: r["lat"]=lat; r["lng"]=lng; r["exact"]=True
        rows.append(r)
    imax_extra("germany","Frankfurt am Main","CineStar Metropolis & IMAX","1.90:1","IMAX CoLa",21.34,11.3,lat=50.1205,lng=8.6790)
    imax_extra("germany","Dortmund","CineStar Dortmund & IMAX","1.90:1","IMAX CoLa",20.04,10.15,note="am Hauptbahnhof, Steinstraße 44",lat=51.5179,lng=7.4573)
    imax_extra("germany","Leipzig","CineStar & IMAX","1.90:1","IMAX CoLa",20.0,10.19,lat=51.3372,lng=12.3748)
    imax_extra("germany","Oberhausen","CineStar Filmpalast im CentrO & IMAX","1.90:1","IMAX CoLa",17.7,9.3,">164 m²",lat=51.4926,lng=6.8806)
    imax_extra("germany","Dresden","Kristallpalast & IMAX","1.90:1","IMAX CoLa",None,None,"Neueröffnung Juli 2026",lat=51.0505,lng=13.7380)
    imax_extra("germany","Bochum","UCI Ruhr Park & IMAX","1.90:1","IMAX CoLa",18.0,9.5,"ca. 170 m² · Ruhr Park",lat=51.4817,lng=7.2960)
    imax_extra("germany","Düsseldorf","UCI Kinowelt & IMAX","1.90:1","IMAX CoLa",None,None,
      "ehemaliger iSense-Saal, jetzt IMAX with Laser · Hammer Straße 29-31 (Medienhafen) · Leinwandmaß nicht verifiziert",
      lat=51.2133,lng=6.7524)
    imax_extra("denmark","Kopenhagen","CinemaxX Fisketorvet & IMAX","1.90:1","",None,None)
    imax_extra("ireland","Dublin","Cineworld Dublin & IMAX","1.90:1","",None,None)
    imax_extra("ireland","Dublin","ODEON Blanchardstown & IMAX","1.90:1","",None,None)
    imax_extra("hungary","Budapest","Cinema City Aréna & IMAX","1.90:1","",None,None)
    imax_extra("romania","Bukarest","Cinema City Cotroceni & IMAX","1.90:1","",None,None)
    imax_extra("romania","Timișoara","Cinema City & IMAX","1.90:1","",None,None)
    imax_extra("slovakia","Bratislava","Cinemax & IMAX","1.90:1","",None,None)

    # Reguläre Kinos, die der OSM-Massenabruf verpasst hat (manuell nachgetragen, meist mit OSM als Quelle verifiziert)
    def cinema_extra(slug,city,name,url,lat,lng,srcurl="",note=""):
        nm,iso,reg,clat,clng=C[slug]
        rows.append({"n":name,"ci":city,"st":"","co":nm,"slug":slug,"reg":reg,"ar":"","cat":"cinema","film":False,
          "dp":"","fp":"","w":None,"h":None,"com":True,"tier":"cinema","url":url,
          "src":"OpenStreetMap" if srcurl else "manuell ergänzt","srcurl":srcurl,"note":note,
          "lat":lat,"lng":lng,"exact":True})
    cinema_extra("germany","Altena","Apollo Service Kino","https://www.apollo-service-kino.de/",
      51.29705,7.67818,srcurl="https://www.openstreetmap.org/way/126668089",
      note="Säle: Apollo Royal (historisch) & Apollo De Luxe (4K-Projektion, Dolby 7.1)")
    cinema_extra("germany","Hagen","CineStar Hagen","https://www.cinestar.de/kino-hagen",
      51.354755,7.47965,srcurl="https://www.openstreetmap.org/way/31354078",
      note="Springe 1, 58095 Hagen · 8 Säle")
    cinema_extra("germany","Iserlohn","Filmpalast Iserlohn","https://iserlohn.filmpalast.de/",
      51.375943,7.696702,srcurl="https://www.openstreetmap.org/way/71002352",
      note="Kurt-Schumacher-Ring 1-3, 58636 Iserlohn")
    cinema_extra("germany","Borken","Kinocenter Borken","https://www.kinocenterborken.de",
      51.847211,6.860071,srcurl="https://www.openstreetmap.org/way/244101550",
      note="Johann-Walling-Straße 26, 46325 Borken")

    # Premium-Formate aus gepflegter CSV (Dolby Cinema, ScreenX, 4DX, iSense, Atmos)
    n_extra=0
    if os.path.exists(EXTRA):
        with open(EXTRA,encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                fmt=r["format"].strip()
                nm,iso,reg,clat,clng=C["germany"]
                slbl,surl=SRC.get(fmt,("recherchiert",""))
                rows.append({"n":r["cinema"].strip(),"ci":r["city"].strip(),"st":"","co":nm,"slug":"germany",
                  "reg":reg,"ar":"","cat":fmt,"film":False,"dp":"","fp":"","w":None,"h":None,
                  "com":True,"tier":"premium","url":"","src":slbl,"srcurl":surl,"note":r.get("note","").strip()})
                n_extra+=1
    log(f"• {len(rows)} Einträge (inkl. {n_extra} Premium-Format-Säle)")
    return rows

# ---------------------------------------------------------------- 2b) Alle Kinos aus OpenStreetMap
def _norm(s):
    import unicodedata
    s=unicodedata.normalize("NFD",s or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]"," ",s)

OVERPASS=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]
def fetch_osm():
    out=[]
    for iso,slug in OSM_COUNTRIES:
        nm,iso2,reg,clat,clng=C[slug]
        cache=os.path.join(CACHE,f"osm_{iso}.json")
        q=(f'[out:json][timeout:180];area["ISO3166-1"="{iso}"][admin_level=2];'
           '(node["amenity"="cinema"](area);way["amenity"="cinema"](area);relation["amenity"="cinema"](area););out center tags;')
        log(f"• OSM: lade alle Kinos {iso} … (kann etwas dauern)")
        rows_c=None
        for ep in OVERPASS:
            try:
                req=urllib.request.Request(ep,data=urllib.parse.urlencode({"data":q}).encode(),
                    headers={"User-Agent":"cinema-atlas/1.0"})
                j=json.load(urllib.request.urlopen(req,timeout=240))
                rows_c=[]
                for el in j.get("elements",[]):
                    t=el.get("tags",{}); name=(t.get("name") or "").strip()
                    if not name: continue
                    lat=el.get("lat") or (el.get("center") or {}).get("lat")
                    lng=el.get("lon") or (el.get("center") or {}).get("lon")
                    if lat is None or lng is None: continue
                    rows_c.append({"n":name,"ci":(t.get("addr:city") or t.get("addr:town") or t.get("addr:suburb") or "").strip(),
                      "st":"","co":nm,"reg":reg,"ar":"","cat":"cinema","film":False,"dp":"","fp":"","w":None,"h":None,
                      "com":True,"tier":"cinema","url":(t.get("website") or t.get("contact:website") or t.get("url") or "").strip(),
                      "src":"OpenStreetMap","srcurl":f"https://www.openstreetmap.org/{el['type']}/{el['id']}","note":"",
                      "lat":round(float(lat),5),"lng":round(float(lng),5),"exact":True})
                if rows_c:
                    json.dump(rows_c,open(cache,"w",encoding="utf-8"))   # Cache aktualisieren
                    log(f"  {len(rows_c)} Kinos geladen")
                    break
            except Exception as e:
                log(f"  OSM-Fehler ({ep.split('/')[2]}):",str(e)[:120])
        if not rows_c:   # Abruf fehlgeschlagen -> letzten guten Stand aus Cache nehmen
            if os.path.exists(cache):
                rows_c=json.load(open(cache,encoding="utf-8"))
                log(f"  -> {len(rows_c)} Kinos aus Cache (.cache/osm_{iso}.json) übernommen")
            else:
                rows_c=[]; log("  -> kein Cache vorhanden, OSM-Kinos fehlen diesmal")
        out.extend(rows_c)
    return out

# ---------------------------------------------------------------- 2d) Event-Infos + PDF (red-carpet-event.de)
RCECACHE=os.path.join(CACHE,"rce.json")
def _get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (cinema-atlas)"})
    return urllib.request.urlopen(req,timeout=30).read().decode("utf-8","ignore")

def fetch_rce():
    if os.path.exists(RCECACHE):
        try:
            d=json.load(open(RCECACHE,encoding="utf-8"))
            if time.time()-d.get("_ts",0) < 14*86400:
                log(f"• RCE: {len(d['items'])} Event-Locations aus Cache"); return d["items"]
        except Exception: pass
    log("• RCE: Event-Locations von red-carpet-event.de laden … (einmalig, dann 14 Tage Cache)")
    try:
        idx=_get("https://red-carpet-event.de/event-locations/")
    except Exception as e:
        log("  RCE-Index-Fehler:",str(e)[:150])
        if os.path.exists(RCECACHE): return json.load(open(RCECACHE,encoding="utf-8")).get("items",[])
        return []
    slugs=[]
    for s in re.findall(r'/eventlocations/([a-z0-9\-]+)/', idx):
        if s not in slugs: slugs.append(s)
    # Saal-Tabelle: Zeilen mit <td ... data-title="Feldname">Wert</td> — Spaltenzahl/Reihenfolge
    # variiert je Location (mal mit Leinwandgröße, mal ohne; mal mit Rollstuhlplätzen in Klammern).
    # -> generisch pro <tr> als {data-title: Wert}-Dict parsen statt feste Spaltenreihenfolge anzunehmen.
    tr_re=re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
    td_re=re.compile(r'<td[^>]*\bdata-title="([^"]*)"[^>]*>(.*?)</td>', re.S)
    def parse_halls(html):
        halls=[]
        for trm in tr_re.finditer(html):
            tds=td_re.findall(trm.group(1))
            if not tds: continue
            d={}
            for title,val in tds:
                clean=re.sub(r'<[^>]+>',' ',val)
                clean=re.sub(r'&#8211;|&ndash;|–','',clean)
                clean=re.sub(r'&#\d+;','',clean)
                d[title.strip()]=re.sub(r'\s+',' ',clean).strip()
            if d.get("Art des Raumes")!="Kinosaal": continue
            name=d.get("Name/ Nummer") or d.get("Name") or ""
            seats_key=next((k for k in d if "Sitzpl" in k), None)
            seats_raw=d.get(seats_key,"") if seats_key else ""
            m=re.match(r'\s*(\d+)', seats_raw)   # führende Zahl (Rollstuhlplätze in Klammern ignorieren)
            if not m: continue
            screen_key=next((k for k in d if "Leinwand" in k), None)
            screen=d.get(screen_key,"") if screen_key else ""
            halls.append({"name":name,"seats":int(m.group(1)),
              "screen":screen if re.search(r'\d',screen) else ""})
        return halls
    # Foto-Galerie: <a href="....jpg" class="pushed" ... data-caption="..." data-lbox="ilightbox_gallery-XXXX"
    #               data-external-thumb-image="....-150x150.jpg" ...>
    photo_re=re.compile(
        r'href="(https://www\.red-carpet-event\.de/app/uploads/[^"]+?\.(?:jpg|jpeg|png|webp))"\s+class="pushed"'
        r'[^>]*?data-caption="([^"]*)"[^>]*?data-lbox="([^"]*)"[^>]*?data-external-thumb-image="([^"]+)"', re.I)
    def parse_photos(html, cap=20):
        seen=set(); out=[]
        for url,caption,lbox,thumb in photo_re.findall(html):
            if url in seen: continue
            seen.add(url)
            out.append({"url":url,"thumb":thumb,"caption":caption.strip()})
            if len(out)>=cap: break
        return out
    items=[]
    for i,slug in enumerate(slugs):
        u=f"https://www.red-carpet-event.de/eventlocations/{slug}/"
        try:
            html=_get(u)
            m=re.search(r'https://www\.red-carpet-event\.de/app/uploads/[^"\'\s)]+\.pdf', html, re.I)
            tt=re.search(r'<title>([^<|–]+)', html)
            name=(tt.group(1).strip() if tt else slug.replace('-',' '))
            halls=parse_halls(html)
            photos=parse_photos(html)
            items.append({"slug":slug,"url":u,"pdf":(m.group(0) if m else ""),"name":name,
              "halls":halls,"seats":sum(h["seats"] for h in halls),"photos":photos})
        except Exception as e:
            log("  RCE-Seite übersprungen:",slug,str(e)[:60])
        time.sleep(0.1)
        if i%15==0: log(f"  RCE {i}/{len(slugs)}")
    json.dump({"_ts":time.time(),"items":items},open(RCECACHE,"w",encoding="utf-8"))
    log(f"• RCE: {len(items)} Locations geladen ({sum(1 for x in items if x['pdf'])} mit PDF, "
        f"{sum(1 for x in items if x['halls'])} mit Saal-Tabelle, "
        f"{sum(1 for x in items if x['photos'])} mit Fotos)")
    return items

_RSTOP={'eventlocation','mieten','event','location','red','carpet','filmpalast'}
def attach_rce(venues, items):
    R=[]
    for it in items:
        core={t for t in (_core(it['slug'].replace('-',' ')) | _core(it['name'])) if t not in _RSTOP}
        R.append((core,it))
    n=0
    for v in venues:
        if v["co"] not in ("Deutschland","Österreich"): continue
        vc={t for t in (_core(v['n']) | _core(v['ci'])) if t not in _RSTOP}
        best=None; bo=0
        for core,it in R:
            sh=core & vc
            if len(sh)<2: continue
            ov=len(sh)/min(len(core),len(vc)) if core and vc else 0
            if ov>bo: bo=ov; best=it
        if best and bo>=0.6:
            v["rce"]=best["url"]
            if best["pdf"]: v["pdf"]=best["pdf"]
            if best.get("halls"):
                v["halls"]=best["halls"]; v["hallSeats"]=best["seats"]
            if best.get("photos"):
                v["rcePhotos"]=best["photos"]
            n+=1
    log(f"• RCE: {n} Kinos mit Event-Seite/PDF verknüpft")
    return venues

# ---------------------------------------------------------------- 2c) Stadt nachtragen (Reverse-Geocoding)
def reverse_fill(rows):
    cache=json.load(open(REVCACHE,encoding="utf-8")) if os.path.exists(REVCACHE) else {}
    todo=[r for r in rows if not r.get("ci") and r.get("lat") is not None]
    if todo: log(f"• Reverse-Geocoding (Stadt nachtragen) für {len(todo)} Kinos …")
    for i,r in enumerate(todo):
        k=f"{r['lat']:.4f},{r['lng']:.4f}"
        if k in cache: r["ci"]=cache[k]; continue
        city=""
        try:
            u=(f"https://api.bigdatacloud.net/data/reverse-geocode-client?"
               f"latitude={r['lat']}&longitude={r['lng']}&localityLanguage=de")
            j=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"cinema-atlas/1.0"}),timeout=20))
            city=(j.get("city") or j.get("locality") or j.get("principalSubdivision") or "").strip()
        except Exception: pass
        cache[k]=city; r["ci"]=city; time.sleep(0.05)
        if i%50==0: json.dump(cache,open(REVCACHE,"w",encoding="utf-8")); log(f"  rev {i}/{len(todo)}")
    json.dump(cache,open(REVCACHE,"w",encoding="utf-8"))

# ---------------------------------------------------------------- 3) Geocoding
def geocode_all(rows):
    cache=json.load(open(GEO,encoding="utf-8")) if os.path.exists(GEO) else {}
    def gc(city,slug,state):
        key=f"{city}|{slug}|{state}"
        if key in cache: return cache[key]
        nm,iso,reg,clat,clng=C[slug]; res=None
        try:
            q=urllib.parse.urlencode({"name":city,"count":10,"language":"en","format":"json"})
            req=urllib.request.Request("https://geocoding-api.open-meteo.com/v1/search?"+q,headers={"User-Agent":"cinema-atlas/1.0"})
            cands=json.load(urllib.request.urlopen(req,timeout=20)).get("results",[]) or []
            best=None
            for c in cands:
                if c.get("country_code")!=iso: continue
                if slug=="unitedstates" and state:
                    want=US_STATES.get(state,"").lower()
                    if want and c.get("admin1","").lower()!=want:
                        best=best or c; continue
                best=c; break
            if best is None:
                for c in cands:
                    if c.get("country_code")==iso: best=c; break
            if best: res=[round(best["latitude"],4),round(best["longitude"],4),True]
        except Exception: pass
        if res is None:
            hh=int(hashlib.md5(key.encode()).hexdigest(),16)
            res=[round(clat+(((hh//1000)%1000)/1000-0.5)*3,4),round(clng+((hh%1000)/1000-0.5)*3,4),False]
        cache[key]=res; time.sleep(0.03); return res
    ok=fb=0
    for i,r in enumerate(rows):
        if r.get("lat") is not None:  # bereits verortet (OSM)
            continue
        lat,lng,ex=gc(r["ci"],r["slug"],r.get("st",""))
        r["lat"]=lat;r["lng"]=lng;r["exact"]=ex; ok+=ex; fb+=(not ex)
        if i%80==0: json.dump(cache,open(GEO,"w",encoding="utf-8")); log(f"  geocode {i}/{len(rows)}")
    json.dump(cache,open(GEO,"w",encoding="utf-8"))
    log(f"• Geocoding: {ok} exakt, {fb} genähert")

# ---------------------------------------------------------------- 3b) Zusammenführen (ein Kino = ein Eintrag)
PRIORITY=['film143','laser143','dome','gtxt190','cola190','xenon190','other190','other',
          'dolby_cinema','screenx','fourdx','isense','atmos','dbox','cinema']
def _srcrank(s): return 0 if s=="OpenStreetMap" else 1
_STOP={'imax','and','und','der','die','das','am','im','the','cinema','cinemas','kino','kinos','3d','dome','amp','hauptbahnhof','hbf'}
def _core(name):
    return {t for t in _norm(name).split() if t not in _STOP and len(t)>=3}
def _dist(a,b):
    from math import radians,sin,cos,asin,sqrt
    dlat=radians(b[0]-a[0]); dlon=radians(b[1]-a[1])
    h=sin(dlat/2)**2+cos(radians(a[0]))*cos(radians(b[0]))*sin(dlon/2)**2
    return 2*6371*asin(sqrt(h))
def _fmt(r):
    return {"cat":r["cat"],"ar":r["ar"],"dp":r["dp"],"fp":r["fp"],"w":r["w"],"h":r["h"],
            "film":r["film"],"note":r["note"],"src":r["src"],"srcurl":r["srcurl"]}

def merge_venues(rows):
    venues=[]
    for r in rows:
        rc=_core(r["n"]); rcity=_norm(r["ci"])
        m=None
        for v in venues:
            if v["co"]!=r["co"]: continue
            d=_dist((v["lat"],v["lng"]),(r["lat"],r["lng"]))
            sh=v["_core"]&rc
            ov=(len(sh)/min(len(v["_core"]),len(rc))) if (v["_core"] and rc) else 0
            if (v["_core"]==rc and rc and d<=20) or (ov>=0.6 and len(sh)>=2 and d<=15) or (ov>=0.6 and d<=2.5):
                m=v; break
        if m is None:
            venues.append({"n":r["n"],"ci":r["ci"],"st":r["st"],"co":r["co"],"reg":r["reg"],
              "lat":r["lat"],"lng":r["lng"],"exact":r["exact"],"url":r["url"],"com":r["com"],
              "formats":[_fmt(r)],"_core":set(rc),"_city":rcity,"_nsrc":_srcrank(r["src"]),"_nl":len(r["n"])})
        else:
            m["formats"].append(_fmt(r)); m["_core"]|=rc
            if not m["_city"] and rcity: m["_city"]=rcity
            if r["exact"] and not m["exact"]: m["lat"],m["lng"],m["exact"]=r["lat"],r["lng"],True
            if r["url"] and not m["url"]: m["url"]=r["url"]
            m["com"]=m["com"] or r["com"]
            rr=_srcrank(r["src"])
            if rr>m["_nsrc"] or (rr==m["_nsrc"] and len(r["n"])>m["_nl"]):
                m["n"]=r["n"]; m["st"]=r["st"] or m["st"]; m["_nsrc"]=rr; m["_nl"]=len(r["n"])
            if r["ci"] and not m["ci"]: m["ci"]=r["ci"]
    out=[]
    for v in venues:
        cats=[f["cat"] for f in v["formats"]]
        key=lambda c:PRIORITY.index(c) if c in PRIORITY else 99
        prim=min(cats,key=key); pf=next(f for f in v["formats"] if f["cat"]==prim)
        vid=hashlib.md5((v["n"]+"|"+v["ci"]+"|"+v["co"]).encode()).hexdigest()[:10]
        out.append({"id":vid,"n":v["n"],"ci":v["ci"],"st":v["st"],"co":v["co"],"reg":v["reg"],
          "lat":v["lat"],"lng":v["lng"],"exact":v["exact"],"url":v["url"],"com":v["com"],
          "cat":prim,"cats":sorted(set(cats),key=key),"film":any(f["film"] for f in v["formats"]),
          "ar":pf["ar"],"dp":pf["dp"],"fp":pf["fp"],"w":pf["w"],"h":pf["h"],
          "note":pf["note"],"src":pf["src"],"srcurl":pf["srcurl"],"formats":v["formats"]})
    return out

def apply_corrections(venues):
    p=os.path.join(HERE,"corrections.json")
    if not os.path.exists(p): return venues
    try: corr=json.load(open(p,encoding="utf-8"))
    except Exception as e: log("  corrections.json fehlerhaft:",e); return venues
    out=[]; applied=0
    for v in venues:
        o=corr.get(v["id"])
        if o:
            if o.get("_delete"): applied+=1; continue
            for k,val in o.items():
                if k!="_delete": v[k]=val
            applied+=1
        out.append(v)
    log(f"• Korrekturen aus corrections.json angewendet: {applied}")
    return out

# ---------------------------------------------------------------- 4) Schreiben
def write(rows):
    for r in rows: r.pop("slug",None)
    from collections import Counter
    log("• Formate:",dict(Counter(r["cat"] for r in rows)))
    gen=time.strftime("%Y-%m-%d %H:%M")
    with open(OUT,"w",encoding="utf-8") as fh:
        fh.write("// Auto-generiert von update.py — Quelle: r-imax/imaxguide + cinema_extra_de.csv. Stand "+gen+"\n")
        fh.write("const GEN="+json.dumps(gen)+";\n")
        fh.write("const DATA="+json.dumps(rows,ensure_ascii=False)+";\n")
    log("• geschrieben:",OUT,f"({os.path.getsize(OUT)//1024} KB)")

if __name__=="__main__":
    sync_repo()
    rows=load()
    rows+=fetch_osm()
    reverse_fill(rows)
    geocode_all(rows)
    venues=merge_venues(rows)
    venues=attach_rce(venues, fetch_rce())
    venues=apply_corrections(venues)
    log(f"• Merge: {len(rows)} Einträge → {len(venues)} Kinos ({len(rows)-len(venues)} Dubletten zusammengeführt)")
    multi=[v for v in venues if len(v["formats"])>1]
    log(f"• {len(multi)} Kinos mit mehreren Formaten, z. B.:")
    for v in multi[:8]:
        log("   -",v["n"],"|",v["ci"],"|",", ".join(sorted({f['cat'] for f in v['formats']})))
    write(venues)
    log("Fertig. Webseite (imax-saele.html) neu laden.")
