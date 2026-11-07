# SQL & Power BI portfolio

**Nasratullah Shinwari** · Project Management Professional (PMP) · Microsoft Certified: Power BI Data Analyst Associate and SQL AI Developer Associate

Three case studies use fictional data to answer operational questions. Each includes the source records, SQL, results, and a dashboard that opens on a Mac or PC.

| Case study | Decision | Tools |
|---|---|---|
| [IT service desk response](support-sla/) | Which support queues miss response targets, and which tickets need attention now? | SQLite, Power BI, DAX, Python |
| [Project delivery review](project-delivery/) | Which projects need a budget or schedule review first? | SQLite, Power BI, DAX, Python |
| [Marketplace contribution](marketplace-profit/) | Which products earn money after refunds, shipping, fees, and advertising? | SQLite, Python |

### IT service desk response

![First-response performance for four support queues](support-sla/preview.svg)

The Identity queue missed 16 first-response targets. The report separates unanswered tickets that are already overdue from those still within their response window. [Inspect the SQL, Power BI report, and ticket-level results](support-sla/).

### Project delivery review

![Budget use for six fictional projects. Two exceed budget, with three overdue milestones across the portfolio.](project-delivery/preview.svg)

Overall spend is below the portfolio budget, but that total hides two project overruns. Cedar Intake Retrofit is $46,500 over budget and has an overdue readiness review. [Explore the SQL and Power BI project](project-delivery/).

### Marketplace contribution

![Contribution by product. The folding kettle is the only loss-making product.](marketplace-profit/preview.svg)

The folding kettle generated $1,121.66 in gross sales and lost $165.67 after variable costs and advertising. The case study traces that result to the underlying order lines and charges. [Explore the profit analysis](marketplace-profit/).

### Run the projects

Download the repository with **Code → Download ZIP** and unzip it. Open any project's **dashboard.html** in a browser to filter the results. The delivery and service desk projects also include native Power BI Desktop reports for Windows.

To reproduce the results, run the following commands from the repository root with Python 3.10 or newer. No additional Python packages or database server are required.

```sh
python3 run.py
python3 -m unittest -v
python3 tools/build_reports.py
python3 tools/build_previews.py
python3 tools/build_powerbi.py
python3 tools/build_support.py
```

All projects, transactions, costs, dates, and products are illustrative. The data come from no employer, client, or customer records.
