
import os
import sqlite3
import psycopg
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
SQLITE_PATH = BASE_DIR / "database" / "career_finder.db"

load_dotenv(Path(__file__).parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

TABLES = [
    "companies",
    "users",
    "applications",
    "cv",
    "favorites",
    "assistant_messages",
]

if not DATABASE_URL:
    print("ERREUR : DATABASE_URL introuvable")
    raise SystemExit

try:
    # SQLite en lecture seule
    sqlite_conn = sqlite3.connect(
        f"file:{SQLITE_PATH.as_posix()}?mode=ro",
        uri=True
    )

    with psycopg.connect(DATABASE_URL, connect_timeout=15) as pg_conn:
        print("COMPARAISON SQLITE / NEON")
        print("=" * 45)

        total = 0
        erreurs = 0

        for table in TABLES:
            sqlite_cur = sqlite_conn.execute(
                f'SELECT * FROM "{table}" ORDER BY id'
            )
            sqlite_rows = sqlite_cur.fetchall()
            columns = [col[0] for col in sqlite_cur.description]

            with pg_conn.cursor() as pg_cur:
                pg_cur.execute(
                    f'SELECT * FROM "{table}" ORDER BY id'
                )
                neon_rows = pg_cur.fetchall()

            if len(sqlite_rows) != len(neon_rows):
                print(f"\nERREUR {table}: nombres differents")
                erreurs += 1
                continue

            differences = []

            for index, (row_sqlite, row_neon) in enumerate(
                zip(sqlite_rows, neon_rows)
            ):
                for col_index, column in enumerate(columns):
                    value_sqlite = row_sqlite[col_index]
                    value_neon = row_neon[col_index]

                    if value_sqlite != value_neon:
                        differences.append(
                            f"Ligne ID {row_sqlite[0]}, colonne {column}"
                        )

            if differences:
                print(f"\nDIFFERENCES dans {table}:")
                for difference in differences[:5]:
                    print("-", difference)
                erreurs += 1
            else:
                print(
                    f"OK - {table}: {len(sqlite_rows)} lignes identiques"
                )
                total += len(sqlite_rows)

        print("\n" + "=" * 45)
        print("Total de lignes identiques :", total)
        print("Tables avec differences :", erreurs)

        if erreurs == 0:
            print("SUCCES : toutes les donnees sont identiques !")
        else:
            print("ATTENTION : verification supplementaire necessaire.")

    sqlite_conn.close()

except Exception as e:
    print("ERREUR :", e)
