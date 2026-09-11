"""English summary and commodity detail, with matching PNG/PDF figures."""
from datetime import datetime
import json
import io
import os
import tempfile
import shutil
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from analytics import fmt, persistence_text, diagnostics, seasonality
from cftc_positioning import REPORTS
from units import LABELS, value

INK='#18354c'
MUTED='#607486'
BLUE='#367bb8'
RED='#cf3c49'


def number(v, unit='contracts', signed=True):
    return fmt(v, 0 if unit=='contracts' else 2, signed=signed)


def change(r, horizon, unit):
    if horizon=='previous':
        if r['report_interval_days'] is None or r['report_interval_days']>10:return None
        if unit=='pct-oi':return r['net_change_previous_pct_oi_pp']
        return value(r,'net_change_since_previous_report',unit)
    suffix={'contracts':'contracts','mmt':'mmt','pct-oi':'pct_oi_pp'}[unit]
    return r[f'net_change_{horizon}w_{suffix}']


def setup(ax, unit='contracts', calendar=False):
    ax.grid(axis='y',color='#e7edf2',lw=.7)
    ax.tick_params(length=0,labelsize=8)
    for spine in ax.spines.values():spine.set_visible(False)
    if calendar:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda x,p: f'{x/1000:g}k' if unit=='contracts' else f'{x:g}'+('%' if unit=='pct-oi' else '')))
    ax.axhline(0,color='#8fa1af',lw=.6)


def plot_history(ax, items, unit):
    setup(ax,unit,calendar=True)
    for field,color,label in [('long_contracts',BLUE,'Longs'),('short_signed_contracts',RED,'Shorts (−)'),('net_contracts',INK,'Net')]:
        x=[];y=[];prev=None
        for r in items:
            d=datetime.fromisoformat(r['report_date'])
            if prev and (d-prev).days>10:x.append(d);y.append(float('nan'))
            v=value(r,field,unit)
            x.append(d);y.append(v if v is not None else float('nan'));prev=d
        ax.plot(x,y,color=color,label=label,lw=1.3)
    ax.legend(frameon=False,ncol=3,fontsize=8,loc='upper left')


def plot_season(ax, series, title, small=False):
    unit=series['unit'];setup(ax,unit)
    data=series['weeks'];x=[r['week'] for r in data]
    def vals(field):return [float('nan') if r[field] is None else r[field] for r in data]
    years=series['reference_years']
    ax.fill_between(x,vals('min'),vals('max'),color='#dce7ed',label=f'{years[0]}–{years[-1]} range')
    ax.plot(x,vals('median'),color='#8a9ca6',ls='--',lw=1,label='Median')
    ax.plot(x,vals('previous'),color='#bb7c40',lw=1.2,label=str(series['previous_year']))
    ax.plot(x,vals('current'),color=BLUE,lw=2,label=str(series['current_year']))
    ax.set_xlim(1,53)
    ax.set_xticks([1,9,18,27,36,44,53],['Jan','Mar','May','Jul','Sep','Nov','Dec'])
    ax.set_ylabel('MMT' if unit=='mmt' else '% OI' if unit=='pct-oi' else 'Contracts',fontsize=8,color=MUTED)
    ax.set_title(title,loc='left',fontsize=10 if small else 12,fontweight='bold',color=INK)
    ax.legend(frameon=False,ncol=2 if small else 4,fontsize=6.5 if small else 8,loc='best')
    if not any(r['median'] is not None for r in data):
        ax.text(.5,.5,'Insufficient seasonal history',ha='center',transform=ax.transAxes,color=MUTED,fontsize=9)


def save_pair(fig, out, basename, latest, offline):
    # Materialize and validate in memory before replacing any artifact on disk.
    try:
        for extension in ('png','pdf'):
            buffer=io.BytesIO()
            options={'dpi':145} if extension=='png' else {'metadata':{
                'Title':'CFTC Agricultural Positioning | '+latest,
                'Subject':'Matching PNG/PDF panel; '+('OFFLINE REPRODUCTION' if offline else 'official source snapshot'),
                'Author':'CFTC Agricultural Positioning skill'}}
            fig.savefig(buffer,format=extension,**options)
            data=buffer.getvalue()
            if len(data)<1000 or (extension=='pdf' and not data.rstrip().endswith(b'%%EOF')):
                raise ValueError('Incomplete rendered '+extension)
            fd,temporary=tempfile.mkstemp(prefix='.render-',dir=out)
            try:
                with os.fdopen(fd,'wb') as f:
                    f.write(data);f.flush();os.fsync(f.fileno())
                os.replace(temporary,out/(basename+'.'+extension))
            finally:
                if os.path.exists(temporary):os.unlink(temporary)
    finally:plt.close(fig)


def footer(fig, report, fetched, offline, unit, synthetic=False):
    stamp='SYNTHETIC TEST DATA — OFFLINE' if synthetic else 'OFFLINE REPRODUCTION' if offline else 'Retrieved'
    fig.text(.04,.034,f"CFTC {REPORTS[report]['dataset']} | {stamp}: {fetched[:16]} UTC | Methodology 3.0 | Edition 2.0",fontsize=8,color=MUTED)
    note={'contracts':'Contract counts are not cash flows.',
          'mmt':'MMT = million metric tonnes of physical equivalent; not cash flow, inventory or delivery commitments.',
          'pct-oi':'Positions use contemporaneous OI; changes are percentage-point differences in net/OI.'}[unit]
    fig.text(.04,.015,note+' Spreading is separate. Position date differs from publication date.',fontsize=8,color=MUTED)


def detail(rows, r, out, latest, fetched, report, unit, offline, seasonal):
    fig=plt.figure(figsize=(16,11));fig.patch.set_facecolor('white')
    fig.text(.04,.953,r['commodity'].upper()+' | POSITIONING',fontsize=24,fontweight='bold',color=INK)
    fig.text(.04,.918,f"{REPORTS[report]['category']} | futures only | {LABELS[unit]} | positions as of {latest}",fontsize=11,color=MUTED)
    suffix='%' if unit=='pct-oi' else ' MMT' if unit=='mmt' else ''
    delta_suffix=' pp' if unit=='pct-oi' else ' MMT' if unit=='mmt' else ''
    tiles=[('NET POSITION',number(value(r,unit=unit),unit)+suffix),
           ('NET / OPEN INTEREST',fmt(r['net_pct_open_interest'],2,True)+'%'),
           ('4-WEEK NET CHANGE',number(change(r,4,unit),unit)+delta_suffix),
           ('13-WEEK NET CHANGE',number(change(r,13,unit),unit)+delta_suffix)]
    for x,(label,v) in zip([.04,.29,.54,.79],tiles):
        fig.text(x,.874,label,fontsize=9,color=MUTED)
        fig.text(x,.839,v,fontsize=23,fontweight='bold',color=INK)
    ax=fig.add_axes([.055,.475,.415,.295]);plot_season(ax,seasonal,'Seasonal net positioning')
    ax=fig.add_axes([.56,.475,.40,.295]);plot_history(ax,[x for x in rows if x['report_date']>=r['extrema_window_start']],unit)
    ax.set_title('Longs, shorts and net | trailing five years',loc='left',fontsize=12,color=INK)
    ax=fig.add_axes([.055,.205,.26,.175]);setup(ax,'contracts')
    vals=[r['long_contribution_contracts'],r['short_contribution_contracts'],r['net_change_since_previous_report']]
    for i,v in enumerate(vals):
        if v is not None:
            ax.bar(i,v,color=[BLUE,RED,INK][i],width=.55)
            ax.annotate(fmt(v,signed=True),(i,v),xytext=(0,5 if v>=0 else -12),textcoords='offset points',ha='center',fontsize=8)
        else:ax.text(i,0,'N/A',ha='center',fontsize=9)
    ax.set_xticks([0,1,2],['Δ longs','−Δ shorts','Δ net']);ax.margins(y=.3)
    ax.set_title('Decomposition | contracts',loc='left',fontsize=11,color=INK)
    fig.text(.37,.375,'HISTORICAL CONTEXT',fontsize=11,fontweight='bold',color=INK)
    lines=[f"Net percentile (prior 5 years): {fmt(r['net_percentile_5y'],1)} | n={r['percentile_reference_n']}",
        f"Minimum net: {fmt(r['net_min_5y_contracts'],signed=True)} contracts | {r['net_min_5y_date'] or 'N/A'}",
        f"Maximum net: {fmt(r['net_max_5y_contracts'],signed=True)} contracts | {r['net_max_5y_date'] or 'N/A'}",
        f"Extrema window: {r['extrema_window_start']} to {latest}, inclusive",
        f"Open interest: {fmt(r['open_interest_contracts'])} | Δ {fmt(r['delta_open_interest_contracts'],signed=True)} contracts",
        f"Comparison: {r['previous_report_date'] or 'N/A'} | {r['report_interval_days'] or 'N/A'} days",
        f"Persistence: {persistence_text(r)}"]
    fig.text(.37,.344,'\n'.join(lines),fontsize=10,color=MUTED,linespacing=1.75,va='top')
    fig.text(.04,.123,'Dominant component: '+r['decomposition_driver']+'. Measures are descriptive, not return forecasts.',fontsize=10,color=INK)
    fig.text(.04,.079,'Seasonality: prior five calendar years, minimum three years per bin; Jan-1 seven-day bins. No interpolation.\n4/13-week changes require the exact comparison date and no intervening gap over ten days. Missing comparisons remain N/A.',fontsize=8.5,color=MUTED,linespacing=1.5)
    footer(fig,report,fetched,offline,unit,synthetic=any('SYNTHETIC' in x['source_market_name'].upper() for x in rows))
    save_pair(fig,out,r['market_code'],latest,offline)


def render_v2(rows,out,latest,fetched,markets,offline=False,report='legacy',unit='contracts',market=None):
    """Retain the Python entrypoint name for existing adapters; edition is now 2.0."""
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titleweight':'bold'})
    last=[next(r for r in reversed(rows) if r['market_code']==c) for c in markets]
    all_diag,ranked=diagnostics(last)
    seasonal={}
    for r in last:
        items=[x for x in rows if x['market_code']==r['market_code']]
        seasonal[r['market_code']]=seasonality(items,latest,unit)
        detail(items,r,out,latest,fetched,report,unit,offline,seasonal[r['market_code']])
    (out/'seasonality.json').write_text(json.dumps(seasonal,indent=2,allow_nan=False),encoding='utf-8')
    if market:
        for extension in ['png','pdf']:shutil.copyfile(out/(market+'.'+extension),out/('cftc-agricultural-positioning.'+extension))
        return last,all_diag,ranked
    fig=plt.figure(figsize=(21,13));fig.patch.set_facecolor('white')
    fig.text(.04,.953,'CFTC | AGRICULTURAL POSITIONING',fontsize=25,fontweight='bold',color=INK)
    fig.text(.04,.919,f"{REPORTS[report]['category']} | futures only | positions as of {latest} | 13 markets",fontsize=12,color=MUTED)
    compared=', '.join(sorted({r['previous_report_date'] or 'N/A' for r in last}))
    fig.text(.04,.893,f'Net and changes: {LABELS[unit]} | Previous report: {compared} | OI and extrema: contracts',fontsize=10,color=MUTED)
    delta_label='pp' if unit=='pct-oi' else 'MMT' if unit=='mmt' else 'contracts'
    columns=['Commodity','Open interest\ncontracts','Δ OI\ncontracts','Net\n'+delta_label,'Δ previous\n'+delta_label,
             'Δ 4 weeks\n'+delta_label,'Δ 13 weeks\n'+delta_label,'Percentile\nprior 5y','Net\n% OI',
             'Min net / date\ntrailing 5y','Max net / date\ntrailing 5y','Persistence\nreports']
    # Percent positions are levels; only their changes are percentage points.
    if unit=='pct-oi':columns[3]='Net\n% OI'
    cells=[]
    for r in last:
        persist='N/A' if r['persistence_reports'] is None else ('0' if not r['persistence_reports'] else f"{'≥' if r['persistence_at_least'] else ''}{r['persistence_reports']} {r['persistence_direction']}")
        cells.append([r['commodity'],fmt(r['open_interest_contracts']),fmt(r['delta_open_interest_contracts'],signed=True),
          number(value(r,unit=unit),unit),number(change(r,'previous',unit),unit),number(change(r,4,unit),unit),number(change(r,13,unit),unit),
          fmt(r['net_percentile_5y'],1),fmt(r['net_pct_open_interest'],1,True)+'%',
          fmt(r['net_min_5y_contracts'],signed=True)+'\n'+(r['net_min_5y_date'] or 'N/A'),
          fmt(r['net_max_5y_contracts'],signed=True)+'\n'+(r['net_max_5y_date'] or 'N/A'),persist])
    ax=fig.add_axes([.04,.425,.92,.445]);ax.axis('off')
    table=ax.table(cellText=cells,colLabels=columns,cellLoc='right',colLoc='center',
                   colWidths=[.15,.085,.065,.075,.075,.075,.075,.055,.055,.105,.105,.08],bbox=[0,0,1,1])
    table.auto_set_font_size(False);table.set_fontsize(9)
    for (i,j),cell in table.get_celld().items():
        cell.set_edgecolor('white');cell.PAD=.07
        if i==0:cell.set_facecolor(INK);cell.set_text_props(color='white',weight='bold',fontsize=8.5)
        else:
            cell.set_facecolor('#eff4f7' if i%2 else 'white');cell.set_text_props(color=INK)
            if j==0:cell.set_text_props(ha='left',weight='bold')
            p=last[i-1]['net_percentile_5y']
            if j==7 and p is not None and (p>=95 or p<=5):cell.set_facecolor('#fff0d9');cell.set_text_props(color='#875610',weight='bold')
    fig.text(.04,.399,'SEASONAL CONTEXT & RESEARCH REVIEW',fontsize=12,fontweight='bold',color=INK)
    selected=[d['market_code'] for d in ranked[:3]]
    selected += [c for c in markets if c not in selected][:3-len(selected)]
    for x,code in zip([.055,.37,.685],selected):
        r=next(r for r in last if r['market_code']==code)
        ax=fig.add_axes([x,.157,.275,.19]);plot_season(ax,seasonal[code],r['commodity']+' | net',True)
        note=f"{r['decomposition_driver']}; {persistence_text(r)}."
        fig.text(x,.122,textwrap.fill(note,width=56),fontsize=8.5,color=INK)
    fig.text(.04,.067,'Percentile excludes current observation; extrema include it. 4/13 weeks use exact calendar comparisons. Seasonal bands: prior five calendar years, ≥3 years/bin.\nCharts prioritize percentile extremes and persistence; remaining slots follow market order. These are descriptive review prompts, not trading signals.',fontsize=9,color=MUTED,linespacing=1.5)
    footer(fig,report,fetched,offline,unit,synthetic=any('SYNTHETIC' in x['source_market_name'].upper() for x in rows))
    save_pair(fig,out,'cftc-agricultural-positioning',latest,offline)
    return last,all_diag,ranked
