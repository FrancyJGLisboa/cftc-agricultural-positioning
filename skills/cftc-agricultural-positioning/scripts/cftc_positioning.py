"""Official CFTC collector and strict contract validation."""
import csv, hashlib, json, urllib.request, urllib.parse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from units import tonnes_per_contract

API='https://publicreporting.cftc.gov/resource/6dca-aqww.json'
PAGE='https://publicreporting.cftc.gov/Commitments-of-Traders/Legacy-Futures-Only/6dca-aqww'
MARKETS={
 '002602':'Corn','005602':'Soybeans','001602':'Wheat SRW (Chicago)',
 '001612':'Wheat HRW (Kansas)','026603':'Soybean meal','007601':'Soybean oil',
 '057642':'Live cattle','054642':'Lean hogs','061641':'Feeder cattle',
 '033661':'Cotton No. 2','080732':'Sugar No. 11','083731':'Coffee C','073732':'Cocoa'}

FIELDS=['report_date_as_yyyy_mm_dd','cftc_contract_market_code','market_and_exchange_names',
 'noncomm_positions_long_all','noncomm_positions_short_all','noncomm_postions_spread_all',
 'open_interest_all','comm_positions_long_all','comm_positions_short_all',
 'nonrept_positions_long_all','nonrept_positions_short_all','contract_units','futonly_or_combined']
WHERE='cftc_contract_market_code in ('+','.join("'"+x+"'" for x in MARKETS)+')'

REPORTS = {
    'legacy': {'dataset': '6dca-aqww', 'category': 'Non-Commercial',
               'page': PAGE, 'fields': FIELDS},
    'managed-money': {'dataset': '72hh-3qpy', 'category': 'Managed Money',
        'page': 'https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy',
        'fields': FIELDS[:3] + [
            'm_money_positions_long_all', 'm_money_positions_short_all', 'm_money_positions_spread',
            'open_interest_all', 'prod_merc_positions_long', 'prod_merc_positions_short',
            'swap_positions_long_all', 'swap__positions_short_all', 'swap__positions_spread_all',
            'other_rept_positions_long', 'other_rept_positions_short', 'other_rept_positions_spread',
            'nonrept_positions_long_all', 'nonrept_positions_short_all',
            'contract_units', 'futonly_or_combined']},
}


def fetch(params, report='legacy'):
    url='https://publicreporting.cftc.gov/resource/'+REPORTS[report]['dataset']+'.json?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'User-Agent':'CFTC-public-positioning/2.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as r:raw=r.read()
    data=json.loads(raw)
    if not isinstance(data,list):raise ValueError('CFTC did not return an array')
    return data,url,hashlib.sha256(raw).hexdigest()


def newest(report='legacy'):
    rows,_,_=fetch({'$select':'max(report_date_as_yyyy_mm_dd) as latest','$where':WHERE}, report)
    return rows[0]['latest']


def fingerprint(rows):
    data=sorted(rows,key=lambda r:(r['report_date_as_yyyy_mm_dd'],r['cftc_contract_market_code']))
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate(rows, report='legacy'):
    config=REPORTS[report]
    seen=set();out=[]
    number_fields=config['fields'][3:-2]
    for r in rows:
        d=r['report_date_as_yyyy_mm_dd'][:10];datetime.strptime(d,'%Y-%m-%d');c=r['cftc_contract_market_code']
        if c not in MARKETS:raise ValueError('Unexpected market')
        if (d,c) in seen:raise ValueError('Duplicate date/market')
        seen.add((d,c))
        if r['futonly_or_combined']!='FutOnly':raise ValueError('Mixed report types')
        other_key='m_money_positions_long_all' if report=='legacy' else 'noncomm_positions_long_all'
        if other_key in r:raise ValueError('Mixed report categories')
        v={}
        for k in number_fields:
            n=Decimal(str(r[k]))
            if not n.is_finite() or n<0 or n!=n.to_integral_value():raise ValueError('Invalid contract count: '+k)
            v[k]=int(n)
        OI=v['open_interest_all']
        if report=='legacy':
            L=v['noncomm_positions_long_all'];S=v['noncomm_positions_short_all'];P=v['noncomm_postions_spread_all']
            long_total=L+P+v['comm_positions_long_all']+v['nonrept_positions_long_all']
            short_total=S+P+v['comm_positions_short_all']+v['nonrept_positions_short_all']
        else:
            L=v['m_money_positions_long_all'];S=v['m_money_positions_short_all'];P=v['m_money_positions_spread']
            spreads=P+v['swap__positions_spread_all']+v['other_rept_positions_spread']
            long_total=L+spreads+v['prod_merc_positions_long']+v['swap_positions_long_all']+v['other_rept_positions_long']+v['nonrept_positions_long_all']
            short_total=S+spreads+v['prod_merc_positions_short']+v['swap__positions_short_all']+v['other_rept_positions_short']+v['nonrept_positions_short_all']
        if long_total!=OI:raise ValueError('Long-side open interest identity failed')
        if short_total!=OI:raise ValueError('Short-side open interest identity failed')
        factor=tonnes_per_contract(c,r['contract_units'])
        out.append(dict(report_date=d,market_code=c,commodity=MARKETS[c],source_market_name=r['market_and_exchange_names'],
          report=report,category=config['category'],dataset=config['dataset'],
          long_contracts=L,short_contracts=S,short_signed_contracts=-S,net_contracts=L-S,
          spreading_contracts=P,open_interest_contracts=OI,contract_units=r['contract_units'],
          tonnes_per_contract=factor,physical_conversion_status='verified' if factor is not None else 'unrecognized_contract_units'))
    if not out:raise ValueError('No observations')
    latest=max(x['report_date'] for x in out)
    covered={x['market_code'] for x in out if x['report_date']==latest}
    if covered!=set(MARKETS):raise ValueError('Latest report incomplete: '+str(set(MARKETS)-covered))
    return sorted(out,key=lambda x:(x['market_code'],x['report_date']))
