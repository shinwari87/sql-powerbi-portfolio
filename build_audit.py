"""Build the AI quality audit dashboard, preview, and portable Power BI project."""
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

from build_powerbi import pbir, visual, write

BASE = Path(__file__).resolve().parents[1]
CASE = BASE / "ai-quality-audit"
OUT = CASE / "power-bi"
TABLE = "Scenarios"
MEASURES = {
    "Scenario count": ("COALESCE(COUNTROWS(Scenarios), 0)", "#,0"),
    "A passes": ('COALESCE(CALCULATE(COUNTROWS(Scenarios), KEEPFILTERS(Scenarios[a_result] = "Pass")), 0)', "#,0"),
    "B passes": ('COALESCE(CALCULATE(COUNTROWS(Scenarios), KEEPFILTERS(Scenarios[b_result] = "Pass")), 0)', "#,0"),
    "A failures": ("[Scenario count] - [A passes]", "#,0"),
    "B failures": ("[Scenario count] - [B passes]", "#,0"),
    "A pass rate": ("DIVIDE([A passes], [Scenario count])", "0.0%"),
    "B pass rate": ("DIVIDE([B passes], [Scenario count])", "0.0%"),
    "Pass rate change": ("[B pass rate] - [A pass rate]", "+0.0%;-0.0%;0.0%"),
    "Improved": ('COALESCE(CALCULATE(COUNTROWS(Scenarios), KEEPFILTERS(Scenarios[change] = "Improved")), 0)', "#,0"),
    "Regressed": ('COALESCE(CALCULATE(COUNTROWS(Scenarios), KEEPFILTERS(Scenarios[change] = "Regressed")), 0)', "#,0"),
    "Net change": ("[B passes] - [A passes]", "+#,0;-#,0;0"),
}

def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))

def embed_model(rows):
    # All columns are text; one M expression line per scenario keeps diffs readable.
    fields = list(rows[0])
    header = ", ".join(k + " = nullable text" for k in fields)
    expression = ["#table(type table [" + header + "], {"]
    for i, row in enumerate(rows):
        values = ['"' + row[k].replace('"', '""') + '"' for k in fields]
        expression.append("    {" + ", ".join(values) + "}" + ("," if i + 1 < len(rows) else ""))
    expression.append("})")
    return {
        "name": TABLE,
        "columns": [{"name": k, "dataType": "string", "sourceColumn": k} for k in fields],
        "partitions": [{"name": "Snapshot", "mode": "import", "source": {"type": "m", "expression": expression}}],
        "measures": [{"name": k, "expression": v, "formatString": fmt} for k, (v, fmt) in MEASURES.items()]
    }

def power_bi(rows):
    report = OUT / "Audit.Report"
    model = OUT / "Audit.SemanticModel"
    write(OUT / "Audit.pbip", {"version": "1.0", "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
    write(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": "../" + model.name}}})
    write(model / "definition.pbism", {"version": "1.0", "settings": {}})
    write(model / "model.bim", {"name": "Audit", "compatibilityLevel": 1550, "model": {"culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3", "tables": [embed_model(rows)]}})
    definition = report / "definition"
    pbir(definition / "version.json", "versionMetadata", version="2.0.0")
    pbir(definition / "report.json", "report", layoutOptimization="None", themeCollection={})
    names = ["b41c7d2e9f05a6c3d8e1", "7a9e3c1d5b2f4e8a6c0d"]
    pbir(definition / "pages/pages.json", "pagesMetadata", pageOrder=names, activePageName=names[0])
    summary, detail = [definition / "pages" / name for name in names]
    for page, title in [(summary, "Version comparison"), (detail, "Failure detail")]:
        pbir(page / "page.json", "page", name=page.name, displayName=title, displayOption="FitToPage", width=1280, height=720)
    def add(page, name, typ, rect, roles, order):
        visual(page, name, typ, rect, roles, order, table=TABLE, measures=MEASURES)
    for i, measure in enumerate(["A pass rate", "B pass rate", "Improved", "Regressed"]):
        add(summary, "kpi" + str(i), "card", (12 + i * 315, 14, 306, 116), {"Values": [measure]}, i)
    add(summary, "topicslicer", "slicer", (12, 150, 221, 240), {"Values": ["topic"]}, 4)
    add(summary, "bytopic", "clusteredBarChart", (250, 150, 1010, 240), {"Category": ["topic"], "Y": ["A pass rate", "B pass rate"]}, 5)
    add(summary, "scorecard", "tableEx", (12, 410, 1248, 280), {"Values": ["topic", "Scenario count", "A pass rate", "B pass rate", "Improved", "Regressed", "Net change", "Pass rate change"]}, 6)
    add(detail, "topic", "slicer", (12, 12, 386, 120), {"Values": ["topic"]}, 0)
    add(detail, "change", "slicer", (414, 12, 386, 120), {"Values": ["change"]}, 1)
    add(detail, "failuretype", "slicer", (816, 12, 444, 120), {"Values": ["b_failure_type"]}, 2)
    add(detail, "scenarios", "tableEx", (12, 153, 1252, 530), {"Values": ["scenario_id", "topic", "change", "b_failure_type", "customer_message", "a_response", "b_response", "b_note"]}, 3)

def preview(rows, topics, rates):
    def label(x, y, s, size, fill="#20262b", weight="400", anchor="start"):
        return f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(str(s))}</text>'
    def rect(x, y, w, h, color, r=0):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}"/>'
    a, b = [r for r in rates if r["version"] == "A"][0], [r for r in rates if r["version"] == "B"][0]
    improved = sum(r["change"] == "Improved" for r in rows)
    regressed = sum(r["change"] == "Regressed" for r in rows)
    metrics = [("Version A pass rate", a["pass_pct"] + "%"), ("Version B pass rate", b["pass_pct"] + "%"),
               ("Improved / regressed", f"{improved} / {regressed}")]
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 560" role="img"><title>AI answer quality audit: pass rate by topic for two assistant versions</title>',
           rect(0, 0, 1000, 560, "#f4f3ef"), rect(0, 0, 1000, 105, "#2d2a4a"),
           label(30, 49, "AI answer quality audit", 34, "#ffffff", "700"),
           label(31, 79, f"{len(rows)} simulated support scenarios graded for two assistant versions", 16, "#d8d4ea")]
    for i, (k, v) in enumerate(metrics):
        x = 30 + i * 317
        out.extend([rect(x, 125, 307, 85, "#ffffff", 5), label(x + 14, 151, k, 16, "#565b73"), label(x + 14, 191, v, 31, "#2d2a4a", "700")])
    out.extend([label(30, 253, "Pass rate by topic", 22, weight="700"),
                label(30, 278, "Purple = version A (baseline). Green = version B (candidate). Bars run from 0 to 100%.", 15, "#565b73")])
    ordered = sorted(topics, key=lambda r: int(r["net_change"]))
    for i, r in enumerate(ordered):
        y = 305 + i * 36
        ra, rb = float(r["a_pass_pct"]), float(r["b_pass_pct"])
        net = int(r["net_change"])
        out.extend([label(32, y + 14, r["topic"], 16),
                    rect(230, y, 420, 9, "#e4e2ea", 4), rect(230, y, round(4.2 * ra, 1), 9, "#5b57a0", 4),
                    rect(230, y + 12, 420, 9, "#e4e2ea", 4), rect(230, y + 12, round(4.2 * rb, 1), 9, "#2f8f6a", 4),
                    label(665, y + 14, f"{ra:.0f}% to {rb:.0f}%", 16, weight="700"),
                    label(820, y + 14, f"{net:+d} net" + (f", {r['regressed']} regressed" if int(r["regressed"]) else ""), 15, "#b1402d" if net < 0 else "#565b73")])
    out.extend([label(30, 540, "Nasratullah Shinwari  /  SQL and Power BI  /  Simulated data", 14, "#565b73"), "</svg>"])
    (CASE / "preview.svg").write_text("\n".join(out), encoding="utf-8")

def main():
    rows = read_rows(CASE / "results/scenario_comparison.csv")
    topics = read_rows(CASE / "results/topic_scorecard.csv")
    rates = read_rows(CASE / "results/version_pass_rate.csv")
    versions = read_rows(CASE / "data/versions.csv")
    payload = json.dumps({"versions": versions, "rows": rows}, separators=(",", ":")).replace("<", "\\u003c")
    template = (BASE / "tools/audit_dashboard.html.in").read_text(encoding="utf-8")
    (CASE / "dashboard.html").write_text(template.replace("{{PAYLOAD}}", payload), encoding="utf-8")
    preview(rows, topics, rates)
    power_bi(rows)

if __name__ == "__main__":
    main()
