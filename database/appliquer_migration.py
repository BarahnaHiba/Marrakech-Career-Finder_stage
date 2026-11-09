"""
Applique une migration SQL sur la base définie par DATABASE_URL (Neon ou locale).

    python database/appliquer_migration.py database/migrations/001_harmonisation.sql

Avant d'exécuter, le script exporte les tables applications et cv en CSV dans
database/sauvegardes/ (jamais versionné par git) pour que rien ne soit perdu.
"""
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / "backend" / ".env")


def sauvegarder(conn):
    dossier = RACINE / "database" / "sauvegardes"
    dossier.mkdir(exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    for table in ("applications", "cv"):
        cur = conn.execute(f"SELECT * FROM {table}")  # noms fixes, pas d'entrée utilisateur
        colonnes = [c.name for c in cur.description]
        chemin = dossier / f"{table}_{horodatage}.csv"
        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(colonnes)
            w.writerows(cur.fetchall())
        print(f"Sauvegarde : {chemin}")


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage : python database/appliquer_migration.py <fichier.sql>")
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL introuvable (backend/.env ou variable d'environnement).")
    sql = Path(sys.argv[1]).read_text(encoding="utf-8")
    with psycopg.connect(url, autocommit=True) as conn:
        sauvegarder(conn)
        conn.execute(sql)
    print("Migration appliquée.")


if __name__ == "__main__":
    main()
