import sqlite3, re, sys, shutil, unicodedata
from datetime import datetime
from collections import Counter
import pandas as pd

EXCEL = "DATA SUR EXCEL/Entreprises_Marrakech_Final_361.xlsx"
DB = "database/career_finder.db"
APPLIQUER = "--appliquer" in sys.argv


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def telephones(s):
    res = set()
    for part in re.split(r"[/;,]", str(s or "")):
        d = re.sub(r"\D", "", part)
        if len(d) >= 9:
            res.add(d[-9:])
    return res


def domaine_site(s):
    s = str(s or "").lower().strip()
    if s in ("", "—", "-", "nan", "none"):
        return ""
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.split("/")[0]


def choisir_domaine(d):
    d = str(d).lower()
    if any(m in d for m in ("ia", "data")) and ("ia" in d.split("/")[-1:][0] or "data" in d):
        return "IA / Data"
    if any(m in d for m in ("logiciel", "software", "it /", "cyber", "devops")) or d.startswith("it"):
        return "Développement logiciel"
    return "Web & Digital"


con = sqlite3.connect(DB)
cur = con.cursor()
colonnes_db = [c[1] for c in cur.execute("PRAGMA table_info(companies)")]

existants = cur.execute(
    "SELECT nom_entreprise, telephone, site_web FROM companies").fetchall()
noms_db = [norm(n) for n, _, _ in existants if n]
tels_db = set()
sites_db = set()
for _, t, s in existants:
    tels_db |= telephones(t)
    if domaine_site(s):
        sites_db.add(domaine_site(s))

statut_defaut = cur.execute(
    "SELECT statut_candidature FROM companies GROUP BY statut_candidature "
    "ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
statut_defaut = statut_defaut[0] if statut_defaut else ""

df = pd.read_excel(EXCEL)
a_ajouter, ignorees = [], []

for _, r in df.iterrows():
    nom = str(r["Entreprise"]).strip()
    n = norm(nom)
    tels = telephones(r["Téléphone"])
    site = domaine_site(r["Site officiel"])

    raison = None
    for nd in noms_db:
        if n == nd or (len(n) >= 6 and (n in nd or nd in n and len(nd) >= 6)):
            raison = "même nom"
            break
    if not raison and tels & tels_db:
        raison = "même téléphone"
    if not raison and site and site in sites_db:
        raison = "même site web"
    if not raison and n in {norm(x["nom"]) for x in a_ajouter}:
        raison = "doublon dans le fichier"

    if raison:
        ignorees.append((nom, raison))
        continue

    tel_txt = str(r["Téléphone"]).split("/")[0].strip()
    a_ajouter.append({
        "nom": nom,
        "nom_entreprise": nom,
        "secteur": "Informatique & Digital",
        "domaine": choisir_domaine(r["Domaine"]),
        "titre_poste": str(r["Type de stage / poste"]),
        "type_source": "Excel Marrakech Final",
        "adresse": str(r["Adresse"]),
        "ville": "Marrakech",
        "type_contrat": "Stage",
        "score_total": 60.0,
        "priorite": "Moyenne",
        "statut_candidature": statut_defaut,
        "telephone": tel_txt,
        "site_web": ("https://" + site) if site else "",
        "lien": ("https://" + site) if site else "",
    })
    sites_db.add(site) if site else None
    tels_db |= tels
    noms_db.append(n)

print("=" * 55)
print("MODE :", "APPLICATION" if APPLIQUER else "SIMULATION (rien n'est écrit)")
print("=" * 55)
print("Lignes lues dans l'Excel     :", len(df))
print("Entreprises à ajouter        :", len(a_ajouter))
print("Entreprises ignorées         :", len(ignorees))
print("Dans la base avant           :", len(existants))
print("Dans la base après           :", len(existants) + len(a_ajouter))
print("\nRépartition par domaine :")
for d, n in Counter(x["domaine"] for x in a_ajouter).items():
    print(f"  {d} : {n}")
print("\nÀ AJOUTER :")
for x in a_ajouter:
    print(f"  + {x['nom']} | {x['domaine']}")
print("\nIGNORÉES :")
for nom, raison in ignorees:
    print(f"  - {nom} -> déjà dans la base ({raison})")

if not APPLIQUER:
    print("\nAucune modification faite. Si le rapport te convient, lance :")
    print("  python importer_nouveau.py --appliquer")
    con.close()
    sys.exit()

sauv = f"database/career_finder_sauvegarde_{datetime.now():%Y%m%d_%H%M%S}.db"
shutil.copy2(DB, sauv)
print("\nSauvegarde créée :", sauv)

for x in a_ajouter:
    x.pop("nom")
    ligne = {k: v for k, v in x.items() if k in colonnes_db}
    cols = ", ".join(ligne)
    qs = ", ".join("?" for _ in ligne)
    cur.execute(f"INSERT INTO companies ({cols}) VALUES ({qs})", list(ligne.values()))
con.commit()
total = cur.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
print(f"Ajout terminé : {len(a_ajouter)} entreprises ajoutées. Total dans la base : {total}.")
con.close()