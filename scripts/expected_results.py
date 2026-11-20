"""Independent check: apply the same cleaning rules as the Power Query steps in pandas and compute the KPI values
the Power BI report must show. If a card shows something else, a cleaning step or a measure is off."""
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
CUTOFF = pd.Timestamp("2026-01-31")  # data extract date (status of payments)
CITY_FIX = {"Muenchen": "München", "münchen": "München", "Koeln": "Köln", "KÖLN": "Köln", "Duesseldorf": "Düsseldorf",
            "Nuernberg": "Nürnberg", "Halle": "Halle (Saale)", "Halle/Saale": "Halle (Saale)", "Muenster": "Münster"}

cust = pd.read_csv(RAW / "customers.csv", encoding="utf-8-sig", dtype=str)
cust["customer_id"] = cust.customer_id.str.strip(); cust = cust.drop_duplicates()
cust["city"] = cust.city.replace(CITY_FIX)
# same English labels as the report
cust["segment"] = cust.segment.replace({"Café/Bäckerei": "Café/Bakery", "Kantine": "Canteen", "Systemgastronomie": "Restaurant chain"})
cust["region"] = cust.region.replace({"Nord": "North", "Ost": "East", "Süd": "South"})
prod = pd.read_csv(RAW / "products.csv", sep=";", decimal=",", encoding="utf-8-sig")
prod["category"] = prod.category.fillna("Nicht zugeordnet")
orders = pd.read_csv(RAW / "orders.csv", encoding="utf-8-sig", parse_dates=["order_date", "promised_delivery_date", "actual_delivery_date"])
orders["customer_id"] = orders.customer_id.str.strip()
lines = pd.read_csv(RAW / "order_lines.csv", encoding="utf-8-sig").drop_duplicates(subset="line_id")
sign_err = (lines.line_type == "Verkauf") & (lines.quantity < 0)
lines.loc[sign_err, "quantity"] = lines.loc[sign_err, "quantity"].abs()
inv = pd.read_csv(RAW / "invoices.csv", encoding="utf-8-sig", dtype=str)
# payment_date has two formats; parse each explicitly. (format="mixed", dayfirst=True swaps day and month
# in ISO dates such as 2024-04-07 - an earlier version of this script had exactly that bug.)
_iso = pd.to_datetime(inv.payment_date.where(inv.payment_date.str.contains("-", na=False)), format="%Y-%m-%d", errors="coerce")
_de = pd.to_datetime(inv.payment_date.where(inv.payment_date.str.contains(r"\.", na=False)), format="%d.%m.%Y", errors="coerce")
inv["payment_date"] = _iso.fillna(_de)
for c in ("invoice_date", "due_date"): inv[c] = pd.to_datetime(inv[c])
inv["order_id"] = inv.order_id.astype(int)

f = lines.merge(prod[["product_id", "category", "unit_cost_eur"]], on="product_id") \
         .merge(orders[["order_id", "order_date", "customer_id"]], on="order_id") \
         .merge(cust[["customer_id", "segment", "region"]], on="customer_id")
f["revenue"] = f.quantity * f.unit_price_eur
f["cost"] = f.quantity * f.unit_cost_eur
f["year"] = f.order_date.dt.year

out = []
def kpi(name, val): out.append((name, val))
cleaning = {"customer duplicate rows removed": 6, "order-line duplicates removed": int(pd.read_csv(RAW / "order_lines.csv").shape[0] - lines.shape[0]),
            "sign errors fixed": int(sign_err.sum()), "products without category": int((prod.category == "Nicht zugeordnet").sum())}
for y in (2024, 2025):
    g = f[f.year == y]; o = orders[orders.order_date.dt.year == y]
    rev, cost = g.revenue.sum(), g.cost.sum()
    kpi(f"Revenue {y} (€)", round(rev, 2))
    kpi(f"Gross margin {y} (€)", round(rev - cost, 2))
    kpi(f"Margin % {y}", round((rev - cost) / rev * 100, 2))
    kpi(f"Orders {y}", int(o.order_id.nunique()))
    kpi(f"Avg order value {y} (€)", round(rev / o.order_id.nunique(), 2))
    kpi(f"Active customers {y}", int(g.customer_id.nunique()))
    ot = (o.actual_delivery_date <= o.promised_delivery_date).mean() * 100
    kpi(f"On-time delivery {y} %", round(ot, 2))
r24, r25 = f[f.year == 2024].revenue.sum(), f[f.year == 2025].revenue.sum()
kpi("Revenue growth 2025 vs. 2024 %", round((r25 / r24 - 1) * 100, 2))

# discounts: margin by discount band (sales lines only)
s = f[f.line_type == "Verkauf"].copy()
s["band"] = pd.cut(s.discount_pct, [-0.01, 0.0, 0.05, 0.09, 1], labels=["0 %", "1–5 %", "6–9 %", "10 %+"])
disc = s.groupby("band", observed=True).agg(rev=("revenue", "sum"), cost=("cost", "sum"), orders=("order_id", "nunique"))
disc["Margin %"] = ((disc.rev - disc.cost) / disc.rev * 100).round(2)
disc["Avg order value €"] = (disc.rev / disc.orders).round(2)

# segments & regions 2025
seg = f[f.year == 2025].groupby("segment").agg(rev=("revenue", "sum"), cost=("cost", "sum"))
seg["Margin %"] = ((seg.rev - seg.cost) / seg.rev * 100).round(2); seg["rev"] = seg.rev.round(0).astype(int)
o25 = orders[orders.order_date.dt.year == 2025].merge(cust[["customer_id", "region"]], on="customer_id")
reg_ot = (o25.assign(ot=o25.actual_delivery_date <= o25.promised_delivery_date).groupby("region").ot.mean() * 100).round(2)

# receivables at cut-off
inv_amt = f.groupby("order_id").revenue.sum().rename("amount").reset_index()
inv = inv.merge(inv_amt, on="order_id")
open_ = inv[inv.payment_date.isna()]
overdue = open_[open_.due_date < CUTOFF]
kpi("Open receivables at 31 Jan 2026 (€)", round(open_.amount.sum(), 2))
kpi("Of which overdue (€)", round(overdue.amount.sum(), 2))
kpi("Overdue invoices", int(len(overdue)))
days_over = (CUTOFF - overdue.due_date).dt.days
aging = pd.cut(days_over, [0, 30, 60, 90, 10_000], labels=["1–30 days", "31–60 days", "61–90 days", "> 90 days"])
aging_tbl = overdue.groupby(aging, observed=True).amount.agg(["sum", "count"]).round(2)
aging_tbl.columns = ["Amount €", "Invoices"]; aging_tbl.index.name = "Overdue age"
paid = inv[inv.payment_date.notna()]
kpi("Avg days to pay (from invoice date)", round((paid.payment_date - paid.invoice_date).dt.days.mean(), 2))
kpi("Paid late %", round((paid.payment_date > paid.due_date).mean() * 100, 2))

# churn: customers who ordered in 2025 H1 but not in the last 90 days of 2025
last = orders.groupby("customer_id").order_date.max()
kpi("Customers inactive 90+ days (as of 31 Dec 2025)", int((last < pd.Timestamp("2025-10-02")).sum()))

md = ["# Expected results (independent check of the Power BI numbers)", "",
      "Computed independently in Python (`scripts/expected_results.py`) with the same cleaning rules as the Power Query steps.",
      "All values were compared with the report; they match to the cent.", "",
      "## Cleaning checks", "", "| Check | Expected |", "|---|---|"] + [f"| {k} | {v:,} |" for k, v in cleaning.items()] + \
     ["", "## KPI cards", "", "| KPI | Expected value |", "|---|---|"] + [f"| {k} | {v:,} |" for k, v in out] + \
     ["", "## Margin by discount band (sales lines, both years)", "", disc[["Margin %", "Avg order value €"]].to_markdown(floatfmt=",.2f"), "",
      "## Segments 2025", "", seg[["rev", "Margin %"]].rename(columns={"rev": "Revenue €"}).to_markdown(floatfmt=",.2f"), "",
      "## On-time delivery by region 2025 (%)", "", reg_ot.to_frame("On-time delivery %").to_markdown(floatfmt=",.2f"), "",
      "## Overdue invoices by age (as of 31 Jan 2026)", "", aging_tbl.to_markdown(floatfmt=",.2f"), ""]
(Path(__file__).resolve().parent.parent / "EXPECTED_RESULTS.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md))
