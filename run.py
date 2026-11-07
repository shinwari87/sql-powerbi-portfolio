"""Rebuild both portfolio analyses with the Python standard library."""
from pathlib import Path
import csv
import sqlite3

ROOT = Path(__file__).resolve().parent
PROJECTS = {
    "project-delivery": (
        ["projects", "report_settings", "costs", "milestones"],
        {"portfolio": "project_id", "milestone_status": "project_id, due_on"}
    ),
    "marketplace-profit": (
        ["products", "order_lines", "line_charges", "advertising"],
        {"product_month": "month, sku", "sku_ranking": "profit_rank, sku"}
    ),
}

def load(project):
    folder = ROOT / project
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript((folder / "sql/schema.sql").read_text())
    for table in PROJECTS[project][0]:
        with (folder / "data" / f"{table}.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            headers = next(reader)
            expected = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
            if headers != expected:
                raise ValueError(f"Unexpected columns in {table}: {headers}")
            params = ",".join("?" for _ in headers)
            rows = ([s if s != "" else None for s in row] for row in reader)
            db.executemany(f"INSERT INTO {table} VALUES ({params})", rows)
    db.executescript((folder / "sql/analysis.sql").read_text())
    return db

def build():
    for project, (_, views) in PROJECTS.items():
        db = load(project)
        for view, order in views.items():
            cur = db.execute(f"SELECT * FROM {view} ORDER BY {order}")
            rows = cur.fetchall()
            target = ROOT / project / "results" / f"{view}.csv"
            target.parent.mkdir(exist_ok=True)
            with target.open("w", newline="", encoding="utf-8") as stream:
                w = csv.writer(stream, lineterminator="\n")
                w.writerow([c[0] for c in cur.description])
                w.writerows(rows)
            print(f"{project}/{view}: {len(rows)} rows")
        db.close()

if __name__ == "__main__":
    build()
