"""Independent numerical cases and source/state boundary checks for edition 2."""
import copy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from analytics import enrich, seasonality, seasonal_week
from cftc_positioning import MARKETS, REPORTS, validate
from units import SPECS, tonnes_per_contract, value
import radar
from test_analytics import row
from test_pipeline import snapshot


def managed_snapshot(d='2026-01-06'):
    rows=[]
    for code in MARKETS:
        qty,unit,_=SPECS[code]
        rows.append(dict(report_date_as_yyyy_mm_dd=d+'T00:00:00.000',cftc_contract_market_code=code,
            market_and_exchange_names='SYNTHETIC TEST RECORD',futonly_or_combined='FutOnly',
            contract_units=f'(CONTRACTS OF {qty:,} {unit})',open_interest_all='1000',
            m_money_positions_long_all='100',m_money_positions_short_all='80',m_money_positions_spread='20',
            prod_merc_positions_long='500',prod_merc_positions_short='600',
            swap_positions_long_all='100',swap__positions_short_all='50',swap__positions_spread_all='30',
            other_rept_positions_long='80',other_rept_positions_short='50',other_rept_positions_spread='40',
            nonrept_positions_long_all='130',nonrept_positions_short_all='130'))
    return rows


class ExpandedTests(unittest.TestCase):
    def test_managed_identity_and_category(self):
        raw=managed_snapshot();rows=validate(raw,'managed-money')
        self.assertEqual(len(rows),13)
        self.assertEqual({r['category'] for r in rows},{'Managed Money'})
        self.assertEqual({r['net_contracts'] for r in rows},{20})
        self.assertTrue(all(r['tonnes_per_contract']>0 for r in rows))
        for key in ['prod_merc_positions_long','swap__positions_spread_all','other_rept_positions_short','nonrept_positions_short_all']:
            bad=copy.deepcopy(raw);bad[0][key]=str(int(bad[0][key])+1)
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad,'managed-money')
    def test_published_corn_row_reconciles_independently(self):
        # Official 2026-09-08 CFTC ag_lf.htm corn All row; other rows remain synthetic.
        # https://www.cftc.gov/dea/futures/ag_lf.htm (checked during edition-2 development)
        raw=managed_snapshot('2026-09-08')
        corn=next(r for r in raw if r['cftc_contract_market_code']=='002602')
        corn.update(open_interest_all='1803323',prod_merc_positions_long='291269',prod_merc_positions_short='1072185',
            swap_positions_long_all='337943',swap__positions_short_all='27632',swap__positions_spread_all='32341',
            m_money_positions_long_all='491034',m_money_positions_short_all='76575',m_money_positions_spread='235193',
            other_rept_positions_long='193378',other_rept_positions_short='64838',other_rept_positions_spread='95045',
            nonrept_positions_long_all='127120',nonrept_positions_short_all='199514')
        result=next(r for r in validate(raw,'managed-money') if r['market_code']=='002602')
        self.assertEqual(result['net_contracts'],414459)
        self.assertEqual(result['spreading_contracts'],235193)
        self.assertAlmostEqual(value(result,unit='mmt'),52.6387232217924)

    def test_wrong_or_mixed_source_cannot_substitute_category(self):
        with self.assertRaises((ValueError,KeyError)):validate(snapshot(),'managed-money')
        with self.assertRaises((ValueError,KeyError)):validate(managed_snapshot(),'legacy')
        raw=managed_snapshot();raw[0]['noncomm_positions_long_all']='100'
        with self.assertRaises(ValueError):validate(raw,'managed-money')
        rows=validate(snapshot())+validate(managed_snapshot(),'managed-money')
        with self.assertRaises(ValueError):enrich(rows)
    def test_physical_units_known_values_and_rejection(self):
        self.assertAlmostEqual(tonnes_per_contract('002602','(CONTRACTS OF 5,000 BUSHELS)'),127.0058636)
        self.assertAlmostEqual(tonnes_per_contract('005602','5000 BUSHELS'),136.077711)
        self.assertAlmostEqual(tonnes_per_contract('026603','100 SHORT TONS'),90.718474)
        self.assertEqual(tonnes_per_contract('073732','10 METRIC TONS'),10)
        self.assertIsNone(tonnes_per_contract('026603','100 METRIC TONS'))
        self.assertIsNone(tonnes_per_contract('002602','1000 BUSHELS'))
        r={'net_contracts':-10000,'tonnes_per_contract':127.0058636,'open_interest_contracts':20000}
        self.assertAlmostEqual(value(r,unit='mmt'),-1.270058636)
        self.assertEqual(value(r,unit='pct-oi'),-50)
    def test_calendar_horizons_not_row_offsets(self):
        start=date(2025,10,7)
        rows=[{**row((start+timedelta(weeks=i)).isoformat(),100+10*i,80,1000+100*i),
               'tonnes_per_contract':100} for i in range(14)]
        last=enrich(rows)[-1]
        self.assertEqual(last['net_change_4w_contracts'],40)
        self.assertEqual(last['net_change_13w_contracts'],130)
        self.assertEqual(last['net_change_13w_reference_date'],'2025-10-07')
        self.assertAlmostEqual(last['net_change_4w_mmt'],.004)
        self.assertAlmostEqual(last['net_change_4w_pct_oi_pp'],150/2300*100-110/1900*100)
        missing=enrich(rows[:10]+rows[11:])[-1]
        self.assertIsNone(missing['net_change_4w_contracts'])
        self.assertIsNone(missing['net_change_13w_contracts'])
        missing=enrich(rows[1:])[-1]
        self.assertIsNone(missing['net_change_13w_contracts'])
    def test_extrema_dates_ties_current_and_no_future_leakage(self):
        start=date(2020,1,7)
        rows=[row((start+timedelta(weeks=i)).isoformat(),100,80) for i in range(270)]
        rows[-1].update(long_contracts=120,net_contracts=40)
        r=enrich(rows)[-1]
        self.assertEqual(r['net_min_5y_contracts'],20)
        self.assertEqual(r['net_min_5y_date'],rows[-2]['report_date'])
        self.assertEqual(r['net_max_5y_contracts'],40)
        self.assertEqual(r['net_max_5y_date'],r['report_date'])
        self.assertEqual(enrich(rows[:-1]),enrich(rows)[:-1])
    def test_seasonal_excludes_current_year_from_band_and_requires_coverage(self):
        rows=[row(f'{y}-01-03',100+y-2020,80) for y in range(2020,2026)]
        rows += [row('2026-01-03',900,80),row('2026-10-03',9999,80),row('2027-01-03',9999,80)]
        s=seasonality(rows,'2026-01-06')['weeks'][0]
        self.assertEqual(s['reference_n'],5)
        self.assertEqual((s['min'],s['median'],s['max']),(21,23,25))
        self.assertEqual(s['current'],820)
        self.assertIsNone(seasonality(rows,'2026-01-06')['weeks'][40]['current'])
        s=seasonality(rows[-4:],'2026-01-06')['weeks'][0]
        self.assertIsNone(s['median'])
    def test_seasonal_leap_day_and_last_in_bin(self):
        self.assertEqual(seasonal_week(date(2024,2,29)),seasonal_week(date(2023,2,28)))
        rows=[row('2026-01-01',100,80),row('2026-01-06',110,80)]
        s=seasonality(rows,'2026-01-06')['weeks'][0]
        self.assertEqual(s['current'],30)
        self.assertEqual(s['current_date'],'2026-01-06')
    def test_new_cli_default_and_existing_legacy_binding(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.assertEqual(radar.resolve_config(root)['report'],'managed-money')
            state=radar.load_state(root);radar.atomic_json(root/'state.json',state)
            self.assertEqual(radar.resolve_config(root)['report'],'legacy')
            with self.assertRaises(ValueError):radar.resolve_config(root,report='managed-money')
            state['configuration']={'report':'managed-money','unit':'mmt','market':'002602'}
            radar.atomic_json(root/'state.json',state)
            self.assertEqual(radar.resolve_config(root),state['configuration'])
            with self.assertRaises(ValueError):radar.resolve_config(root,unit='contracts')
    def test_managed_prepare_retry_and_ack(self):
        raw=managed_snapshot();source_hash=radar.fingerprint(raw)
        def fake_build(raw,out,provenance,**config):
            self.assertEqual(config,{'report':'managed-money','unit':'mmt','market':'002602'})
            (out/radar.PANEL).write_bytes(b'png');(out/radar.PDF).write_bytes(b'pdf')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);config={'report':'managed-money','unit':'mmt','market':'002602'}
            with patch.object(radar,'check_source',return_value=('2026-01-06',source_hash)),patch.object(radar,'collect',return_value=(raw,{})),patch.object(radar,'build',side_effect=fake_build):
                first=radar.run(root,**config)
            with patch.object(radar,'check_source') as check:
                self.assertEqual(first,radar.run(root,**radar.resolve_config(root)));check.assert_not_called()
            before=(root/'state.json').read_bytes()
            with self.assertRaises(ValueError):radar.run(root,report='legacy')
            self.assertEqual(before,(root/'state.json').read_bytes())
            radar.acknowledge(root,first['edition_id'],'confirmed pair')
            with patch.object(radar,'check_source',return_value=('2026-01-06',source_hash)),patch.object(radar,'collect') as collect:
                self.assertIsNone(radar.run(root,**config));collect.assert_not_called()
    def test_collect_routes_to_correct_dataset_fields(self):
        with patch.object(radar,'fetch',return_value=([],'query','hash')) as fetch:
            radar.collect('managed-money')
        args=fetch.call_args.args
        self.assertEqual(args[1],'managed-money')
        self.assertIn('m_money_positions_long_all',args[0]['$select'])
        self.assertNotIn('noncomm_positions_long_all',args[0]['$select'])
    def test_mmt_rejects_changed_spec_before_artifact_writes(self):
        raw=managed_snapshot();raw[0]['contract_units']='1000 BUSHELS'
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)
            with self.assertRaises(ValueError):radar.build(raw,out,{},report='managed-money',unit='mmt')
            self.assertEqual(list(out.iterdir()),[])
    def test_invalid_secondary_pdf_blocks_build(self):
        def partial(rows,out,*args,**kwargs):
            for base in ['cftc-agricultural-positioning',*MARKETS]:
                (out/(base+'.png')).write_bytes(b'\x89PNG\r\n\x1a\n'+b'x'*1100)
                (out/(base+'.pdf')).write_bytes(b'%PDF-'+b'x'*1100+b'%%EOF')
            (out/'026603.pdf').write_bytes(b'')
            return [],[],[]
        with tempfile.TemporaryDirectory() as t,patch('reporting.render_v2',side_effect=partial):
            out=Path(t)
            with self.assertRaisesRegex(ValueError,'026603.pdf'):
                radar.build(managed_snapshot(),out,{},report='managed-money')
            self.assertFalse((out/'validation.json').exists())

    def test_managed_detail_png_pdf_and_evidence(self):
        raw=managed_snapshot('2025-12-30')+managed_snapshot()
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)
            receipt=radar.build(raw,out,{},offline=True,report='managed-money',unit='pct-oi',market='002602')
            self.assertEqual(receipt['dataset'],'72hh-3qpy')
            self.assertEqual(receipt['detail_market'],'002602')
            self.assertEqual((out/radar.PANEL).read_bytes(),(out/'002602.png').read_bytes())
            self.assertEqual((out/radar.PDF).read_bytes(),(out/'002602.pdf').read_bytes())
            self.assertTrue(receipt['checks']['physical_conversion_all_rows'])
            seasonal=json.loads((out/'seasonality.json').read_text())
            self.assertEqual(seasonal['002602']['unit'],'pct-oi')

if __name__=='__main__':unittest.main()
