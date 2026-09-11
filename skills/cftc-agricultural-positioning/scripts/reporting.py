"""Publication figures for the four CFTC-only diagnostics."""
from datetime import datetime
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from analytics import fmt,persistence_text,diagnostics

COLORS=['#367bb8','#cf3c49','#202a35']

def line(ax,items,field,color,label):
    x=[];y=[];prev=None
    for r in items:
        d=datetime.fromisoformat(r['report_date'])
        if prev and (d-prev).days>10:x.append(d);y.append(float('nan'))
        x.append(d);y.append(r[field] if r[field] is not None else float('nan'));prev=d
    ax.plot(x,y,color=color,label=label,lw=1.7 if field=='net_contracts' else 1.15)

def setup(ax,percent=False):
    ax.grid(axis='y',color='#e7edf2',lw=.7);ax.tick_params(length=0,labelsize=8)
    for s in ax.spines.values():s.set_visible(False)
    ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    if percent:ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x:.0f}%'))
    else:ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x/1000:.0f}k'))

def render_v2(rows,out,latest,fetched,markets,offline=False):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titleweight':'bold'})
    last=[next(r for r in reversed(rows) if r['market_code']==c) for c in markets]
    all_diag,ranked=diagnostics(last)
    for r in last:
        items=[x for x in rows if x['market_code']==r['market_code'] and x['report_date']>='2021-08-01']
        fig=plt.figure(figsize=(14,10.5));fig.patch.set_facecolor('white')
        fig.text(.065,.954,r['commodity']+' | POSITIONING',fontsize=22,fontweight='bold',color='#172e42')
        fig.text(.065,.922,f'Non-Commercial • futures only • contracts • positions as of {latest}',fontsize=11,color='#4d6679')
        labels=['PERCENTILE • 5 YEARS','NET / OPEN INTEREST','CHANGE IN NET','PERSISTENCE']
        values=[fmt(r['net_percentile_5y'],1),fmt(r['net_pct_open_interest'],1,signed=True)+'%',fmt(r['net_change_since_previous_report'],signed=True),
          ('≥' if r['persistence_at_least'] else '')+str(r['persistence_reports'])+' reports' if r['persistence_reports'] is not None else 'N/A']
        notes=[f"{r['percentile_reference_n']} prior observations",'position relative to market size','contracts since previous report',r['persistence_direction']]
        for x,label,val,note in zip([.065,.305,.55,.79],labels,values,notes):
            fig.text(x,.875,label,fontsize=8,color='#617487');fig.text(x,.84,val,fontsize=20,fontweight='bold',color='#172e42');fig.text(x,.817,note,fontsize=8,color='#617487')
        ax=fig.add_axes([.065,.475,.88,.29]);setup(ax)
        for f,c,l in zip(['long_contracts','short_signed_contracts','net_contracts'],COLORS,['Longs','Shorts (−)','Net']):line(ax,items,f,c,l)
        ax.axhline(0,c='#8fa1af',lw=.6);ax.legend(ncol=3,frameon=False,loc='upper left');ax.set_title('History in contracts',loc='left',fontsize=11)
        a=fig.add_axes([.065,.235,.255,.155]);setup(a,True);line(a,items,'net_percentile_5y','#547a93','Percentile')
        a.set_ylim(-3,103);a.axhline(95,c='#be7042',ls=':',lw=.8);a.axhline(5,c='#be7042',ls=':',lw=.8);a.set_title('Rolling five-year percentile',loc='left',fontsize=10)
        b=fig.add_axes([.377,.235,.255,.155]);setup(b,True);line(b,items,'net_pct_open_interest','#30596f','Net/OI');b.axhline(0,c='#8fa1af',lw=.6);b.set_title('Net / open interest',loc='left',fontsize=10)
        c=fig.add_axes([.69,.235,.255,.155]);setup(c)
        vals=[r['long_contribution_contracts'],r['short_contribution_contracts'],r['net_change_since_previous_report']]
        c.bar(range(3),[v or 0 for v in vals],color=[COLORS[0],COLORS[1],COLORS[2]],width=.57)
        c.axhline(0,c='#8fa1af',lw=.6);c.set_xticks(range(3),['Δ longs','−Δ shorts','Δ net'],fontsize=8);c.set_title('Contributions in contracts',loc='left',fontsize=10)
        for i,v in enumerate(vals):
            if v is not None:c.annotate(fmt(v,signed=True),(i,v),xytext=(0,4 if v>=0 else -10),textcoords='offset points',ha='center',fontsize=8)
        c.margins(y=.28)
        diag=next(d for d in all_diag if d['market_code']==r['market_code'])
        text=f"Dominant component: {r['decomposition_driver']}. {persistence_text(r).capitalize()}.\n"+diag['research_question']
        fig.text(.065,.155,'\n'.join(textwrap.fill(t,width=145) for t in text.split('\n')),fontsize=10,linespacing=1.6,color='#334c60')
        fig.text(.065,.043,'Source: CFTC 6dca-aqww. Percentile excludes the current observation; ties use midrank. Spreading is separate.\nMeasures are descriptive; they do not estimate returns or establish causes. Position date differs from publication date.',fontsize=8,color='#687c8a',linespacing=1.5)
        fig.savefig(out/(r['market_code']+'.png'),dpi=145);plt.close(fig)

    fig=plt.figure(figsize=(18,12));fig.patch.set_facecolor('white')
    fig.text(.045,.948,'CFTC | AGRICULTURAL POSITIONING',fontsize=25,fontweight='bold',color='#172e42')
    fig.text(.045,.915,f'Non-Commercial | futures only | contracts • positions as of {latest} • 13 markets',fontsize=12,color='#4d6679')
    comparison_dates = sorted({r['previous_report_date'] or 'N/A' for r in last})
    fig.text(.045,.888,'Changes versus: ' + ', '.join(comparison_dates) + ' | Position date differs from publication date.',fontsize=9,color='#4d6679')
    columns=['Commodity','Net\ncontracts','Percentile\n5 years','Net\n% OI','Δ net\ncontracts','Δ longs\ncontribution','−Δ shorts\ncontribution','Persistence\nreports']
    cells=[]
    for r in last:
        short_name=r['commodity']
        persist='N/A' if r['persistence_reports'] is None else ('unchanged (0)' if not r['persistence_reports'] else f"{'≥' if r['persistence_at_least'] else ''}{r['persistence_reports']} {r['persistence_direction']}")
        cells.append([short_name,fmt(r['net_contracts'],signed=True),fmt(r['net_percentile_5y'],1),fmt(r['net_pct_open_interest'],1,signed=True)+'%',
          fmt(r['net_change_since_previous_report'],signed=True),fmt(r['long_contribution_contracts'],signed=True),fmt(r['short_contribution_contracts'],signed=True),persist])
    ax=fig.add_axes([.045,.38,.91,.49]);ax.axis('off')
    table=ax.table(cellText=cells,colLabels=columns,cellLoc='right',colLoc='center',colWidths=[.19,.125,.09,.09,.12,.13,.13,.125],bbox=[0,0,1,1])
    table.auto_set_font_size(False);table.set_fontsize(10)
    for (i,j),cell in table.get_celld().items():
        cell.set_edgecolor('white');cell.PAD=.1
        if i==0:cell.set_facecolor('#18354c');cell.set_text_props(color='white',weight='bold',fontsize=10)
        else:
            cell.set_facecolor('#f0f5f8' if i%2 else '#ffffff');cell.set_text_props(color='#253e52')
            if j==0:cell.set_text_props(ha='left',weight='bold')
            p=last[i-1]['net_percentile_5y']
            if j==2 and p is not None and (p>=95 or p<=5):cell.set_facecolor('#fff0d9');cell.set_text_props(weight='bold',color='#875610')
    fig.text(.045,.337,'RESEARCH REVIEW HIGHLIGHTS',fontsize=12,fontweight='bold',color='#172e42')
    selected=ranked[:3]
    if not selected:fig.text(.045,.29,'No market reached the descriptive thresholds: percentile >=95 / <=5 or a streak of at least four reports.',fontsize=11,color='#4d6679')
    for y,d in zip([.294,.235,.176],selected):
        r=next(x for x in last if x['market_code']==d['market_code'])
        s=f"{r['commodity']}: P{fmt(r['net_percentile_5y'],1)} • {fmt(r['net_pct_open_interest'],1,signed=True)}% OI • {r['decomposition_driver']} • {persistence_text(r)}."
        fig.text(.045,y,s,fontsize=11,fontweight='bold',color='#253e52')
        fig.text(.045,y-.021,textwrap.shorten(d['research_question'],width=170,placeholder='…'),fontsize=9,color='#607486')
    fig.text(.045,.088,'Percentile: preceding five years, excluding the current observation; ties have weight 0.5. Change in net = change in longs - change in shorts.\nPersistence counts consecutive changes, not calendar weeks; zero resets the streak. Highlights are not trading signals.',fontsize=9,color='#607486',linespacing=1.6)
    stamp='OFFLINE REPRODUCTION' if offline else 'retrieved'
    fig.text(.045,.027,f'Sole source: CFTC • Dataset 6dca-aqww • {stamp} {fetched[:16]} UTC • methodology 2.0 | English edition 1.1',fontsize=8,color='#607486')
    # Both deliverables come from the same completed figure, before closing it.
    try:
        fig.savefig(out/'cftc-agricultural-positioning.png',dpi=145)
        fig.savefig(out/'cftc-agricultural-positioning.pdf',format='pdf',
                    metadata={'Title': 'CFTC Agricultural Positioning | ' + latest,
                              'Subject': 'The same decision panel as the PNG; ' + stamp,
                              'Author': 'CFTC Agricultural Positioning skill'})
    finally:
        plt.close(fig)
    return last,all_diag,ranked
