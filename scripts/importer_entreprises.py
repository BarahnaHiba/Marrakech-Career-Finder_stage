"""
Importe les entreprises du fichier Excel dans la base career_finder.db.

  python importer_entreprises.py             -> SIMULATION (n'écrit rien)
  python importer_entreprises.py --appliquer -> ajoute vraiment les entreprises
                                                (après une sauvegarde de la base)
"""
import os
import re
import sys
import sqlite3
import unicodedata
from datetime import datetime
from urllib.parse import quote, urlparse

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from openpyxl import load_workbook
except ImportError:
    sys.exit("openpyxl manque. Lance :  pip install openpyxl   puis relance le script.")

# ------------------------------------------------------------------
#  RÉGLAGES (tu peux modifier ces valeurs)
# ------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'database', 'career_finder.db')
FICHIER_EXCEL = os.path.join(BASE, 'data_nettoyee.xlsx')

SECTEUR = 'Informatique & Digital'
VILLE = 'Marrakech'

# Sous-domaine du fichier Excel -> domaine utilisé dans ton application
CORRESPONDANCE_DOMAINES = {
    'web': 'Web & Digital',
    'ia & automatisation': 'IA / Data',
    'logiciels sur mesure': 'Développement logiciel',
    'hébergement & cloud': 'Services informatiques',
    'cybersécurité': 'Réseaux & Cybersécurité',
}
DOMAINE_PAR_DEFAUT = 'Services informatiques'

# Score de départ selon le domaine (ton stage vise Data Analyst / IA)
SCORE_BASE = {
    'IA / Data': 85,
    'Développement logiciel': 70,
    'Réseaux & Cybersécurité': 65,
    'Web & Digital': 62,
    'Services informatiques': 58,
}
BONUS_NOTE_FORTE = 5     # note >= 4,5 avec au moins 10 avis
BONUS_NOTE_BONNE = 2     # note >= 4,0 avec au moins 3 avis
BONUS_SITE = 3           # l'entreprise a un site web
BONUS_TELEPHONE = 2      # l'entreprise a un téléphone
SEUIL_HAUTE = 75         # score >= 75  -> priorité Haute
SEUIL_MOYENNE = 55       # score >= 55  -> priorité Moyenne, sinon Basse

# Entreprises ignorées si leur nom contient un de ces mots
MOTS_A_EXCLURE = ('freelance',)
VILLES_ACCEPTEES = ('marrakech', 'marrakesh', 'مراكش')
# Les codes postaux de Marrakech commencent par 40 (ex. 40000, 40090)
CODE_POSTAL_MARRAKECH = re.compile(r'\b40\d{3}\b')
# ------------------------------------------------------------------


def est_a_marrakech(adresse):
    a = (adresse or '').lower()
    return any(v in a for v in VILLES_ACCEPTEES) or bool(CODE_POSTAL_MARRAKECH.search(a))

def sans_accents(texte):
    texte = unicodedata.normalize('NFKD', texte or '')
    return ''.join(c for c in texte if not unicodedata.combining(c))

def cle_nom(nom):
    return ''.join(c for c in sans_accents(nom).lower() if c.isalnum())

def cle_site(url):
    url = (url or '').strip().lower()
    if not url:
        return ''
    if '://' not in url:
        url = 'http://' + url
    hote = urlparse(url).netloc
    return hote[4:] if hote.startswith('www.') else hote

def cle_tel(tel):
    chiffres = ''.join(c for c in (tel or '') if c.isdigit())
    return chiffres[-9:] if len(chiffres) >= 9 else ''

def valeur(v):
    """Texte propre : 'Non renseigné' et les cellules vides deviennent ''."""
    texte = '' if v is None else str(v).strip()
    return '' if texte.lower() in ('non renseigné', 'non renseigne', 'nan', 'none') else texte

def nombre(v):
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None

def lire_excel(chemin):
    classeur = load_workbook(chemin, read_only=True, data_only=True)
    feuille = classeur.active
    lignes = feuille.iter_rows(values_only=True)
    entetes = [str(c).strip() if c is not None else '' for c in next(lignes)]
    donnees = []
    for ligne in lignes:
        if not any(c not in (None, '') for c in ligne):
            continue
        donnees.append(dict(zip(entetes, ligne)))
    classeur.close()
    return donnees

def calculer_score(domaine, note, nb_avis, a_site, a_tel):
    score = SCORE_BASE.get(domaine, 58)
    if note is not None and nb_avis is not None:
        if note >= 4.5 and nb_avis >= 10:
            score += BONUS_NOTE_FORTE
        elif note >= 4.0 and nb_avis >= 3:
            score += BONUS_NOTE_BONNE
    if a_site:
        score += BONUS_SITE
    if a_tel:
        score += BONUS_TELEPHONE
    score = max(40, min(100, score))
    if score >= SEUIL_HAUTE:
        priorite = 'Haute'
    elif score >= SEUIL_MOYENNE:
        priorite = 'Moyenne'
    else:
        priorite = 'Basse'
    return float(score), priorite


def main():
    appliquer = '--appliquer' in sys.argv

    if not os.path.exists(DB_PATH):
        sys.exit(f"Base introuvable : {DB_PATH}")
    if not os.path.exists(FICHIER_EXCEL):
        sys.exit(f"Fichier Excel introuvable : {FICHIER_EXCEL}\n"
                 "Copie data_nettoyee.xlsx à la racine du projet (à côté de ce script).")

    conn = sqlite3.connect(DB_PATH)
    existantes = conn.execute("SELECT nom_entreprise, site_web, lien, telephone FROM companies").fetchall()
    noms = {cle_nom(r[0]) for r in existantes}
    sites = {cle_site(r[1]) for r in existantes} | {cle_site(r[2]) for r in existantes}
    tels = {cle_tel(r[3]) for r in existantes}
    sites.discard('')
    tels.discard('')
    total_avant = len(existantes)

    lignes = lire_excel(FICHIER_EXCEL)
    a_ajouter, ignorees = [], []

    for l in lignes:
        nom = valeur(l.get('Nom_Entreprise'))
        adresse = valeur(l.get('Adresse'))
        site = valeur(l.get('Site_Web'))
        tel = valeur(l.get('Telephone'))
        email = valeur(l.get('Email'))

        if not nom:
            continue
        if any(m in nom.lower() for m in MOTS_A_EXCLURE):
            ignorees.append((nom, "profil freelance, pas une entreprise"))
            continue
        if not est_a_marrakech(adresse):
            ignorees.append((nom, f"hors Marrakech ({adresse[:45]})"))
            continue

        k_nom, k_site, k_tel = cle_nom(nom), cle_site(site), cle_tel(tel)
        if k_nom in noms:
            ignorees.append((nom, "déjà dans la base (même nom)"))
            continue
        if k_site and k_site in sites:
            ignorees.append((nom, "déjà dans la base (même site web)"))
            continue
        if k_tel and k_tel in tels:
            ignorees.append((nom, "déjà dans la base (même téléphone)"))
            continue

        sous = valeur(l.get('Sous_Domaine')).lower()
        domaine = CORRESPONDANCE_DOMAINES.get(sous, DOMAINE_PAR_DEFAUT)
        note = nombre(l.get('Rating'))
        nb_avis = nombre(l.get('Nb_Avis'))
        nb_avis = int(nb_avis) if nb_avis is not None else None
        score, priorite = calculer_score(domaine, note, nb_avis, bool(site), bool(tel))

        a_ajouter.append({
            'nom_entreprise': nom,
            'secteur': SECTEUR,
            'domaine': domaine,
            'titre_poste': 'Candidature spontanée - Stage',
            'type_source': 'Google Places API',
            'adresse': adresse,
            'ville': VILLE,
            'note_entreprise': note,
            'nb_avis': nb_avis,
            'type_contrat': 'Stage',
            'score_total': score,
            'priorite': priorite,
            'statut_candidature': 'À préparer',
            'date_contact': '',
            'notes_perso': '',
            'lien': site,
            'recherche_linkedin': 'https://www.linkedin.com/search/results/people/?keywords='
                                  + quote(f"{nom} recrutement", safe=''),
            'email': email,
            'site_web': site,
            'telephone': tel,
        })
        # évite aussi les doublons à l'intérieur du fichier Excel
        noms.add(k_nom)
        if k_site: sites.add(k_site)
        if k_tel: tels.add(k_tel)

    # ---------------- Rapport ----------------
    print("=" * 60)
    print("MODE :", "AJOUT RÉEL" if appliquer else "SIMULATION (rien n'est écrit)")
    print("=" * 60)
    print(f"Lignes lues dans l'Excel        : {len(lignes)}")
    print(f"Entreprises à ajouter           : {len(a_ajouter)}")
    print(f"Entreprises ignorées            : {len(ignorees)}")
    print(f"Entreprises dans la base avant  : {total_avant}")
    print(f"Entreprises dans la base après  : {total_avant + len(a_ajouter)}")

    if a_ajouter:
        print("\nRépartition par domaine :")
        for d in sorted({e['domaine'] for e in a_ajouter}):
            print(f"  {d} : {sum(1 for e in a_ajouter if e['domaine'] == d)}")
        print("\nRépartition par priorité :")
        for p in ('Haute', 'Moyenne', 'Basse'):
            n = sum(1 for e in a_ajouter if e['priorite'] == p)
            if n:
                print(f"  {p} : {n}")
        print("\nQuelques exemples :")
        for e in a_ajouter[:5]:
            print(f"  - {e['nom_entreprise'][:55]} | {e['domaine']} | score {e['score_total']} | {e['priorite']}")

    if ignorees:
        print("\nIgnorées :")
        for nom, raison in ignorees:
            print(f"  - {nom[:60]} -> {raison}")

    if not appliquer:
        print("\nAucune modification faite. Si le rapport te convient, lance :")
        print("  python importer_entreprises.py --appliquer")
        conn.close()
        return

    if not a_ajouter:
        print("\nRien à ajouter.")
        conn.close()
        return

    # ---------------- Sauvegarde puis ajout ----------------
    horodatage = datetime.now().strftime('%Y%m%d_%H%M%S')
    sauvegarde = os.path.join(BASE, 'database', f'career_finder_sauvegarde_{horodatage}.db')
    destination = sqlite3.connect(sauvegarde)
    conn.backup(destination)
    destination.close()
    print(f"\nSauvegarde créée : {sauvegarde}")

    colonnes = list(a_ajouter[0].keys())
    requete = (f"INSERT INTO companies ({', '.join(colonnes)}) "
               f"VALUES ({', '.join('?' for _ in colonnes)})")
    with conn:
        conn.executemany(requete, [tuple(e[c] for c in colonnes) for e in a_ajouter])

    total_apres = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    print(f"Ajout terminé : {len(a_ajouter)} entreprises ajoutées. Total dans la base : {total_apres}.")
    conn.close()


if __name__ == '__main__':
    main()