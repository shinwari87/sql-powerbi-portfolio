"""Generate a portable Power BI Project from the exported portfolio snapshot."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "project-delivery"
DEST = ROOT / "power-bi"
REPORT = DEST / "Delivery.Report"
MODEL = DEST / "Delivery.SemanticModel"
BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
CURRENCY = "$#,0;($#,0);$0"
MEASURES = {
    "Approved budget": ("SUM(Portfolio[budget_usd])", CURRENCY),
    "Recorded spend": ("SUM(Portfolio[spend_usd])", CURRENCY),
    "Cost variance": ("[Recorded spend] - [Approved budget]", CURRENCY),
    "Budget consumed": ("DIVIDE([Recorded spend], [Approved budget])", "0.0%"),
    "Overdue milestones": ("SUM(Portfolio[overdue])", "0"),
    "Completion rate": ("DIVIDE(SUM(Portfolio[completed]), SUM(Portfolio[milestones]))", "0.0%"),
}

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n",encoding="utf-8")

def pbir(path, kind, **fields):
    write(path, {"$schema":BASE + kind + "/1.0.0/schema.json", **fields})

def embed_table():
    with (ROOT / "results/portfolio.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    strings = {"project_id","project","program"}
    def m_value(field,value):
        if field in strings:
            return '"' + value.replace('"','""') + '"'
        return str(int(value))
    table_type = ", ".join(f"{key} = {'text' if key in strings else 'Int64.Type'}" for key in fields)
    records = ["{" + ", ".join(m_value(k,row[k]) for k in fields) + "}" for row in rows]
    expression = "#table(type table [" + table_type + "], {" + ", ".join(records) + "})"
    return {"name":"Portfolio",
            "columns":[{"name":k,"dataType":"string" if k in strings else "int64","sourceColumn":k} for k in fields],
            "partitions":[{"name":"Portfolio","mode":"import","source":{"type":"m","expression":expression}}],
            "measures":[{"name":k,"expression":v[0],"formatString":v[1]} for k,v in MEASURES.items()]}

def visual(page, name, kind, rect, roles, order):
    state = {}
    for role, fields in roles.items():
        projections = []
        for field in fields:
            entity = "Measure" if field in MEASURES else "Column"
            projections.append({"field":{entity:{"Expression":{"SourceRef":{"Entity":"Portfolio"}},"Property":field}},
                                "queryRef":"Portfolio."+field,"nativeQueryRef":field})
        state[role]={"projections":projections}
    pbir(page / "visuals" / name / "visual.json","visualContainer",name=name,
         position=dict(zip(("x","y","width","height","z","tabOrder"),(*rect,order,order))),
         visual={"visualType":kind,"query":{"queryState":state}})

def main():
    write(DEST / "Delivery.pbip",{"version":"1.0","artifacts":[{"report":{"path":"Delivery.Report"}}],"settings":{"enableAutoRecovery":True}})
    write(REPORT / "definition.pbir",{"version":"4.0","datasetReference":{"byPath":{"path":"../Delivery.SemanticModel"}}})
    write(MODEL / "definition.pbism",{"version":"1.0","settings":{}})
    write(MODEL / "model.bim",{"name":"Delivery","compatibilityLevel":1550,"model":{"culture":"en-US","defaultPowerBIDataSourceVersion":"powerBI_V3","tables":[embed_table()]}})
    definition=REPORT / "definition"
    page_id="a172cf328c1c482b8e35"
    page=definition / "pages" / page_id
    pbir(definition / "version.json","versionMetadata",version="2.0.0")
    pbir(definition / "report.json","report",layoutOptimization="None",themeCollection={"baseTheme":{"name":"CY24SU06","reportVersionAtImport":"5.55","type":"SharedResources"}})
    pbir(definition / "pages/pages.json","pagesMetadata",pageOrder=[page_id],activePageName=page_id)
    pbir(page / "page.json","page",name=page_id,displayName="Delivery review",displayOption="FitToPage",width=1280,height=720)
    for n,measure in enumerate(("Approved budget","Recorded spend","Overdue milestones")):
        visual(page,f"cametric{n}","card",(20+n*414,16,402,116),{"Values":[measure]},n)
    visual(page,"programslicer","slicer",(20,150,240,238),{"Values":["program"]},3)
    visual(page,"spendbyproject","clusteredBarChart",(274,150,970,238),{"Category":["project"],"Y":["Approved budget","Recorded spend"]},4)
    visual(page,"details","tableEx",(20,410,1224,282),{"Values":["project","Cost variance","Budget consumed","Overdue milestones","Completion rate"]},5)

if __name__ == "__main__":
    main()
