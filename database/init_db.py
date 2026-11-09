import sqlite3
import os
import re
from urllib.parse import quote

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), 'career_finder.db')
EXCEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed',
                          'entreprises_marrakech (1).xlsx')
SHEET = 'Nettoye'


def deviner_domaine(nom, type_principal):
    t = f"{nom} {type_principal}".lower()
    if re.search(r"\bia\b|intelligence artificielle|data|machine learning|\bai\b", t):
        return "IA / Data"
    if re.search(r"web|digital|digitale|seo|e-?commerce|marketing|communication|ux|ui\b|design", t):
        return "Web & Digital"
    if re.search(r"logiciel|software|dev|erp|application|mobile|solutions|soft", t):
        return "Développement logiciel"
    if re.search(r"réseau|reseau|télécom|telecom|cyber|sécurité|securite|cloud|hébergement", t):
        return "Réseaux & Cybersécurité"
    if re.search(r"matériel|materiel|vente|store|accessoires|maintenance|réparation|reparatel", t):
        return "Matériel & Maintenance IT"
    return "Services informatiques"


def calculer_score(r):
    score = 40
    if r['email']:
        score += 25
    if r['site_web']:
        score += 15
    if r['telephone']:
        score += 5
    if r['domaine'] in ("IA / Data", "Développement logiciel"):
        score += 15
    elif r['domaine'] in ("Web & Digital", "Réseaux & Cybersécurité"):
        score += 8
    return float(min(score, 100))


def priorite(score):
    return "Haute" if score >= 75 else "Moyenne" if score >= 55 else "Basse"


def charger_entreprises():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET).fillna('')
    for col in ['entreprise', 'type_principal', 'adresse', 'telephone', 'email',
                'site_web', 'source', 'lien_google_maps']:
        if col not in df.columns:
            df[col] = ''
    out = pd.DataFrame()
    out['nom_entreprise'] = df['entreprise'].astype(str).str.strip()
    out['domaine'] = [deviner_domaine(n, t) for n, t in zip(df['entreprise'], df['type_principal'])]
    out['secteur'] = 'Informatique & Digital'
    out['titre_poste'] = 'Candidature spontanée - Stage'
    out['type_source'] = df['source']
    out['adresse'] = df['adresse']
    out['ville'] = 'Marrakech'
    out['note_entreprise'] = None
    out['nb_avis'] = None
    out['type_contrat'] = 'Stage'
    out['email'] = df['email']
    out['site_web'] = df['site_web']
    out['telephone'] = df['telephone']
    out['score_total'] = [calculer_score(r) for r in out.to_dict('records')]
    out['priorite'] = out['score_total'].apply(priorite)
    out['statut_candidature'] = 'À préparer'
    out['date_contact'] = ''
    out['notes_perso'] = ''
    out['lien'] = df['site_web'].where(df['site_web'] != '', df['lien_google_maps'])
    out['recherche_linkedin'] = ["https://www.linkedin.com/search/results/people/?keywords="
                                 + quote(f"{n} recrutement") for n in out['nom_entreprise']]
    return out[out['nom_entreprise'] != ''].drop_duplicates('nom_entreprise')


def creer_base():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_entreprise TEXT NOT NULL,
            secteur TEXT,
            domaine TEXT,
            titre_poste TEXT,
            type_source TEXT,
            adresse TEXT,
            ville TEXT,
            note_entreprise REAL,
            nb_avis INTEGER,
            type_contrat TEXT,
            score_total REAL,
            priorite TEXT,
            statut_candidature TEXT,
            date_contact TEXT,
            notes_perso TEXT,
            lien TEXT,
            recherche_linkedin TEXT
        )
    ''')

    # Nouvelles colonnes (ajoutées seulement si la base est ancienne)
    existantes = {row[1] for row in cursor.execute("PRAGMA table_info(companies)")}
    for col in ('email', 'site_web', 'telephone'):
        if col not in existantes:
            cursor.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            mot_de_passe TEXT NOT NULL,
            date_creation TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            statut TEXT DEFAULT 'À préparer',
            date_candidature TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom_fichier TEXT,
            texte_extrait TEXT,
            email_detecte TEXT,
            telephone_detecte TEXT,
            date_upload TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()

    # Remplacement des anciennes entreprises (les comptes users et les CV sont conservés).
    # Les anciennes candidatures pointent vers d'anciens id : elles sont donc supprimées.
    cursor.execute("DELETE FROM applications")
    cursor.execute("DELETE FROM companies")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('companies', 'applications')")
    conn.commit()

    df = charger_entreprises()
    df.to_sql('companies', conn, if_exists='append', index=False)
    conn.commit()

    total = cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    print(f"{total} entreprises importées dans la table 'companies'.")
    for dom, n in cursor.execute(
            "SELECT domaine, COUNT(*) FROM companies GROUP BY domaine ORDER BY 2 DESC"):
        print(f"  - {dom}: {n}")
    for p, n in cursor.execute(
            "SELECT priorite, COUNT(*) FROM companies GROUP BY priorite ORDER BY 2 DESC"):
        print(f"  priorité {p}: {n}")
    print("Avec email :", cursor.execute("SELECT COUNT(*) FROM companies WHERE email != ''").fetchone()[0])
    conn.close()

if __name__ == '__main__':
    creer_base()
