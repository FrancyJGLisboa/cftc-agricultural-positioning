#!/usr/bin/env python3
"""Portable CFTC radar: prepare an edition, then acknowledge confirmed delivery.

JSON stdout is an internal adapter protocol, never user-facing prose.
A no-change run emits no stdout. Errors use stderr and exit 1.
"""
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

from analytics import VERSION, enrich
from cftc_positioning import FIELDS, MARKETS, PAGE, WHERE, REPORTS, fetch, fingerprint, newest, validate

EDITION_VERSION = '2.0.0'
PANEL = 'cftc-agricultural-positioning.png'
PDF = 'cftc-agricultural-positioning.pdf'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def lock(root):
    """Exclusive filesystem lock; never automatically steal a potentially live lock."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.run.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError('Another operation holds the state lock. If it crashed, confirm it stopped before removing .run.lock.') from exc
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(json.dumps({'pid': os.getpid(), 'created_at': now()}))
        yield
    finally:
        path.unlink()


def load_state(root):
    path = root / 'state.json'
    if not path.exists():
        if (root / 'editions').exists() and any((root / 'editions').iterdir()):
            raise RuntimeError('State is missing but editions exist; restore state instead of resetting publication history.')
        return {'schema_version': 1, 'run_log': [], 'pending': None, 'last_published': None}
    state = json.loads(path.read_text(encoding='utf-8'))
    if state.get('schema_version') != 1 or not isinstance(state.get('run_log'), list) or 'pending' not in state or 'last_published' not in state:
        raise ValueError('Unsupported or invalid state; restore the last valid state.')
    for entry in [state['pending'], state['last_published']]:
        if entry is not None and (not isinstance(entry, dict) or any(k not in entry for k in ['edition_id','report_date','source_fingerprint','edition_version','files'])):
            raise ValueError('Invalid edition record in state.')
    return state


def same(entry, report_date, source_hash):
    return bool(entry and entry['report_date'] == report_date and entry['source_fingerprint'] == source_hash and entry['edition_version'] == EDITION_VERSION)


def guard_date(state, report_date):
    previous = state.get('last_published')
    if previous and report_date < previous['report_date']:
        raise ValueError('Source reference date regressed; preserving the last published edition.')


def collect(report='legacy'):
    raw, query, raw_hash = fetch({'$select': ','.join(REPORTS[report]['fields']), '$where': WHERE + " AND report_date_as_yyyy_mm_dd >= '2016-08-01T00:00:00.000'", '$order': 'report_date_as_yyyy_mm_dd,cftc_contract_market_code', '$limit': 50000}, report)
    if len(raw) >= 50000:
        raise ValueError('Query may be truncated; pagination is required before publication.')
    return raw, {'source_query': query, 'download_sha256': raw_hash, 'fetched_at_utc': now()}


def check_source(report='legacy'):
    date = newest(report)
    raw, query, raw_hash = fetch({'$select': ','.join(REPORTS[report]['fields']), '$where': WHERE + " AND report_date_as_yyyy_mm_dd='" + date + "'", '$limit': 100}, report)
    rows = validate(raw, report)
    if len(rows) != 13 or {r['report_date'] for r in rows} != {date[:10]}:
        raise ValueError('Latest snapshot does not match the requested complete date.')
    return date[:10], fingerprint(raw)


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(raw, out, provenance, offline=False, report='legacy', unit='contracts', market=None):
    """Validation precedes every artifact write. Out must be an empty staging directory."""
    if report not in REPORTS or unit not in ('contracts','mmt','pct-oi') or (market and market not in MARKETS):
        raise ValueError('Invalid report, unit or market')
    rows = enrich(validate(raw, report))
    if unit=='mmt' and any(r['tonnes_per_contract'] is None for r in rows):
        raise ValueError('MMT requires recognized official contract units for every source row; use contracts or verify updated specifications.')
    latest = max(r['report_date'] for r in rows)
    if not all(r['decomposition_verified'] for r in rows if r['previous_report_date']):
        raise ValueError('Decomposition failed.')
    if not all(0 <= r['net_percentile_5y'] <= 100 for r in rows if r['net_percentile_5y'] is not None):
        raise ValueError('Percentile out of range.')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory must be empty to avoid mixed editions.')
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / 'cftc-source.json', raw)
    write_csv(out / 'history.csv', rows)
    from reporting import render_v2
    generated = now()
    last, diagnostic_rows, highlights = render_v2(rows, out, latest, provenance.get('fetched_at_utc') or generated, MARKETS, offline=offline, report=report, unit=unit, market=market)
    for basename in ['cftc-agricultural-positioning', *MARKETS]:
        for extension,signature in [('png', b'\x89PNG\r\n\x1a\n'),('pdf',b'%PDF-')]:
            filename=basename+'.'+extension
            data=(out/filename).read_bytes()
            if len(data)<1000 or not data.startswith(signature) or (extension=='pdf' and not data.rstrip().endswith(b'%%EOF')):
                raise ValueError('Renderer did not produce a complete '+filename)
    write_csv(out / 'latest-report.csv', last)
    atomic_json(out / 'diagnostics.json', diagnostic_rows)
    atomic_json(out / 'highlights.json', highlights)
    receipt = {
        'dataset': REPORTS[report]['dataset'], 'source_page': REPORTS[report]['page'], 'category': REPORTS[report]['category'],
        'report_type': 'FutOnly', 'units': 'contracts', 'display_unit': unit, 'detail_market': market, 'methodology_version': VERSION,
        'edition_version': EDITION_VERSION, 'latest_report_date': latest,
        'latest_source_fingerprint': fingerprint([r for r in raw if r['report_date_as_yyyy_mm_dd'][:10] == latest]),
        'generated_at_utc': generated, 'offline': offline, **provenance,
        'rows': len(rows), 'market_count': len(MARKETS),
        'observations_per_market': {c: sum(r['market_code'] == c for r in rows) for c in MARKETS},
        'checks': {'unique_date_market': True, 'nonnegative_integer_counts': True,
                   'futures_only': True, 'both_open_interest_identities_all_rows': True,
                   'latest_universe_complete': True, 'decomposition': True, 'percentile_range': True,
                   'panel_and_pdf_generated': True, 'all_detail_pairs_complete': True, 'calendar_horizons': True,
                   'physical_conversion_all_rows': all(r['tonnes_per_contract'] is not None for r in rows)},
        'freshness': 'Position date is not publication date. API maximum is not proof of the latest scheduled release.',
        'files': {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()},
    }
    atomic_json(out / 'validation.json', receipt)
    return receipt


def verify_edition(root, entry):
    folder = root / 'editions' / entry['edition_id']
    if folder.parent.resolve() != (root / 'editions').resolve():
        raise ValueError('Invalid edition location.')
    for name, expected in entry['files'].items():
        if Path(name).name != name or digest(folder / name) != expected:
            raise ValueError('Edition evidence is missing or modified; refusing delivery acknowledgement.')
    return folder


def presentation(folder):
    """Ordered host instructions; file generation alone is not display or delivery."""
    return {'layout': 'image_then_pdf_link', 'automatic_display': True,
            'items': [
                {'kind': 'image', 'path': str(folder / PANEL), 'mime_type': 'image/png',
                 'alt': 'CFTC Agricultural Positioning'},
                {'kind': 'download', 'path': str(folder / PDF), 'mime_type': 'application/pdf',
                 'label': 'Download PDF'}]}


def ready(root, entry):
    if PANEL not in entry['files'] or PDF not in entry['files']:
        raise ValueError('Edition is missing the required PNG/PDF pair.')
    folder = verify_edition(root, entry)
    return {'status': 'READY', 'edition_id': entry['edition_id'], 'report_date': entry['report_date'],
            'panel_path': str(folder / PANEL), 'panel_sha256': entry['files'][PANEL],
            'pdf_path': str(folder / PDF), 'pdf_sha256': entry['files'][PDF],
            'presentation': presentation(folder),
            'evidence_directory': str(folder), 'delivery_idempotency_key': entry['edition_id']}


def prepare(root, state, raw, provenance, date, source_hash, supersedes=None):
    staging = Path(tempfile.mkdtemp(prefix='.building-', dir=root))
    try:
        config = state.get('configuration', DEFAULT_CONFIG)
        if config == DEFAULT_CONFIG:
            build(raw, staging, provenance)
        else:
            build(raw, staging, provenance, **config)
        # A partial render must never replace the pending edition.
        if not all((staging / name).is_file() for name in (PANEL, PDF)):
            raise ValueError('Renderer must produce both PNG and PDF.')
        edition_id = date + '-' + source_hash[:16] + '-' + uuid.uuid4().hex[:8]
        editions = root / 'editions'
        editions.mkdir(exist_ok=True)
        staging.rename(editions / edition_id)
        folder = editions / edition_id
        entry = {'edition_id': edition_id, 'report_date': date, 'source_fingerprint': source_hash,
                 'edition_version': EDITION_VERSION,
                 'files': {p.name: digest(p) for p in folder.iterdir() if p.is_file()}}
        state['pending'] = entry
        event = {'event': 'prepared', 'at_utc': now(), 'edition_id': edition_id}
        if supersedes:
            event['supersedes_pending_edition'] = supersedes
        state['run_log'].append(event)
        atomic_json(root / 'state.json', state)
        return ready(root, entry)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def upgrade_pending(root, state):
    """Rebuild a legacy pending edition from its verified evidence, without fetching."""
    entry = state['pending']
    if entry['edition_version'] not in ('1.0.0', '1.1.0'):
        raise ValueError('Unsupported pending edition version; use the matching skill version or an explicit migration.')
    folder = verify_edition(root, entry)
    if not {'cftc-source.json', 'validation.json'}.issubset(entry['files']):
        raise ValueError('Legacy pending edition lacks verified source evidence; restore it before upgrading.')
    raw = json.loads((folder / 'cftc-source.json').read_text(encoding='utf-8'))
    receipt = json.loads((folder / 'validation.json').read_text(encoding='utf-8'))
    rows = validate(raw)
    date = max(r['report_date'] for r in rows)
    source_hash = fingerprint([r for r in raw if r['report_date_as_yyyy_mm_dd'][:10] == date])
    if date != entry['report_date'] or source_hash != entry['source_fingerprint']:
        raise ValueError('Legacy pending source does not match its edition record.')
    provenance = {k: receipt[k] for k in ('source_query', 'download_sha256', 'fetched_at_utc') if k in receipt}
    return prepare(root, state, raw, provenance, date, source_hash, supersedes=entry['edition_id'])


DEFAULT_CONFIG = {'report': 'legacy', 'unit': 'contracts', 'market': None}


def resolve_config(root, report=None, unit=None, market=None):
    # Existing 1.x destinations retain Legacy; a fresh CLI destination starts in Managed Money.
    state=load_state(root)
    existing=(root/'state.json').exists()
    base=state.get('configuration', DEFAULT_CONFIG if existing else {**DEFAULT_CONFIG,'report':'managed-money'})
    result={'report': report or base['report'], 'unit': unit or base['unit'],
            'market': market if market is not None else base['market']}
    if existing and result != base:
        raise ValueError('This state directory is bound to a different report/unit/market. Use a separate persistent state directory for the requested view.')
    return result


def run(root, report='legacy', unit='contracts', market=None):
    with lock(root):
        state = load_state(root)
        config = resolve_config(root, report, unit, market)
        state['configuration'] = config
        if state['pending']:
            if state['pending']['edition_version'] != EDITION_VERSION:
                return upgrade_pending(root, state)
            return ready(root, state['pending'])
        date, source_hash = check_source() if report=='legacy' else check_source(report)
        guard_date(state, date)
        if same(state['last_published'], date, source_hash):
            return None
        raw, provenance = collect() if report=='legacy' else collect(report)
        # The full validated collection is authoritative, even if the lightweight query differed.
        rows = validate(raw, report)
        date = max(r['report_date'] for r in rows)
        source_hash = fingerprint([r for r in raw if r['report_date_as_yyyy_mm_dd'][:10] == date])
        guard_date(state, date)
        if same(state['last_published'], date, source_hash):
            return None
        # Persist the initial empty state before materializing any edition; never infer delivery from files.
        if not (root / 'state.json').exists():
            atomic_json(root / 'state.json', state)
        return prepare(root, state, raw, provenance, date, source_hash)


def acknowledge(root, edition_id, delivery_receipt):
    with lock(root):
        state = load_state(root)
        entry = state['pending']
        if not entry:
            if state['last_published'] and state['last_published']['edition_id'] == edition_id:
                return {'status': 'ALREADY_ACKNOWLEDGED'}
            raise ValueError('No matching pending edition.')
        if entry['edition_id'] != edition_id:
            raise ValueError('Acknowledgement does not match the pending edition.')
        if entry['edition_version'] != EDITION_VERSION:
            raise ValueError('Run the skill to upgrade the pending edition before acknowledging the PNG/PDF pair.')
        ready(root, entry)
        state['last_published'] = entry
        state['pending'] = None
        state['last_success_at_utc'] = now()
        state['run_log'].append({'event': 'delivered', 'at_utc': now(), 'edition_id': edition_id,
                                 'delivery_receipt': delivery_receipt})
        atomic_json(root / 'state.json', state)
        return {'status': 'ACKNOWLEDGED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('run', help='Prepare a new edition; no stdout if unchanged.')
    p.add_argument('--state-dir', required=True, type=Path)
    p.add_argument('--report', choices=REPORTS)
    p.add_argument('--unit', choices=['contracts','mmt','pct-oi'])
    p.add_argument('--market', choices=MARKETS)
    p = commands.add_parser('ack', help='Record confirmed delivery after rendering and durable handoff.')
    p.add_argument('--state-dir', required=True, type=Path)
    p.add_argument('--edition-id', required=True)
    p.add_argument('--delivery-receipt', required=True)
    p = commands.add_parser('render', help='Reproduce saved official JSON offline; never advances publication state.')
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--report', choices=REPORTS, default='managed-money')
    p.add_argument('--unit', choices=['contracts','mmt','pct-oi'], default='contracts')
    p.add_argument('--market', choices=MARKETS)
    args = parser.parse_args()
    try:
        if args.command == 'run':
            root=args.state_dir.expanduser().resolve()
            config=resolve_config(root,args.report,args.unit,args.market)
            result = run(root,**config)
        elif args.command == 'ack':
            result = acknowledge(args.state_dir.expanduser().resolve(), args.edition_id, args.delivery_receipt)
        else:
            raw = json.loads(args.input.read_text(encoding='utf-8'))
            receipt = build(raw, args.output.resolve(), {'fetched_at_utc': None, 'source_query': None,
                           'input_sha256': digest(args.input)}, offline=True, report=args.report, unit=args.unit, market=args.market)
            result = {'status': 'OFFLINE', 'panel_path': str(args.output.resolve() / PANEL),
                      'pdf_path': str(args.output.resolve() / PDF),
                      'presentation': presentation(args.output.resolve()),
                      'report_date': receipt['latest_report_date']}
        if result is not None:
            print(json.dumps(result))
        return 0
    except Exception as exc:
        signature = hashlib.sha256((type(exc).__name__ + ':' + str(exc)).encode()).hexdigest()
        print(json.dumps({'status': 'ERROR', 'error_type': type(exc).__name__, 'message': str(exc),
                          'failure_signature': signature}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
