"""Render standalone HTML dashboards from the SQL exports (standard library only)."""
import csv
import json
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
def rows(folder, table):
    with (folder / "results" / (table + ".csv")).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    template = (ROOT / "tools/dashboard.html.in").read_text(encoding="utf-8")
    for project, table, title, subtitle, choice in [
        ("project-delivery","portfolio","Project delivery review","Cost and schedule at the September 30, 2026 reporting cutoff.","Program"),
        ("marketplace-profit","product_month","Marketplace contribution","Order economics across July–September 2026, after refunds and variable costs.","Order month")
    ]:
        folder = ROOT / project
        payload = {"project":project, "rows":rows(folder,table)}
        page = template.replace("{{TITLE}}",escape(title)).replace("{{SUBTITLE}}",escape(subtitle)).replace("{{CHOICE}}",choice)
        page = page.replace("{{DATA}}",json.dumps(payload, ensure_ascii=True).replace("<","\\u003c"))
        (folder / "dashboard.html").write_text(page,encoding="utf-8")

if __name__ == "__main__":
    main()
