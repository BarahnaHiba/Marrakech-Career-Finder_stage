import os
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'career_finder.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== STRUCTURE DE LA TABLE companies ===")
print(conn.execute("SELECT sql FROM sqlite_master WHERE name = 'companies'").fetchone()[0])

total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
print("\n=== NOMBRE D'ENTREPRISES ===")
print(total)

print("\n=== SECTEURS ===")
for r in conn.execute("SELECT secteur, COUNT(*) n FROM companies GROUP BY secteur ORDER BY n DESC"):
    print(f"  {r['secteur']} : {r['n']}")

print("\n=== DOMAINES ===")
for r in conn.execute("SELECT domaine, COUNT(*) n FROM companies GROUP BY domaine ORDER BY n DESC"):
    print(f"  {r['domaine']} : {r['n']}")

print("\n=== PRIORITES ===")
for r in conn.execute("SELECT priorite, COUNT(*) n, MIN(score_total) mini, MAX(score_total) maxi "
                      "FROM companies GROUP BY priorite ORDER BY maxi DESC"):
    print(f"  {r['priorite']} : {r['n']} entreprises (score de {r['mini']} à {r['maxi']})")

print("\n=== VILLES ===")
for r in conn.execute("SELECT ville, COUNT(*) n FROM companies GROUP BY ville ORDER BY n DESC"):
    print(f"  {r['ville']} : {r['n']}")

print("\n=== 3 EXEMPLES COMPLETS ===")
for r in conn.execute("SELECT * FROM companies ORDER BY id LIMIT 3"):
    print(dict(r))
    print()

conn.close()