"""Deterministic positioning diagnostics, version 2.0. No prediction model."""
from datetime import date,timedelta
from collections import defaultdict
from statistics import median
from units import value

VERSION='3.0'
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
    categories={r.get('report','legacy') for r in rows}
    if len(categories)>1:raise ValueError('Analytics cannot mix report categories')
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
            r['delta_open_interest_contracts'] = r['open_interest_contracts']-items[i-1]['open_interest_contracts'] if i else None
            r['net_mmt'] = value(r, unit='mmt')
            # Extrema use the same five-year boundary, but include the current observation.
            history=[items[j] for j in range(i+1) if dates[j]>=cutoff]
            r['extrema_window_start']=cutoff.isoformat()
            r['extrema_window_end']=d.isoformat()
            for name, chooser in [('min', min), ('max', max)]:
                extreme=chooser(x['net_contracts'] for x in history) if qualified else None
                r['net_'+name+'_5y_contracts']=extreme
                r['net_'+name+'_5y_date']=next((x['report_date'] for x in reversed(history) if x['net_contracts']==extreme),None)
            for weeks in (4,13):
                target=d-timedelta(weeks=weeks)
                j=next((j for j in range(i) if dates[j]==target),None)
                valid=j is not None and all((dates[k]-dates[k-1]).days<=MAX_CONTIGUOUS_DAYS for k in range(j+1,i+1))
                prefix=f'net_change_{weeks}w'
                r[prefix+'_reference_date']=target.isoformat() if valid else None
                r[prefix+'_status']='valid' if valid else 'missing_reference_or_gap'
                r[prefix+'_contracts']=r['net_contracts']-items[j]['net_contracts'] if valid else None
                a=value(r,unit='pct-oi');b=value(items[j],unit='pct-oi') if valid else None
                r[prefix+'_pct_oi_pp']=a-b if a is not None and b is not None else None
                a=value(r,unit='mmt');b=value(items[j],unit='mmt') if valid else None
                same_spec=valid and r.get('tonnes_per_contract')==items[j].get('tonnes_per_contract')
                r[prefix+'_mmt']=a-b if a is not None and b is not None and same_spec else None
            r['net_change_previous_pct_oi_pp']=None
            if i:
                a=value(r,unit='pct-oi');b=value(items[i-1],unit='pct-oi')
                if a is not None and b is not None:r['net_change_previous_pct_oi_pp']=a-b
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


def seasonal_week(d):
    """Fixed Jan-1 seven-day bins on a non-leap calendar; Feb 29 maps to Feb 28."""
    aligned=date(2001,d.month,28 if d.month==2 and d.day==29 else d.day)
    return (aligned.timetuple().tm_yday-1)//7+1


def seasonality(items, latest, unit='contracts'):
    """Prior five calendar years; >=3 available years per bin; no interpolation."""
    asof=date.fromisoformat(latest);year=asof.year
    buckets={}
    for r in sorted(items,key=lambda r:r['report_date']):
        d=date.fromisoformat(r['report_date'])
        if year-5<=d.year<=year and d<=asof:
            buckets[(d.year,seasonal_week(d))]=(value(r,unit=unit),r['report_date'])
    weeks=[]
    for week in range(1,54):
        references=[buckets[(y,week)][0] for y in range(year-5,year)
                    if (y,week) in buckets and buckets[(y,week)][0] is not None]
        valid=len(references)>=3
        current=buckets.get((year,week),(None,None))
        previous=buckets.get((year-1,week),(None,None))
        weeks.append({'week':week,'reference_n':len(references),
            'median':median(references) if valid else None,'min':min(references) if valid else None,
            'max':max(references) if valid else None,'current':current[0],'current_date':current[1],
            'previous':previous[0],'previous_date':previous[1]})
    return {'unit':unit,'current_year':year,'previous_year':year-1,
            'reference_years':list(range(year-5,year)), 'minimum_reference_years':3,
            'alignment':'Jan-1 seven-day bins; Feb 29 maps to Feb 28; last observation per bin',
            'weeks':weeks}
