"""Draw static README charts from the checked-in SQL results."""
from pathlib import Path
from collections import defaultdict
from xml.sax.saxutils import escape
import csv

ROOT=Path(__file__).resolve().parents[1]
DARK,INK,MUTED,TEAL,RUST,LINE="#173b34","#182e28","#50665a","#36745c","#ac5039","#e2e5d9"

def text(x,y,s,size=18,color=INK,weight="400",anchor="start",serif=False):
    font="Georgia, serif" if serif else "Arial, sans-serif"
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(str(s))}</text>'

def rect(x,y,w,h,c,r=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" rx="{r}"/>'

def generate(slug,title,period,metrics,chart_title,items):
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 582" role="img">',
         f'<title>{escape(title)}</title><desc>{escape(period)}. Key figures: {escape(", ".join(n+" "+v for n,v in metrics))}.</desc>',
         rect(0,0,1000,582,"#f6f5ee"),rect(30,22,940,4,DARK),
         text(32,82,title,43,DARK,"bold",serif=True),text(32,115,period,19,MUTED)]
    for i,(label,val) in enumerate(metrics):
        x=32+i*316
        out.extend([rect(x,145,303,96,DARK,7),text(x+16,173,label,16,"#d4e1d5"),text(x+16,216,val,34,"#fffff6","bold",serif=True)])
    out.extend([text(32,285,chart_title,25,DARK,"bold",serif=True)])
    largest=max(1,max(abs(value) for _,value,_,_ in items))
    for i,(label,value,display,warn) in enumerate(items):
        y=317+35*i
        out.extend([text(32,y+12,label,17),rect(282,y,495,11,LINE,4),rect(282,y,round(495*abs(value)/largest,2),11,RUST if warn else TEAL,4),text(962,y+12,display,17,RUST if warn else DARK,"bold","end")])
    out.extend([rect(32,539,932,1,"#b6c2b9"),text(32,564,"NASRATULLAH SHINWARI",13,MUTED,"bold"),text(964,564,"Illustrative portfolio data",13,MUTED,anchor="end"),"</svg>"])
    (ROOT/slug/"preview.svg").write_text("\n".join(out),encoding="utf-8")

def read(slug,view):
    with (ROOT/slug/'results'/f'{view}.csv').open() as f: return list(csv.DictReader(f))

def main():
    slug="project-delivery"; rows=read(slug,"portfolio")
    budget=sum(int(r["budget_usd"]) for r in rows)
    spend=sum(int(r["spend_usd"]) for r in rows)
    overdue=sum(int(r["overdue"]) for r in rows)
    bars=[]
    for r in rows:
        consumed=int(r["spend_usd"])/int(r["budget_usd"])
        bars.append((r["project"],consumed,f"{consumed:.1%}",consumed>1))
    generate(slug,"Project delivery review","Reporting cutoff  ·  September 30, 2026",
             [("Approved budget",f"${budget:,.0f}"),("Recorded spend",f"${spend:,.0f}"),("Overdue milestones",str(overdue))],
             "Budget consumed by project",bars)
    slug="marketplace-profit"; rows=read(slug,"sku_ranking")
    net=sum(int(r['net_sales']) for r in rows)/100
    profit=sum(int(r['contribution']) for r in rows)/100
    def money(v): return ("−" if v<0 else "")+f"${abs(v):,.2f}"
    bars=[(r["product"],int(r["contribution"])/100,money(int(r['contribution'])/100),int(r['contribution'])<0) for r in rows]
    generate(slug,"Marketplace contribution","Order cohort  ·  July to September 2026",
             [("Net sales",money(net)),("Contribution",money(profit)),("Contribution margin",f"{profit/net:.1%}")],
             "Contribution by product · bars show magnitude",bars)
if __name__=="__main__": main()
