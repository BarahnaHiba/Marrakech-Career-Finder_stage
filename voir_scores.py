import sqlite3

con = sqlite3.connect("database/career_finder.db")
cur = con.cursor()

print("Répartition des scores (toute la base) :")
for score, n in cur.execute(
    "SELECT score_total, COUNT(*) FROM companies GROUP BY score_total ORDER BY score_total DESC"
):
    print(f"  score {score} : {n} entreprises")

print("\nRépartition par priorité :")
for p, n in cur.execute("SELECT priorite, COUNT(*) FROM companies GROUP BY priorite"):
    print(f"  {p} : {n}")

con.close()