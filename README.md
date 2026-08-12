# Ledger Lens

*A clear view into your startup's financial health.*

Upload a monthly financials spreadsheet and instantly get:

- **Runway** — months of cash left at current burn
- **MoM Revenue Growth**
- **Gross Margin**
- **Burn Multiple** — $ spent per $ of new revenue generated
- **Health Score (0-100, A-F)** — a weighted composite of the above, with a
  full breakdown of how each category contributed
- **Auto-generated insights** — plain-language takeaways, no LLM required
- **Interactive dashboard** — revenue vs. costs, cash trend, burn trend,
  growth trend, and CAC (if customer data is provided)

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`),
and click **Load sample data** in the sidebar to try it instantly — or
upload your own file.

## Expected data format

A CSV or Excel file with one row per month:

| Column | Required? | Description |
|---|---|---|
| `month` | Yes | e.g. `2025-01` or `Jan 2025` |
| `revenue` | Yes | Monthly revenue |
| `cogs` | Yes | Cost of goods sold |
| `opex` | Yes | Operating expenses |
| `cash_balance` | Yes | Cash on hand at month end |
| `customers` | No | Total active customers |
| `new_customers` | No | New customers acquired that month |
| `churned_customers` | No | Customers lost that month |
| `cac_spend` | No | Sales & marketing spend that month (used with `new_customers` to compute CAC) |

See `sample_data.csv` for a working example.

## How the Health Score works

The score is a weighted average of four sub-scores, each 0-100:

| Category | Weight | 100 pts when... | 0 pts when... |
|---|---|---|---|
| Runway | 35% | 18+ months of runway (or profitable) | 0 months left |
| Growth | 25% | ≥15% MoM revenue growth (avg, last 3 mo) | ≤ -10% MoM |
| Gross Margin | 20% | ≥80% gross margin (avg, last 3 mo) | 0% margin |
| Burn Efficiency | 20% | Burn multiple ≤ 1x | Burn multiple ≥ 5x |

Thresholds are simple by design — see `scoring.py` to tune them to your
own benchmarks (e.g. SaaS vs. hardware vs. marketplace businesses will
have very different "healthy" gross margins).

## Project structure

```
.
├── app.py             # Streamlit dashboard (UI layer only)
├── analyzer.py         # Pure data-processing functions (no UI dependency)
├── scoring.py           # Health score + rule-based insight generation
├── sample_data.csv       # Example dataset
└── requirements.txt
```

`analyzer.py` and `scoring.py` have no Streamlit dependency, so they're easy
to unit test or reuse in a CLI/notebook/API context later.

## Ideas for extending this

- Add industry benchmarks (SaaS vs. e-commerce vs. marketplace) and let the
  user pick a profile that adjusts the scoring thresholds
- Support multi-scenario "what-if" sliders (e.g. "what if I cut opex 15%?")
- Add a PDF export of the dashboard for sharing with investors
- Plug in an LLM to turn the insights list into a narrative memo
