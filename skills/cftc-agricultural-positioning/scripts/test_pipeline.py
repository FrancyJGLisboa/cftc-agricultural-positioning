"""Offline tests with explicitly synthetic source-shaped records; never market evidence."""
import copy
from decimal import InvalidOperation
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cftc_positioning import MARKETS, fingerprint, validate
import radar


def snapshot(date='2026-01-06'):
    return [dict(report_date_as_yyyy_mm_dd=date+'T00:00:00.000',cftc_contract_market_code=code,
                 market_and_exchange_names='SYNTHETIC TEST RECORD',noncomm_positions_long_all='100',
                 noncomm_positions_short_all='80',noncomm_postions_spread_all='20',open_interest_all='1000',
                 comm_positions_long_all='700',comm_positions_short_all='720',
                 nonrept_positions_long_all='180',nonrept_positions_short_all='180',
                 contract_units='TEST CONTRACTS',futonly_or_combined='FutOnly') for code in MARKETS]


class ValidationTests(unittest.TestCase):
    def test_valid(self):
        rows=validate(snapshot())
        self.assertEqual(len(rows),13)
        self.assertEqual(rows[0]['net_contracts'],20)
        self.assertEqual(rows[0]['short_signed_contracts'],-80)
    def test_bad_counts_and_coverage(self):
        raw=snapshot()
        cases=[raw[:-1],raw+[raw[0]]]
        for field,value in [('noncomm_positions_long_all','-1'),('noncomm_positions_short_all',None),
                            ('open_interest_all','1'),('futonly_or_combined','Combined'),
                            ('noncomm_positions_long_all','1.5'),('noncomm_positions_long_all','NaN'),
                            ('noncomm_positions_long_all','Infinity'),('report_date_as_yyyy_mm_dd','bad-date')]:
            bad=copy.deepcopy(raw);bad[0][field]=value;cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad[0]):
                with self.assertRaises((ValueError,TypeError,InvalidOperation)): validate(bad)
    def test_fingerprint(self):
        raw=snapshot()
        self.assertEqual(fingerprint(raw),fingerprint(raw[::-1]))
        revised=copy.deepcopy(raw);revised[0]['noncomm_positions_long_all']='101'
        self.assertNotEqual(fingerprint(raw),fingerprint(revised))
    def test_missing_field(self):
        raw=snapshot();del raw[0]['noncomm_positions_short_all']
        with self.assertRaises(KeyError):validate(raw)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.raw=snapshot();self.date='2026-01-06';self.hash=fingerprint(self.raw)
    def tearDown(self):self.tmp.cleanup()
    def fake_build(self,raw,out,provenance):
        (out/radar.PANEL).write_bytes(b'test image bytes')
        radar.atomic_json(out/'validation.json',{'synthetic_test':True})
        return {}
    def prepare(self):
        with patch.object(radar,'check_source',return_value=(self.date,self.hash)),patch.object(radar,'collect',return_value=(self.raw,{})),patch.object(radar,'build',side_effect=self.fake_build):
            return radar.run(self.root)
    def test_prepare_ack_and_unchanged_no_write(self):
        ready=self.prepare();state=radar.load_state(self.root)
        self.assertIsNone(state['last_published']);self.assertIsNotNone(state['pending'])
        radar.acknowledge(self.root,ready['edition_id'],'test-confirmed-delivery')
        before=(self.root/'state.json').read_bytes()
        with patch.object(radar,'check_source',return_value=(self.date,self.hash)),patch.object(radar,'collect') as collect:
            self.assertIsNone(radar.run(self.root));collect.assert_not_called()
        self.assertEqual(before,(self.root/'state.json').read_bytes())
        self.assertEqual(len(radar.load_state(self.root)['run_log']),2)
    def test_pending_retried_without_new_collection(self):
        first=self.prepare()
        with patch.object(radar,'check_source') as check:
            self.assertEqual(first,radar.run(self.root));check.assert_not_called()
    def test_tamper_blocks_ack(self):
        ready=self.prepare();Path(ready['panel_path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):radar.acknowledge(self.root,ready['edition_id'],'receipt')
        self.assertIsNone(radar.load_state(self.root)['last_published'])
    def test_ack_wrong_id_and_idempotent_ack(self):
        ready=self.prepare()
        with self.assertRaises(ValueError):radar.acknowledge(self.root,'wrong','receipt')
        radar.acknowledge(self.root,ready['edition_id'],'receipt')
        self.assertEqual(radar.acknowledge(self.root,ready['edition_id'],'receipt')['status'],'ALREADY_ACKNOWLEDGED')
    def test_regression_preserves_state(self):
        ready=self.prepare();radar.acknowledge(self.root,ready['edition_id'],'receipt')
        before=(self.root/'state.json').read_bytes()
        with patch.object(radar,'check_source',return_value=('2025-12-30',self.hash)):
            with self.assertRaises(ValueError):radar.run(self.root)
        self.assertEqual(before,(self.root/'state.json').read_bytes())
    def test_full_collection_is_authority(self):
        ready=self.prepare();radar.acknowledge(self.root,ready['edition_id'],'receipt')
        with patch.object(radar,'check_source',return_value=('2026-01-13','new')),patch.object(radar,'collect',return_value=(self.raw,{})),patch.object(radar,'build') as build:
            self.assertIsNone(radar.run(self.root));build.assert_not_called()
    def test_same_date_revision_triggers(self):
        ready=self.prepare();radar.acknowledge(self.root,ready['edition_id'],'receipt')
        self.raw[0]['noncomm_positions_long_all']='101';self.raw[0]['comm_positions_long_all']='699';self.hash=fingerprint(self.raw)
        self.assertNotEqual(self.prepare()['edition_id'],ready['edition_id'])
    def test_missing_or_corrupt_state_fails_closed(self):
        self.prepare();(self.root/'state.json').unlink()
        with self.assertRaises(RuntimeError):radar.load_state(self.root)
        (self.root/'state.json').write_text('not json')
        with self.assertRaises(ValueError):radar.load_state(self.root)
    def test_lock_excludes_concurrent_run(self):
        with radar.lock(self.root):
            with self.assertRaises(RuntimeError):
                with radar.lock(self.root):pass
    def test_build_failure_does_not_publish(self):
        with patch.object(radar,'check_source',return_value=(self.date,self.hash)),patch.object(radar,'collect',return_value=(self.raw,{})),patch.object(radar,'build',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):radar.run(self.root)
        self.assertIsNone(radar.load_state(self.root)['last_published'])
        self.assertIsNone(radar.load_state(self.root)['pending'])

if __name__=='__main__':unittest.main()
