import os
import sqlite3

RACINE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RACINE, 'database', 'career_finder.db')

conn = sqlite3.connect(DB)

print("Colonnes de la table companies :")
print(" ", [r[1] for r in conn.execute("PRAGMA table_info(companies)")])

total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
print("\nTotal d'entreprises dans la base :", total)

print("\nPar secteur :")
for secteur, n in conn.execute("SELECT secteur, COUNT(*) FROM companies GROUP BY secteur ORDER BY 2 DESC"):
    print(f"  {n:4d}  {secteur}")

print("\nPar domaine (les 15 plus fréquents) :")
for domaine, n in conn.execute("SELECT domaine, COUNT(*) FROM companies GROUP BY domaine ORDER BY 2 DESC LIMIT 15"):
    print(f"  {n:4d}  {domaine}")

print("\nPar ville :")
for ville, n in conn.execute("SELECT ville, COUNT(*) FROM companies GROUP BY ville ORDER BY 2 DESC"):
    print(f"  {n:4d}  {ville}")

avec_email = conn.execute(
    "SELECT COUNT(*) FROM companies WHERE email IS NOT NULL AND TRIM(email) != ''").fetchone()[0]
print("\nEntreprises avec une adresse email :", avec_email)
conn.close()

print("\nFichiers dans les dossiers de données :")
for dossier in ('data', 'DATA SUR EXCEL'):
    chemin = os.path.join(RACINE, dossier)
    if not os.path.isdir(chemin):
        print(f"  (dossier « {dossier} » introuvable)")
        continue
    for repertoire, _, fichiers in os.walk(chemin):
        for f in fichiers:
            p = os.path.join(repertoire, f)
            print(f"  {os.path.relpath(p, RACINE)}  ({os.path.getsize(p) // 1024} Ko)")