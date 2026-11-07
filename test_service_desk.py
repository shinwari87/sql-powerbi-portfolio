"""Regression tests for historical ticket scoring and the service desk model."""
import json
import math
import unittest

from run import ROOT, load

class ServiceDeskTests(unittest.TestCase):
    def setUp(self):
        self.db = load("support-sla")
        self.addCleanup(self.db.close)

    def ticket(self, key):
        return self.db.execute("SELECT * FROM ticket_outcomes WHERE ticket_id=?", (key,)).fetchone()

    def test_nonhuman_and_future_events_do_not_stop_the_clock(self):
        self.assertEqual(self.ticket("SD-146")["outcome"], "Missed")
        self.assertIsNone(self.ticket("SD-146")["first_reply_utc"])
        self.assertEqual(self.ticket("SD-150")["outcome"], "Pending")
        self.assertIsNone(self.ticket("SD-153"))
        self.db.execute("INSERT INTO events VALUES ('early','SD-146','agent_reply','2026-10-01 09:00:00')")
        self.assertIsNone(self.ticket("SD-146")["first_reply_utc"])

    def test_exact_deadline_and_repeat_reply(self):
        t = self.ticket("SD-149")
        self.assertEqual(t["outcome"], "Met")
        self.assertEqual(t["wait_minutes"], t["target_minutes"])
        self.db.execute("DELETE FROM events WHERE ticket_id='SD-149' AND event_type='agent_reply'")
        self.assertEqual(self.ticket("SD-149")["outcome"], "Pending")
        self.db.execute("UPDATE snapshot SET cutoff_utc='2026-10-31 18:01:00'")
        self.assertEqual(self.ticket("SD-149")["outcome"], "Missed")
        self.db.executemany("INSERT INTO events VALUES (?,'SD-149','agent_reply',?)",
                            [('later','2026-10-31 18:01:00'),('ontime','2026-10-31 18:00:00')])
        self.assertEqual(self.ticket("SD-149")["outcome"], "Met")

    def test_queue_totals_and_percentiles_reconcile_to_ticket_grain(self):
        tickets = self.db.execute("SELECT * FROM ticket_outcomes").fetchall()
        self.assertEqual(len(tickets), len({r['ticket_id'] for r in tickets}))
        for summary in self.db.execute("SELECT * FROM queue_scorecard"):
            group = [t for t in tickets if t['queue']==summary['queue']]
            waits = sorted(t['wait_minutes'] for t in group if t['wait_minutes'] is not None)
            met = sum(t['outcome']=='Met' for t in group)
            missed = sum(t['outcome']=='Missed' for t in group)
            self.assertEqual(summary['pending'], len(group)-met-missed)
            self.assertEqual(summary['met_pct'], round(100*met/(met+missed),1))
            self.assertEqual(summary['p90_minutes'], waits[math.ceil(.9*len(waits))-1])

    def test_pending_only_queue_has_no_rate_or_percentile(self):
        self.db.execute("INSERT INTO tickets VALUES ('new','New queue','High','2026-10-31 18:00:00')")
        row=self.db.execute("SELECT * FROM queue_scorecard WHERE queue='New queue'").fetchone()
        self.assertIsNone(row['met_pct'])
        self.assertIsNone(row['p90_minutes'])
        self.assertEqual(row['pending'],1)

    def test_both_native_report_pages_use_valid_model_fields(self):
        root=ROOT/'support-sla/power-bi'
        report=root/json.loads((root/'Response.pbip').read_text())['artifacts'][0]['report']['path']
        model=report/json.loads((report/'definition.pbir').read_text())['datasetReference']['byPath']['path']
        table=json.loads((model/'model.bim').read_text())['model']['tables'][0]
        pages=report/'definition/pages'
        page_ids=json.loads((pages/'pages.json').read_text())['pageOrder']
        self.assertEqual(len(page_ids),2)
        count = self.db.execute("SELECT COUNT(*) FROM ticket_outcomes").fetchone()[0]
        self.assertEqual(len(table['partitions'][0]['source']['expression'])-2, count)
        for page in page_ids:
            visuals=list((pages/page/'visuals').glob('*/visual.json'))
            self.assertTrue(visuals)
            for file in visuals:
                roles=json.loads(file.read_text())['visual']['query']['queryState']
                for role in roles.values():
                    for p in role['projections']:
                        kind,field=next(iter(p['field'].items()))
                        target=table['measures' if kind=='Measure' else 'columns']
                        self.assertEqual(field['Expression']['SourceRef']['Entity'],table['name'])
                        self.assertIn(field['Property'],[x['name'] for x in target])

if __name__=='__main__':
    unittest.main()
