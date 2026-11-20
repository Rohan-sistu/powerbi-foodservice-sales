# Expected results (independent check of the Power BI numbers)

Computed independently in Python (`scripts/expected_results.py`) with the same cleaning rules as the Power Query steps.
All values were compared with the report; they match to the cent.

## Cleaning checks

| Check | Expected |
|---|---|
| customer duplicate rows removed | 6 |
| order-line duplicates removed | 3,296 |
| sign errors fixed | 40 |
| products without category | 9 |

## KPI cards

| KPI | Expected value |
|---|---|
| Revenue 2024 (€) | 12,315,674.03 |
| Gross margin 2024 (€) | 3,436,689.93 |
| Margin % 2024 | 27.91 |
| Orders 2024 | 26,789 |
| Avg order value 2024 (€) | 459.73 |
| Active customers 2024 | 453 |
| On-time delivery 2024 % | 93.71 |
| Revenue 2025 (€) | 14,512,784.6 |
| Gross margin 2025 (€) | 4,053,805.55 |
| Margin % 2025 | 27.93 |
| Orders 2025 | 31,354 |
| Avg order value 2025 (€) | 462.87 |
| Active customers 2025 | 489 |
| On-time delivery 2025 % | 94.27 |
| Revenue growth 2025 vs. 2024 % | 17.84 |
| Open receivables at 31 Jan 2026 (€) | 1,057,064.17 |
| Of which overdue (€) | 993,027.78 |
| Overdue invoices | 2,150 |
| Avg days to pay (from invoice date) | 23.84 |
| Paid late % | 23.44 |
| Customers inactive 90+ days (as of 31 Dec 2025) | 70 |

## Margin by discount band (sales lines, both years)

| band   |   Margin % |   Avg order value € |
|:-------|-----------:|--------------------:|
| 0 %    |      30.07 |              441.07 |
| 1–5 %  |      27.21 |              514.28 |
| 6–9 %  |      23.96 |              499.68 |
| 10 %+  |      21.08 |              458.68 |

## Segments 2025

| segment          |    Revenue € |   Margin % |
|:-----------------|-------------:|-----------:|
| Café/Bakery      | 1,419,270.00 |      29.14 |
| Canteen          | 3,717,763.00 |      27.33 |
| Hotel            | 2,922,486.00 |      28.48 |
| Restaurant       | 3,133,373.00 |      28.78 |
| Restaurant chain | 3,319,894.00 |      26.81 |

## On-time delivery by region 2025 (%)

| region   |   On-time delivery % |
|:---------|---------------------:|
| East     |                92.59 |
| North    |                94.78 |
| South    |                94.83 |
| West     |                94.65 |

## Overdue invoices by age (as of 31 Jan 2026)

| Overdue age   |   Amount € |   Invoices |
|:--------------|-----------:|-----------:|
| 1–30 days     | 208,752.21 |     436.00 |
| 31–60 days    |  50,077.61 |     116.00 |
| 61–90 days    |  29,193.55 |      84.00 |
| > 90 days     | 705,004.41 |   1,514.00 |
