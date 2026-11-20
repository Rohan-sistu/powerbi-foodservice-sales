"""Generate a realistic (synthetic) B2B food-service wholesale dataset for a Power BI portfolio project.

Business: a German food-service wholesaler supplying restaurants, hotels, canteens, cafés and chains.
Period: 2024-01-01 .. 2025-12-31. Seeded, so the output is reproducible.

The RAW files deliberately contain realistic data-quality problems that must be fixed in Power Query
(see BUILD_GUIDE.md, Step 2). Every problem is documented in DATA_ISSUES.md.
"""
import csv, random, datetime as dt
from pathlib import Path
import numpy as np

rng = np.random.default_rng(42); random.seed(42)
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"; OUT.mkdir(parents=True, exist_ok=True)
START, END = dt.date(2024, 1, 1), dt.date(2025, 12, 31)

REGIONS = {
    "Nord": ["Hamburg", "Bremen", "Kiel", "Hannover", "Oldenburg"],
    "Ost": ["Berlin", "Leipzig", "Dresden", "Halle (Saale)", "Erfurt"],
    "Süd": ["München", "Nürnberg", "Stuttgart", "Augsburg", "Freiburg"],
    "West": ["Köln", "Düsseldorf", "Essen", "Dortmund", "Münster"],
}
SEGMENTS = {  # share, avg lines per order, orders per month, discount propensity
    "Restaurant": (0.38, 5, 4.0, 0.25), "Hotel": (0.17, 8, 5.0, 0.35),
    "Kantine": (0.15, 9, 7.0, 0.55), "Café/Bäckerei": (0.18, 4, 4.5, 0.15),
    "Systemgastronomie": (0.12, 10, 8.0, 0.65),
}
CATS = {  # category: (n_products, price range €, margin range)
    "Fleisch & Geflügel": (40, (6, 28), (0.18, 0.28)), "Molkereiprodukte": (35, (1.5, 9), (0.20, 0.30)),
    "Tiefkühlkost": (45, (3, 22), (0.26, 0.38)), "Trockensortiment": (50, (1, 12), (0.30, 0.42)),
    "Getränke": (40, (0.8, 18), (0.28, 0.40)), "Obst & Gemüse": (35, (0.9, 7), (0.16, 0.26)),
    "Non-Food & Hygiene": (25, (2, 35), (0.38, 0.50)),
}
UNITS = {"Fleisch & Geflügel": "kg", "Molkereiprodukte": "Stk", "Tiefkühlkost": "Karton", "Trockensortiment": "Stk",
         "Getränke": "Kiste", "Obst & Gemüse": "kg", "Non-Food & Hygiene": "Packung"}
FIRST = ["Anna", "Jonas", "Lea", "Felix", "Marie", "Lukas", "Sophie", "Paul", "Laura", "Tim", "Nina", "Ben"]
LAST = ["Schmidt", "Müller", "Weber", "Fischer", "Wagner", "Becker", "Hoffmann", "Koch", "Richter", "Klein", "Wolf", "Neumann"]

# ---------- sales reps: 3 per region ----------
reps = []
for i, (reg, _) in enumerate([(r, c) for r in REGIONS for c in range(3)]):
    reps.append({"rep_id": f"R{i+1:02d}", "rep_name": f"{FIRST[i]} {LAST[i]}", "region": reg,
                 "hire_date": (dt.date(2015, 1, 1) + dt.timedelta(days=int(rng.integers(0, 3000)))).isoformat()})

# ---------- products ----------
products = []; pid = 1000
for cat, (n, (lo, hi), (mlo, mhi)) in CATS.items():
    for k in range(n):
        price = round(float(rng.uniform(lo, hi)), 2); margin = float(rng.uniform(mlo, mhi))
        products.append({"product_id": f"P{pid}", "product_name": f"{cat.split(' ')[0]} Artikel {k+1:03d}",
                         "category": cat, "unit": UNITS[cat], "list_price_eur": price,
                         "unit_cost_eur": round(price * (1 - margin), 2), "is_organic": bool(rng.random() < 0.18)})
        pid += 1
# popularity weights (long tail)
pop = rng.pareto(1.6, len(products)) + 0.2; pop /= pop.sum()

# ---------- customers ----------
customers = []; seg_names = list(SEGMENTS); seg_p = [SEGMENTS[s][0] for s in seg_names]
for i in range(520):
    seg = rng.choice(seg_names, p=seg_p); reg = rng.choice(list(REGIONS), p=[0.24, 0.22, 0.28, 0.26])
    city = rng.choice(REGIONS[reg])
    onboard = START - dt.timedelta(days=int(rng.integers(0, 1500))) if rng.random() < 0.7 else \
        START + dt.timedelta(days=int(rng.integers(0, 650)))
    churn = None
    if rng.random() < 0.16:  # ~16% stop ordering at some point
        c = max(onboard, START) + dt.timedelta(days=int(rng.integers(60, 700)))
        churn = c if c < END else None
    rep = rng.choice([r for r in reps if r["region"] == reg])
    customers.append({"customer_id": f"K{10001+i}", "customer_name": f"{seg.split('/')[0]} {city.split(' ')[0]} {i+1:03d}",
                      "segment": seg, "city": city, "region": reg, "rep_id": rep["rep_id"],
                      "onboarding_date": onboard.isoformat(), "_churn": churn,
                      "_size": float(rng.lognormal(0, 0.5)), "payment_terms_days": int(rng.choice([14, 30, 30, 30, 45]))})

# ---------- orders, lines, deliveries, invoices ----------
def season(day, seg, cat):
    m = day.month; f = 1.0
    if seg == "Hotel": f *= 1.25 if m in (7, 8, 12) else 0.9 if m in (1, 2) else 1.0
    if seg == "Kantine": f *= 0.55 if m == 8 else 0.8 if m == 12 else 1.05
    if seg in ("Restaurant", "Café/Bäckerei"): f *= 1.15 if m in (5, 6, 7, 8, 9) else 0.9 if m in (1, 2) else 1.0
    return f

orders, lines, invoices = [], [], []
oid, lid = 500000, 1
days = [START + dt.timedelta(days=d) for d in range((END - START).days + 1)]
growth = lambda d: 1.0 + 0.06 * ((d - START).days / 365)  # ~6% p.a. organic growth
for c in customers:
    seg = c["segment"]; _, avg_lines, per_month, disc_p = SEGMENTS[seg]
    first = max(START, dt.date.fromisoformat(c["onboarding_date"])); last = c["_churn"] or END
    for d in days:
        if d < first or d > last or d.weekday() == 6: continue
        p = per_month / 26 * season(d, seg, None) * min(c["_size"], 2.5) ** 0.5 * growth(d)
        if c["_churn"] and (last - d).days < 90: p *= 0.6  # activity drops before churn
        if rng.random() > p: continue
        oid += 1
        # delivery: next working day promised; Ost/winter & Süd/Dec more delays
        promised = d + dt.timedelta(days=1 if d.weekday() < 5 else 2)
        late_p = 0.05 + (0.07 if c["region"] == "Ost" and d.month in (12, 1, 2) else 0) + (0.04 if d.month == 12 else 0) \
                 + (0.03 if c["region"] == "Ost" and d.year == 2024 else 0)
        delivered = promised + dt.timedelta(days=int(rng.choice([1, 1, 2, 3]))) if rng.random() < late_p else promised
        disc_level = 0.0
        if rng.random() < disc_p:
            disc_level = float(rng.choice([0.03, 0.05, 0.08, 0.10, 0.12, 0.15], p=[0.25, 0.25, 0.2, 0.15, 0.1, 0.05]))
        n_lines = max(1, int(rng.poisson(avg_lines)))
        chosen = rng.choice(len(products), size=min(n_lines, 60), replace=False, p=pop)
        total = 0.0
        for idx in chosen:
            pr = products[idx]; qty = int(max(1, rng.poisson(6 * c["_size"])))
            # deep discounts barely increase volume (the business insight to discover)
            if disc_level >= 0.10: qty = int(qty * rng.uniform(0.95, 1.12))
            unit_price = round(pr["list_price_eur"] * (1 - disc_level), 2)
            lines.append({"line_id": lid, "order_id": oid, "product_id": pr["product_id"], "quantity": qty,
                          "unit_price_eur": unit_price, "discount_pct": disc_level, "line_type": "Verkauf"})
            total += qty * unit_price; lid += 1
        if rng.random() < 0.012:  # occasional return line
            pr = products[chosen[0]]
            lines.append({"line_id": lid, "order_id": oid, "product_id": pr["product_id"], "quantity": -int(rng.integers(1, 4)),
                          "unit_price_eur": round(pr["list_price_eur"] * (1 - disc_level), 2), "discount_pct": disc_level,
                          "line_type": "Retoure"}); lid += 1
        orders.append({"order_id": oid, "order_date": d.isoformat(), "customer_id": c["customer_id"],
                       "channel": rng.choice(["Webshop", "Außendienst", "Telefon"], p=[0.48, 0.32, 0.20]),
                       "promised_delivery_date": promised.isoformat(), "actual_delivery_date": delivered.isoformat()})
        # invoice & payment
        inv_date = delivered; due = inv_date + dt.timedelta(days=c["payment_terms_days"])
        r = rng.random(); late_bias = 0.10 if seg == "Restaurant" else 0.05
        if r < 0.80 - late_bias:  pay = due - dt.timedelta(days=int(rng.integers(0, c["payment_terms_days"])))
        elif r < 0.97:            pay = due + dt.timedelta(days=int(rng.integers(1, 45)))
        else:                     pay = None  # never paid
        if pay and pay > dt.date(2026, 1, 31): pay = None  # data cut-off: not yet paid
        invoices.append({"invoice_id": f"RE-{oid}", "order_id": oid, "invoice_date": inv_date, "due_date": due,
                         "payment_date": pay})

# ---------- write RAW files with realistic data-quality issues ----------
def w(name, rows, fields, delim=","):
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=fields, delimiter=delim); wr.writeheader(); wr.writerows(rows)

# reps: clean
w("sales_reps.csv", reps, ["rep_id", "rep_name", "region", "hire_date"])

# products: German export -> semicolon delimiter + comma decimals; 9 products missing category
prod_rows = []
missing_cat = set(rng.choice(len(products), 9, replace=False).tolist())
for i, p in enumerate(products):
    prod_rows.append({**p, "category": "" if i in missing_cat else p["category"],
                      "list_price_eur": f"{p['list_price_eur']:.2f}".replace(".", ","),
                      "unit_cost_eur": f"{p['unit_cost_eur']:.2f}".replace(".", ","),
                      "is_organic": "ja" if p["is_organic"] else "nein"})
w("products.csv", prod_rows, ["product_id", "product_name", "category", "unit", "list_price_eur", "unit_cost_eur", "is_organic"], ";")

# customers: inconsistent city spellings, trailing spaces in IDs, 6 exact duplicate rows
variants = {"München": ["Muenchen", "münchen"], "Köln": ["Koeln", "KÖLN"], "Düsseldorf": ["Duesseldorf"],
            "Nürnberg": ["Nuernberg"], "Halle (Saale)": ["Halle", "Halle/Saale"], "Münster": ["Muenster"]}
cust_rows = []
for c in customers:
    city = c["city"]
    if city in variants and rng.random() < 0.3: city = random.choice(variants[city])
    cid = c["customer_id"] + (" " if rng.random() < 0.02 else "")
    cust_rows.append({k: v for k, v in c.items() if not k.startswith("_")} | {"city": city, "customer_id": cid})
cust_rows += [dict(cust_rows[i]) for i in rng.choice(len(cust_rows), 6, replace=False)]
w("customers.csv", cust_rows, ["customer_id", "customer_name", "segment", "city", "region", "rep_id", "onboarding_date", "payment_terms_days"])

w("orders.csv", orders, ["order_id", "order_date", "customer_id", "channel", "promised_delivery_date", "actual_delivery_date"])

# order lines: ~0.8% exact duplicate lines (system double-export), 40 sign errors (negative qty on 'Verkauf')
line_rows = [dict(l) for l in lines]
for i in rng.choice(len(line_rows), 40, replace=False):
    if line_rows[i]["line_type"] == "Verkauf": line_rows[i]["quantity"] = -abs(line_rows[i]["quantity"])
dups = [dict(line_rows[i]) for i in rng.choice(len(line_rows), int(len(line_rows) * 0.008), replace=False)]
line_rows += dups; random.shuffle(line_rows)
w("order_lines.csv", line_rows, ["line_id", "order_id", "product_id", "quantity", "unit_price_eur", "discount_pct", "line_type"])

# invoices: mixed date formats in payment_date (ISO vs German dd.mm.yyyy), empty = unpaid
inv_rows = []
for inv in invoices:
    pay = inv["payment_date"]
    s = "" if pay is None else (pay.strftime("%d.%m.%Y") if rng.random() < 0.35 else pay.isoformat())
    inv_rows.append({"invoice_id": inv["invoice_id"], "order_id": inv["order_id"], "invoice_date": inv["invoice_date"].isoformat(),
                     "due_date": inv["due_date"].isoformat(), "payment_date": s})
w("invoices.csv", inv_rows, ["invoice_id", "order_id", "invoice_date", "due_date", "payment_date"])

print(f"customers {len(customers)} (+6 dup rows), products {len(products)}, reps {len(reps)}, "
      f"orders {len(orders)}, lines {len(lines)} (+{len(dups)} dup rows), invoices {len(invoices)}")
