"""Behavior tests for accounting grain, reporting cutoffs, and Power BI references."""
import json
import unittest
from run import ROOT, load

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.db=load("project-delivery")
        self.addCleanup(self.db.close)

    def test_costs_not_duplicated_or_postdated(self):
        total=self.db.execute("SELECT SUM(spend_usd) FROM portfolio").fetchone()[0]
        self.assertEqual(total,2290000)
        self.db.execute("INSERT INTO milestones VALUES ('Extra','P01','Extra review','2026-09-30',NULL)")
        self.assertEqual(self.db.execute("SELECT SUM(spend_usd) FROM portfolio").fetchone()[0],total)
        status=self.db.execute("SELECT status_at_cutoff FROM milestone_status WHERE milestone_id='Extra'").fetchone()[0]
        self.assertEqual(status,"Due today")

    def test_completion_after_cutoff_is_open(self):
        self.db.execute("UPDATE milestones SET due_on='2026-09-15', completed_on='2026-10-03' WHERE milestone_id='M64'")
        status=self.db.execute("SELECT status_at_cutoff FROM milestone_status WHERE milestone_id='M64'").fetchone()[0]
        self.assertEqual(status,"Overdue")

    def test_idle_project_survives(self):
        self.db.execute("INSERT INTO projects VALUES ('P07','New program','Technology',110000)")
        row=self.db.execute("SELECT spend_usd, milestones, overdue FROM portfolio WHERE project_id='P07'").fetchone()
        self.assertEqual(tuple(row),(0,0,0))

class EconomicsTests(unittest.TestCase):
    def setUp(self):
        self.db=load("marketplace-profit")
        self.addCleanup(self.db.close)

    def test_reconcile_to_raw_ledgers(self):
        def total(query):
            return self.db.execute(query).fetchone()[0]
        baseline=total("SELECT SUM(quantity*(unit_price_cents-unit_cost_cents)) FROM order_lines")
        costs=total("SELECT SUM(amount_cents) FROM line_charges")+total("SELECT SUM(spend_cents) FROM advertising")
        self.assertEqual(total("SELECT SUM(contribution) FROM product_month"),baseline-costs)
        self.assertEqual(total("SELECT SUM(gross) FROM product_month"),total("SELECT SUM(unit_price_cents*quantity) FROM order_lines"))

    def test_multi_charge_refund_counts_once(self):
        before=self.db.execute("SELECT SUM(contribution),SUM(net_sales),SUM(gross) FROM product_month").fetchone()
        self.db.execute("INSERT INTO line_charges VALUES ('Extra','L0001','refund',125)")
        after=self.db.execute("SELECT SUM(contribution),SUM(net_sales),SUM(gross) FROM product_month").fetchone()
        self.assertEqual([a-b for a,b in zip(after,before)],[-125,-125,0])

    def test_ad_only_period_is_a_loss(self):
        self.db.execute("INSERT INTO advertising VALUES ('2026-10','T12',2000)")
        row=self.db.execute("SELECT net_sales, contribution FROM product_month WHERE month='2026-10'").fetchone()
        self.assertEqual(tuple(row),(0,-2000))

class BiTests(unittest.TestCase):
    def test_all_report_fields_exist_in_model(self):
        root=ROOT/'project-delivery/power-bi'
        report=root/json.loads((root/'Delivery.pbip').read_text())['artifacts'][0]['report']['path']
        model=report/json.loads((report/'definition.pbir').read_text())['datasetReference']['byPath']['path']
        table=json.loads((model/'model.bim').read_text())['model']['tables'][0]
        for path in (report/'definition/pages').glob('*/visuals/*/visual.json'):
            query=json.loads(path.read_text())['visual']['query']['queryState']
            for role in query.values():
                for field in role['projections']:
                    kind,ref=next(iter(field['field'].items()))
                    self.assertEqual(ref['Expression']['SourceRef']['Entity'],table['name'])
                    members=table['measures' if kind=='Measure' else 'columns']
                    self.assertIn(ref['Property'],[m['name'] for m in members])

if __name__ == "__main__":
    unittest.main()
