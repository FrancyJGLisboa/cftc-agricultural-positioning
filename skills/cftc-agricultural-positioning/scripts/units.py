"""Physical contract equivalents. Never estimates cash flow or deliverable inventory."""
import re

LB_TO_TONNE = 0.00045359237
# quantity, CFTC unit, pounds per bushel (only for grain contracts)
SPECS = {
    '002602': (5000, 'BUSHELS', 56),
    '005602': (5000, 'BUSHELS', 60),
    '001602': (5000, 'BUSHELS', 60),
    '001612': (5000, 'BUSHELS', 60),
    '026603': (100, 'TONS', None),
    '007601': (60000, 'POUNDS', None),
    '057642': (40000, 'POUNDS', None),
    '054642': (40000, 'POUNDS', None),
    '061641': (50000, 'POUNDS', None),
    '033661': (50000, 'POUNDS', None),
    '080732': (112000, 'POUNDS', None),
    '083731': (37500, 'POUNDS', None),
    '073732': (10, 'METRIC TONS', None),
}
LABELS = {'contracts': 'contracts', 'mmt': 'million metric tonnes (physical equivalent)',
          'pct-oi': '% of open interest'}


def tonnes_per_contract(code, source_units):
    """Return None for unknown/changed source specs; never silently use a stale factor."""
    quantity, unit, pounds = SPECS[code]
    normalized = ' '.join(str(source_units).upper().replace(',', '').split())
    normalized = normalized.strip('() ')
    normalized = re.sub(r'^CONTRACTS (?:OF|IN) ', '', normalized)
    aliases = {'100 SHORT TONS': '100 TONS', '10 METRIC TONNES': '10 METRIC TONS'}
    normalized = aliases.get(normalized, normalized)
    if normalized != f'{quantity} {unit}':
        return None
    if unit == 'BUSHELS':
        return quantity * pounds * LB_TO_TONNE
    if unit == 'POUNDS':
        return quantity * LB_TO_TONNE
    if unit == 'TONS':
        return quantity * 2000 * LB_TO_TONNE
    return float(quantity)


def value(row, field='net_contracts', unit='contracts'):
    if unit not in LABELS:
        raise ValueError('Unknown display unit')
    number = row.get(field)
    if number is None:
        return None
    if unit == 'contracts':
        return number
    if unit == 'mmt':
        factor = row.get('tonnes_per_contract')
        return None if factor is None else number * factor / 1_000_000
    oi = row['open_interest_contracts']
    return 100 * number / oi if oi else None
