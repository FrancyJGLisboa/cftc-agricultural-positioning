import unittest
from datetime import date,timedelta
from analytics import enrich,midrank,five_years_before,driver,diagnostic

def row(d,L,S,oi=1000):
    return dict(report_date=d,market_code='x',commodity='Test',long_contracts=L,short_contracts=S,net_contracts=L-S,open_interest_contracts=oi)

class MetricsTests(unittest.TestCase):
    def test_percentile_ties_and_tails(self):
        self.assertEqual(midrank(2,[1,2,2,3]),50)
        self.assertEqual(midrank(0,[1,2,2,3]),0)
        self.assertEqual(midrank(4,[1,2,2,3]),100)
        self.assertEqual(midrank(1,[1,1,1]),50)
    def test_calendar_leap_day(self):
        self.assertEqual(five_years_before(date(2024,2,29)),date(2019,2,28))
    def test_same_net_change_different_mechanisms(self):
        a=enrich([row('2026-01-06',100,80),row('2026-01-13',120,80)])[-1]
        b=enrich([row('2026-01-06',100,80),row('2026-01-13',100,60)])[-1]
        self.assertEqual(a['net_change_since_previous_report'],b['net_change_since_previous_report'])
        self.assertEqual(a['decomposition_driver'],'increasing longs')
        self.assertEqual(b['decomposition_driver'],'decreasing shorts')
    def test_opposing_contributions_and_flat_offset(self):
        r=enrich([row('2026-01-06',100,80),row('2026-01-13',120,90)])[-1]
        self.assertEqual((r['long_contribution_contracts'],r['short_contribution_contracts'],r['net_change_since_previous_report']),(20,-10,10))
        self.assertEqual(driver(20,-20,0),'offsetting contributions')
        self.assertEqual(driver(-10,-20,-30),'increasing shorts')
    def test_open_interest_zero_and_signed(self):
        r=enrich([row('2026-01-06',0,0,0),row('2026-01-13',10,40,100)])
        self.assertIsNone(r[0]['net_pct_open_interest']);self.assertEqual(r[1]['net_pct_open_interest'],-30)
        self.assertIsNone(r[1]['net_change_pct_previous_oi'])
    def test_streak_flat_reversal(self):
        start=date(2026,1,6);values=[0,10,20,30,30,20,10,20]
        rs=enrich([row((start+timedelta(days=7*i)).isoformat(),100+n,100) for i,n in enumerate(values)])
        self.assertEqual([r['persistence_reports'] for r in rs],[None,1,2,3,0,1,2,1])
        self.assertTrue(rs[3]['persistence_at_least']);self.assertFalse(rs[-1]['persistence_at_least'])
    def test_streak_gap(self):
        r=enrich([row('2026-01-06',100,80),row('2026-01-13',110,80),row('2026-02-03',120,80),row('2026-02-10',130,80)])
        self.assertIsNone(r[2]['persistence_reports']);self.assertEqual(r[3]['persistence_reports'],1)
        self.assertTrue(r[3]['persistence_at_least'])
    def test_insufficient_history(self):
        r=enrich([row('2026-01-06',100,80),row('2026-01-13',120,80)])[-1]
        self.assertIsNone(r['net_percentile_5y']);self.assertEqual(r['percentile_reference_n'],1)
    def test_point_in_time_and_calendar_window(self):
        start=date(2020,1,7)
        rows=[row((start+timedelta(days=i*7)).isoformat(),100+i,80,10000) for i in range(280)]
        before=enrich(rows[:-1]);after=enrich(rows)
        self.assertEqual(before,after[:-1])
        r=after[-1];self.assertEqual(r['net_percentile_5y'],100)
        self.assertLessEqual(r['percentile_reference_n'],262)
        self.assertLess(r['percentile_reference_last'],r['report_date'])
        self.assertGreaterEqual(r['percentile_reference_first'],r['percentile_window_start'])
    def test_reference_does_not_include_current(self):
        start=date(2020,1,7)
        rows=[row((start+timedelta(days=i*7)).isoformat(),100,80) for i in range(270)]
        rows[-1]['long_contracts']=110;rows[-1]['net_contracts']=30
        self.assertEqual(enrich(rows)[-1]['net_percentile_5y'],100)
    def test_flags_respect_sign(self):
        start=date(2020,1,7)
        rs=[row((start+timedelta(days=7*i)).isoformat(),100,300-i//2) for i in range(270)]
        r=enrich(rs)[-1];d=diagnostic(r)
        self.assertLess(r['net_contracts'],0)
        self.assertNotIn('long exposure',d['research_question'])
    def test_duplicate_key_rejected(self):
        r=row('2026-01-06',100,80)
        with self.assertRaises(ValueError):enrich([r,r])

if __name__=='__main__':unittest.main()
