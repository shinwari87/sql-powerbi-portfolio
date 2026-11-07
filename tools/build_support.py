"""Build the service desk dashboard, preview, and portable Power BI project."""
import csv
import json
from html import escape
from math import ceil
from pathlib import Path

from build_powerbi import pbir, visual, write

BASE = Path(__file__).resolve().parents[1]
CASE = BASE / "support-sla"
OUT = CASE / "power-bi"
TABLE = "Tickets"
MEASURES = {
    "Ticket count": ("COALESCE(COUNTROWS(Tickets), 0)", "#,0"),
    "Met targets": ('COALESCE(CALCULATE(COUNTROWS(Tickets), KEEPFILTERS(Tickets[outcome] = "Met")), 0)', "#,0"),
    "Missed targets": ('COALESCE(CALCULATE(COUNTROWS(Tickets), KEEPFILTERS(Tickets[outcome] = "Missed")), 0)', "#,0"),
    "Evaluated tickets": ("[Met targets] + [Missed targets]", "#,0"),
    "Target met rate": ("DIVIDE([Met targets], [Evaluated tickets])", "0.0%"),
    "Overdue unanswered": ('COALESCE(CALCULATE(COUNTROWS(Tickets), KEEPFILTERS(Tickets[outcome] = "Missed"), KEEPFILTERS(ISBLANK(Tickets[wait_minutes]))), 0)', "#,0"),
    "P90 reply minutes": ("""VAR Answered = FILTER(Tickets, NOT ISBLANK(Tickets[wait_minutes]))
VAR K = ROUNDUP(0.9 * COUNTROWS(Answered), 0)
RETURN IF(K > 0, MAXX(TOPN(K, Answered, Tickets[wait_minutes], ASC, Tickets[ticket_id], ASC), Tickets[wait_minutes]))""", "#,0")
}
NUMERIC = {"target_minutes", "wait_minutes", "age_minutes"}

def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))

def embed_model(rows):
    # Store one M expression line per record for readable diffs.
    fields = list(rows[0])
    header = ", ".join(k+" = "+("nullable number" if k in NUMERIC else "nullable text") for k in fields)
    expression = ["#table(type table [" + header + "], {"]
    for i,row in enumerate(rows):
        values = ["null" if not row[k] else str(int(row[k])) if k in NUMERIC else '"'+row[k].replace('"','""')+'"' for k in fields]
        expression.append("    {" + ", ".join(values) + "}" + ("," if i+1<len(rows) else ""))
    expression.append("})")
    return {
        "name": TABLE,
        "columns": [{"name":k,"dataType":"int64" if k in NUMERIC else "string","sourceColumn":k} for k in fields],
        "partitions": [{"name":"Snapshot","mode":"import","source":{"type":"m","expression":expression}}],
        "measures": [{"name":k,"expression":v,"formatString":fmt} for k,(v,fmt) in MEASURES.items()]
    }

def power_bi(rows):
    report = OUT / "Response.Report"
    model = OUT / "Response.SemanticModel"
    write(OUT/"Response.pbip",{"version":"1.0","artifacts":[{"report":{"path":report.name}}],"settings":{"enableAutoRecovery":True}})
    write(report/"definition.pbir",{"version":"4.0","datasetReference":{"byPath":{"path":"../"+model.name}}})
    write(model/"definition.pbism",{"version":"1.0","settings":{}})
    write(model/"model.bim",{"name":"Response","compatibilityLevel":1550,"model":{"culture":"en-US","defaultPowerBIDataSourceVersion":"powerBI_V3","tables":[embed_model(rows)]}})
    definition = report / "definition"
    pbir(definition/"version.json","versionMetadata",version="2.0.0")
    pbir(definition/"report.json","report",layoutOptimization="None",themeCollection={})
    names = ["c83d559bd486e98d4501","e03c9814e29b456066ba"]
    pbir(definition/"pages/pages.json","pagesMetadata",pageOrder=names,activePageName=names[0])
    summary,detail=[definition / "pages" / name for name in names]
    for page,title in [(summary,"Response performance"),(detail,"Ticket detail")]:
        pbir(page/"page.json","page",name=page.name,displayName=title,displayOption="FitToPage",width=1280,height=720)
    def add(page,name,typ,rect,roles,order):
        visual(page,name,typ,rect,roles,order,table=TABLE,measures=MEASURES)
    for i,measure in enumerate(["Target met rate","Missed targets","P90 reply minutes","Overdue unanswered"]):
        add(summary,"kpi"+str(i),"card",(12+i*315,14,306,116),{"Values":[measure]},i)
    add(summary,"priority","slicer",(12,150,221,240),{"Values":["priority"]},4)
    add(summary,"byqueue","clusteredBarChart",(250,150,1010,240),{"Category":["queue"],"Y":["Target met rate"]},5)
    add(summary,"scorecard","tableEx",(12,410,1248,280),{"Values":["queue","Ticket count","Evaluated tickets","Met targets","Missed targets","Target met rate","P90 reply minutes"]},6)
    add(detail,"queue","slicer",(12,12,386,120),{"Values":["queue"]},0)
    add(detail,"status","slicer",(414,12,386,120),{"Values":["outcome"]},1)
    add(detail,"priority","slicer",(816,12,444,120),{"Values":["priority"]},2)
    add(detail,"tickets","tableEx",(12,153,1252,530),{"Values":["ticket_id","queue","priority","opened_utc","due_utc","first_reply_utc","outcome"]},3)

def preview(rows,scores,cutoff):
    def label(x,y,s,size,fill="#202e42",weight="400"):
        return f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}">{escape(str(s))}</text>'
    def rect(x,y,w,h,color,r=0):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}"/>'
    met=sum(r['outcome']=='Met' for r in rows)
    misses=sum(r['outcome']=='Missed' for r in rows)
    waits=sorted(int(r['wait_minutes']) for r in rows if r['wait_minutes'])
    p90=waits[ceil(0.9*len(waits))-1] if waits else '—'
    metrics=[("Targets met",f"{100*met/(met+misses):.1f}%" if met+misses else '—'),("Missed targets",str(misses)),("90th percentile reply",f"{p90} min" if waits else '—')]
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 505" role="img"><title>IT service desk first-response performance by queue</title>',rect(0,0,1000,505,'#f3f5fa'),rect(0,0,1000,105,'#17283e'),
         label(30,49,"First-response review",34,'#ffffff',"700"),label(31,79,cutoff+' UTC   /   Fictional service desk data',16,'#ced8e6')]
    for i,(k,v) in enumerate(metrics):
        x=30+i*317
        out.extend([rect(x,125,307,85,'#ffffff',5),label(x+14,151,k,16,'#495a6e'),label(x+14,191,v,31,'#17283e','700')])
    out.extend([label(30,253,'Share of evaluated tickets answered on time',22,weight='700'),label(30,278,'Pending targets are excluded. Bars run from 0 to 100%.',15,'#495a6e')])
    for i,r in enumerate(sorted(scores,key=lambda x:float(x['met_pct']) if x['met_pct'] else -1)):
        y=310+i*40
        rate=float(r['met_pct']) if r['met_pct'] else 0
        out.extend([label(32,y+9,r['queue'],17),rect(205,y-3,470,12,'#dce4ec',4),rect(205,y-3,4.70*rate,12,'#426686',4),
                    label(710,y+9,str(r['met_pct']+'%' if r['met_pct'] else '—'),17,weight='700'),label(818,y+9,r['missed']+' missed',16,'#495a6e')])
    out.extend([label(30,480,'Nasratullah Shinwari  /  SQL and Power BI',14,'#495a6e'),'</svg>'])
    (CASE/'preview.svg').write_text('\n'.join(out),encoding='utf-8')

def main():
    rows=read_rows(CASE/"results/ticket_outcomes.csv")
    scores=read_rows(CASE/"results/queue_scorecard.csv")
    cutoff=read_rows(CASE/"data/snapshot.csv")[0]["cutoff_utc"]
    payload=json.dumps({"cutoff":cutoff,"tickets":rows},separators=(',',':')).replace('<','\\u003c')
    template=(BASE/'tools/support_dashboard.html.in').read_text(encoding='utf-8')
    (CASE/'dashboard.html').write_text(template.replace('{{PAYLOAD}}',payload),encoding='utf-8')
    preview(rows,scores,cutoff)
    power_bi(rows)

if __name__=="__main__":
    main()
