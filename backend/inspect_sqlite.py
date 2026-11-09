
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "career_finder.db"
REPORT_PATH = Path(__file__).parent / "schema_report.txt"

if not DB_PATH.exists():
    print("ERREUR: Base SQLite introuvable :", DB_PATH)
    raise SystemExit(1)

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()

    tables = cursor.execute("""
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    lines = []
    lines.append("RAPPORT DE LA BASE SQLITE\n")
    lines.append(f"Nombre de tables : {len(tables)}\n")

    for table_name, create_sql in tables:
        count = cursor.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

        lines.append("\n" + "=" * 60)
        lines.append(f"\nTABLE : {table_name}")
        lines.append(f"\nNombre de lignes : {count}")
        lines.append("\n\nSTRUCTURE :")
        lines.append(create_sql or "Non disponible")

        columns = cursor.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

        lines.append("\n\nCOLONNES :")
        for col in columns:
            lines.append(
                f"- {col[1]} | {col[2]} | NOT NULL={col[3]} | "
                f"PRIMARY KEY={col[5]}"
            )

        foreign_keys = cursor.execute(
            f'PRAGMA foreign_key_list("{table_name}")'
        ).fetchall()

        if foreign_keys:
            lines.append("\nRELATIONS :")
            for fk in foreign_keys:
                lines.append(str(fk))

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("Inspection terminée !")
    print("Nombre de tables :", len(tables))
    print("Rapport créé :", REPORT_PATH)
