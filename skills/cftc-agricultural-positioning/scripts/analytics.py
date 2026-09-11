"""Deterministic positioning diagnostics, version 2.0. No prediction model."""
from datetime import date,timedelta
from collections import defaultdict

VERSION='2.0'
MIN_REFERENCE=208
MAX_CONTIGUOUS_DAYS=10

def five_years_before(d):
    try:return d.replace(year=d.year-5)
    except ValueError:return d.replace(year=d.year-5,day=28)

def midrank(value,reference):
    if not reference:return None
    return 100*(sum(x<value for x in reference)+.5*sum(x==value for x in reference))/len(reference)

def driver(a,b,total):
    if total==0:return 'unchanged' if a==b==0 else 'offsetting contributions'
    if total>0:
        if a==b:return 'increasing longs and decreasing shorts'
        return 'increasing longs' if a>b else 'decreasing shorts'
    if a==b:return 'decreasing longs and increasing shorts'
    return 'decreasing longs' if a<b else 'increasing shorts'

def enrich(rows):
    groups=defaultdict(list)
    for r in rows:groups[r['market_code']].append(dict(r))
    result=[]
    for code,items in groups.items():
        items.sort(key=lambda r:r['report_date']);dates=[date.fromisoformat(r['report_date']) for r in items]
        if len(set(dates))!=len(dates):raise ValueError('Duplicate analytics key')
        streak=0;previous_sign=0;left_censored=True
        for i,r in enumerate(items):
            d=dates[i];cutoff=five_years_before(d)
            refs=[items[j]['net_contracts'] for j in range(i) if dates[j]>=cutoff]
            refdates=[dates[j] for j in range(i) if dates[j]>=cutoff]
            qualified=len(refs)>=MIN_REFERENCE and bool(refdates) and refdates[0]<=cutoff+timedelta(days=14)
            r.update(percentile_window_start=cutoff.isoformat(),percentile_window_end_exclusive=d.isoformat(),
              percentile_reference_n=len(refs),percentile_reference_first=refdates[0].isoformat() if refdates else None,
              percentile_reference_last=refdates[-1].isoformat() if refdates else None,
              net_percentile_5y=midrank(r['net_contracts'],refs) if qualified else None,
              percentile_status='valid' if qualified else 'insufficient_history',
              net_pct_open_interest=100*r['net_contracts']/r['open_interest_contracts'] if r['open_interest_contracts']>0 else None)
            delta_fields=dict(previous_report_date=None,report_interval_days=None,delta_long_contracts=None,delta_short_contracts=None,
              long_contribution_contracts=None,short_contribution_contracts=None,net_change_since_previous_report=None,
              net_change_pct_previous_oi=None,decomposition_driver='no comparison',decomposition_verified=None,
              persistence_direction='no comparison',persistence_reports=None,persistence_at_least=False)
            r.update(delta_fields)
            if i:
                prev=items[i-1];gap=(d-dates[i-1]).days
                a=r['long_contracts']-prev['long_contracts'];ds=r['short_contracts']-prev['short_contracts'];b=-ds
                total=r['net_contracts']-prev['net_contracts']
                if total!=a+b:raise ValueError('Decomposition does not reconcile')
                sign=1 if total>0 else -1 if total<0 else 0
                if gap>MAX_CONTIGUOUS_DAYS:
                    streak=0;previous_sign=0;left_censored=True;direction='irregular interval';count=None
                elif sign==0:
                    streak=0;previous_sign=0;left_censored=False;direction='unchanged';count=0
                else:
                    if sign==previous_sign:streak+=1
                    else:
                        streak=1
                        if i>1 and (dates[i-1]-dates[i-2]).days<=MAX_CONTIGUOUS_DAYS:left_censored=False
                    previous_sign=sign;direction='increase' if sign>0 else 'decrease';count=streak
                r.update(previous_report_date=prev['report_date'],report_interval_days=gap,delta_long_contracts=a,delta_short_contracts=ds,
                  long_contribution_contracts=a,short_contribution_contracts=b,net_change_since_previous_report=total,
                  net_change_pct_previous_oi=100*total/prev['open_interest_contracts'] if prev['open_interest_contracts']>0 else None,
                  decomposition_driver=driver(a,b,total),decomposition_verified=True,persistence_direction=direction,
                  persistence_reports=count,persistence_at_least=bool(count and left_censored))
            result.append(r)
    return sorted(result,key=lambda r:(r['market_code'],r['report_date']))

def fmt(x,decimals=0,signed=False):
    if x is None:return 'N/A'
    s=f'{x:+,.{decimals}f}' if signed else f'{x:,.{decimals}f}'
    return s

def persistence_text(r):
    n=r['persistence_reports'];direction=r['persistence_direction']
    if n is None:return direction
    if n==0:return 'unchanged; streak reset'
    return f"{'at least ' if r['persistence_at_least'] else ''}{n} {'report' if n==1 else 'reports'} of {direction}"

def diagnostic(r):
    p=r['net_percentile_5y'];n=r['net_contracts'];st=r['persistence_reports']
    flags=[]
    if p is not None and p>=95:flags.append('percentile_high')
    if p is not None and p<=5:flags.append('percentile_low')
    if st is not None and st>=4:flags.append('persistence_4_or_more')
    if 'percentile_high' in flags and n>0:
        question='Review long exposure and test a pause in additional buying; a historical extreme does not predict a reversal.'
    elif 'percentile_low' in flags and n<0:
        question='Examine a short-covering scenario; COT data do not establish the presence of a bullish catalyst.'
    elif flags:
        question='Review the thesis against relative positioning and the observed streak, without assuming future price direction.'
    else:question='Monitor the next release; none of the defined descriptive thresholds were reached.'
    pct=f"percentile {fmt(p,1)} against the preceding five years (n={r['percentile_reference_n']})" if p is not None else 'percentile unavailable: insufficient history'
    message=(f"{r['commodity']}: {pct}; net {fmt(n,signed=True)} contracts, {fmt(r['net_pct_open_interest'],1,signed=True)}% of open interest. "
       f"Since {r['previous_report_date'] or 'N/A'}: Δ net {fmt(r['net_change_since_previous_report'],signed=True)}, "
       f"long contribution {fmt(r['long_contribution_contracts'],signed=True)} and short contribution {fmt(r['short_contribution_contracts'],signed=True)} contracts. "
       f"Dominant component: {r['decomposition_driver']}. Persistence: {persistence_text(r)}.")
    return {'market_code':r['market_code'],'commodity':r['commodity'],'report_date':r['report_date'],'flags':flags,
      'eligible_for_highlight':bool(flags),'evidence':message,'research_question':question,
      'metrics':{k:r[k] for k in ['net_contracts','net_percentile_5y','net_pct_open_interest','net_change_since_previous_report',
       'long_contribution_contracts','short_contribution_contracts','net_change_pct_previous_oi','persistence_reports','persistence_direction','percentile_reference_n']}}

def diagnostics(latest):
    all_items=[diagnostic(r) for r in latest]
    ranked=sorted([x for x in all_items if x['eligible_for_highlight']],key=lambda x:(
      -int(any(s.startswith('percentile_') for s in x['flags'])),
      -abs((x['metrics']['net_percentile_5y'] if x['metrics']['net_percentile_5y'] is not None else 50)-50),
      -abs(x['metrics']['net_change_pct_previous_oi'] or 0),x['market_code']))
    return all_items,ranked
