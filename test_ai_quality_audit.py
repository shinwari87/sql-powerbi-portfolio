"""Checks for the AI answer quality audit: grain, reconciliation, rubric, dashboard, and Power BI."""
import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from run import ROOT, load

CASE = ROOT / "ai-quality-audit"

def read(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

class GrainTests(unittest.TestCase):
    def setUp(self):
        self.db = load("ai-quality-audit")
        self.addCleanup(self.db.close)

    def test_each_scenario_has_exactly_one_result_per_version(self):
        scenarios = self.db.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]
        self.assertGreaterEqual(scenarios, 60)
        for table in ("responses", "judgments"):
            per_version = self.db.execute(
                f"SELECT version, COUNT(*), COUNT(DISTINCT scenario_id) FROM {table} GROUP BY version").fetchall()
            self.assertEqual([tuple(r) for r in per_version], [("A", scenarios, scenarios), ("B", scenarios, scenarios)])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM scenario_comparison").fetchone()[0], scenarios)

    def test_duplicate_judgment_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO judgments VALUES ('S001','A','Pass','','')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO judgments VALUES ('S001','C','Pass','','')")

    def test_pass_rates_reconcile_to_counts(self):
        comparison = self.db.execute("SELECT * FROM scenario_comparison").fetchall()
        for row in self.db.execute("SELECT * FROM version_pass_rate"):
            key = "a_result" if row["version"] == "A" else "b_result"
            passed = sum(r[key] == "Pass" for r in comparison)
            self.assertEqual(row["passed"], passed)
            self.assertEqual(row["passed"] + row["failed"], row["scenarios"])
            self.assertEqual(row["scenarios"], len(comparison))
            self.assertEqual(row["pass_pct"], round(100 * passed / len(comparison), 1))
        topics = self.db.execute("SELECT * FROM topic_scorecard").fetchall()
        totals = self.db.execute("SELECT version, passed FROM version_pass_rate").fetchall()
        self.assertEqual(sum(t["a_passed"] for t in topics), dict(totals)["A"])
        self.assertEqual(sum(t["b_passed"] for t in topics), dict(totals)["B"])
        self.assertEqual(sum(t["scenarios"] for t in topics), len(comparison))
        for t in topics:
            self.assertEqual(t["net_change"], t["b_passed"] - t["a_passed"])
            self.assertEqual(t["a_pass_pct"], round(100 * t["a_passed"] / t["scenarios"], 1))
        changes = dict(self.db.execute("SELECT change, scenarios FROM change_summary").fetchall())
        self.assertEqual(sum(changes.values()), len(comparison))
        self.assertEqual(changes["Improved"] - changes["Regressed"], dict(totals)["B"] - dict(totals)["A"])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM regressions").fetchone()[0], changes["Regressed"])
        failures = self.db.execute("SELECT version, SUM(failures) FROM failure_breakdown GROUP BY version").fetchall()
        self.assertEqual(dict(failures), dict(self.db.execute("SELECT version, failed FROM version_pass_rate").fetchall()))

    def test_recorded_judgments_match_the_rubric(self):
        mismatches = self.db.execute("SELECT COUNT(*) FROM rubric_audit WHERE rubric_result <> recorded_result").fetchone()[0]
        self.assertEqual(mismatches, 0)
        self.db.execute("UPDATE responses SET response_text = replace(response_text, '30 days of delivery', '14 days of delivery') WHERE scenario_id='S002' AND version='A'")
        row = self.db.execute("SELECT rubric_result, recorded_result FROM rubric_audit WHERE scenario_id='S002' AND version='A'").fetchone()
        self.assertEqual(tuple(row), ("Fail", "Pass"))

    def test_regression_view_shows_both_answers(self):
        for row in self.db.execute("SELECT * FROM regressions"):
            self.assertNotEqual(row["a_response"], row["b_response"])
            self.assertTrue(row["b_note"])

class ReproducibilityTests(unittest.TestCase):
    def test_generator_rewrites_identical_files(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import build_audit_data
        with tempfile.TemporaryDirectory() as tmp:
            original = build_audit_data.ROOT
            build_audit_data.ROOT = Path(tmp)
            try:
                build_audit_data.build()
            finally:
                build_audit_data.ROOT = original
            for path in sorted((CASE / "data").glob("*.csv")):
                self.assertEqual((Path(tmp) / path.name).read_text(encoding="utf-8"), path.read_text(encoding="utf-8"), path.name)

class ReportTests(unittest.TestCase):
    def test_dashboard_payload_agrees_with_sql_results(self):
        html = (CASE / "dashboard.html").read_text(encoding="utf-8")
        start = html.index('<script id="source" type="application/json">') + len('<script id="source" type="application/json">')
        payload = json.loads(html[start:html.index("</script>", start)])
        rows = payload["rows"]
        comparison = read(CASE / "results/scenario_comparison.csv")
        self.assertEqual(rows, comparison)
        rates = {r["version"]: r for r in read(CASE / "results/version_pass_rate.csv")}
        for version, key in (("A", "a_result"), ("B", "b_result")):
            passed = sum(r[key] == "Pass" for r in rows)
            self.assertEqual(str(passed), rates[version]["passed"])
            self.assertEqual(f"{100 * passed / len(rows):.1f}", rates[version]["pass_pct"])
        changes = {r["change"]: int(r["scenarios"]) for r in read(CASE / "results/change_summary.csv")}
        self.assertEqual(sum(r["change"] == "Improved" for r in rows), changes["Improved"])
        self.assertEqual(sum(r["change"] == "Regressed" for r in rows), changes["Regressed"])
        for topic in read(CASE / "results/topic_scorecard.csv"):
            group = [r for r in rows if r["topic"] == topic["topic"]]
            self.assertEqual(str(len(group)), topic["scenarios"])
            self.assertEqual(str(sum(r["b_result"] == "Pass" for r in group)), topic["b_passed"])

    def test_power_bi_model_embeds_the_snapshot_and_visuals_reference_valid_fields(self):
        root = CASE / "power-bi"
        report = root / json.loads((root / "Audit.pbip").read_text())["artifacts"][0]["report"]["path"]
        model = report / json.loads((report / "definition.pbir").read_text())["datasetReference"]["byPath"]["path"]
        table = json.loads((model / "model.bim").read_text())["model"]["tables"][0]
        rows = read(CASE / "results/scenario_comparison.csv")
        self.assertEqual(len(table["partitions"][0]["source"]["expression"]) - 2, len(rows))
        self.assertEqual([c["name"] for c in table["columns"]], list(rows[0]))
        pages = report / "definition/pages"
        page_ids = json.loads((pages / "pages.json").read_text())["pageOrder"]
        self.assertEqual(len(page_ids), 2)
        for page in page_ids:
            visuals = list((pages / page / "visuals").glob("*/visual.json"))
            self.assertTrue(visuals)
            for file in visuals:
                roles = json.loads(file.read_text())["visual"]["query"]["queryState"]
                for role in roles.values():
                    for p in role["projections"]:
                        kind, field = next(iter(p["field"].items()))
                        target = table["measures" if kind == "Measure" else "columns"]
                        self.assertEqual(field["Expression"]["SourceRef"]["Entity"], table["name"])
                        self.assertIn(field["Property"], [x["name"] for x in target])

if __name__ == "__main__":
    unittest.main()
