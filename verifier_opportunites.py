import sqlite3

con = sqlite3.connect("database/career_finder.db")
cur = con.cursor()

print("Lignes avec un titre de poste :",
      cur.execute("SELECT COUNT(*) FROM companies WHERE titre_poste IS NOT NULL AND titre_poste != ''").fetchone()[0])

print("\nRépartition par type_source :")
for ligne in cur.execute("SELECT type_source, COUNT(*) FROM companies GROUP BY type_source"):
    print("  ", ligne)

print("\nRépartition par type_contrat :")
for ligne in cur.execute("SELECT type_contrat, COUNT(*) FROM companies GROUP BY type_contrat"):
    print("  ", ligne)

con.close()