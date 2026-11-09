import sqlite3

chemin = "database/career_finder.db"
con = sqlite3.connect(chemin)
cur = con.cursor()

for (table,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"\n=== {table} ({n} lignes) ===")
    for col in cur.execute(f"PRAGMA table_info({table})").fetchall():
        print("  ", col[1], col[2])

con.close()