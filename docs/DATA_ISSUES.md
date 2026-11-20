# Data quality issues in the raw export

The raw files imitate a real ERP/CRM export. These problems show up in Power Query's column profiling and filters; each one is fixed in the queries (see `power_query.m`).

| File | Issue | Scale | Fix (Power Query) | Why it matters |
|---|---|---|---|---|
| customers.csv | Trailing spaces in `customer_id` | 6 IDs | Trim | Joins fail silently → revenue without customer |
| customers.csv | Exact duplicate rows | 6 rows | Remove duplicates | Customer counted twice, relationship error ("not unique") |
| customers.csv | City spelled several ways (Muenchen, münchen, KÖLN, Halle/Saale …) | ~30 % of rows in affected cities | Replace values / mapping | Region & city charts split one city into several bars |
| products.csv | Semicolon delimiter + comma decimals (German locale) | whole file | Delimiter `;`, change type using locale de-DE | 22,75 read as 2275 or as text |
| products.csv | Missing `category` | 9 products | Replace empty → "Unassigned" | Blank category in visuals |
| order_lines.csv | Dot decimals | whole file | Change type using locale en-US | On German Windows 7.37 → 737 (100× revenue!) |
| order_lines.csv | Exact duplicate lines (double export) | 3,296 rows (~0.8 %) | Remove duplicates on `line_id` | Revenue overstated |
| order_lines.csv | Negative quantity on `Verkauf` lines (sign error) | 40 lines | if Verkauf and qty < 0 then −qty | Revenue understated; real returns are `Retoure` |
| invoices.csv | `payment_date` in two formats (ISO and dd.MM.yyyy) | ~35 % German format | Parse by format | Wrong or failed dates → wrong payment KPIs |
| all files | Labels exported in German (segments, regions, categories, channels, line types) | every row | Translate to English with a small mapping function after cleaning | Report audience reads English |
| invoices.csv | Empty `payment_date` | unpaid invoices | null = not paid | Basis for open/overdue receivables |

Legitimate data that looks odd but is **not** an error: `Retoure` lines with negative quantity (customer returns). In the report they are shown as `Return`, sales lines as `Sale`.
