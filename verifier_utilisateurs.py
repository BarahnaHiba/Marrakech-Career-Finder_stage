import os
import sqlite3

RACINE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(RACINE, 'database', 'career_finder.db')

conn = sqlite3.connect(DB_PATH)
colonnes = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
print("Colonnes de la table users :")
print(" ", colonnes)

print("\nUtilisateurs inscrits (sans mot de passe) :")
afficher = [c for c in ('id', 'nom', 'email') if c in colonnes]
lignes = conn.execute(f"SELECT {', '.join(afficher)} FROM users ORDER BY id").fetchall()
for ligne in lignes:
    print(" ", ligne)
print("\nTotal :", len(lignes))
conn.close()