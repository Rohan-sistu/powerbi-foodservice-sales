// Power Query (M) - every query in the model, in load order.

// ---------- DataFolder (parameter): path to data/raw/ ending with a backslash ----------

// ---------- Translate (function) ----------
(value as nullable text, pairs as list) as nullable text =>
    let
        hit = List.Select(pairs, (p) => p{0} = value)
    in
        if List.IsEmpty(hit) then value else hit{0}{1}

// ---------- LinesClean (helper, not loaded) ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "order_lines.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // "en-US": this file uses a dot as decimal separator. On a German PC 7.37 would otherwise become 737.
    Types    = Table.TransformColumnTypes(Headers, {{"line_id", Int64.Type}, {"order_id", Int64.Type}, {"quantity", Int64.Type}, {"unit_price_eur", type number}, {"discount_pct", type number}}, "en-US"),
    NoDups   = Table.Distinct(Types, {"line_id"}),
    // Sign errors: sales lines ("Verkauf") must not have a negative quantity; real returns are "Retoure".
    SignFix  = Table.ReplaceValue(NoDups, each [quantity], each if [line_type] = "Verkauf" and [quantity] < 0 then -[quantity] else [quantity], Replacer.ReplaceValue, {"quantity"}),
    English  = Table.TransformColumns(SignFix, {{"line_type", each Translate(_, {{"Verkauf", "Sale"}, {"Retoure", "Return"}}), type text}}),
    Amount   = Table.AddColumn(English, "line_amount_eur", each [quantity] * [unit_price_eur], type number),
    Band     = Table.AddColumn(Amount, "discount_band", each if [discount_pct] = 0 then "0 %" else if [discount_pct] <= 0.05 then "1–5 %" else if [discount_pct] <= 0.09 then "6–9 %" else "10 %+", type text),
    BandSort = Table.AddColumn(Band, "discount_band_sort", each if [discount_pct] = 0 then 1 else if [discount_pct] <= 0.05 then 2 else if [discount_pct] <= 0.09 then 3 else 4, Int64.Type)
in
    BandSort

// ---------- DimCustomer ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "customers.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    TrimId   = Table.TransformColumns(Headers, {{"customer_id", Text.Trim, type text}}),
    NoDups   = Table.Distinct(TrimId),
    CityMap  = {{"Muenchen", "München"}, {"münchen", "München"}, {"Koeln", "Köln"}, {"KÖLN", "Köln"}, {"Duesseldorf", "Düsseldorf"}, {"Nuernberg", "Nürnberg"}, {"Halle", "Halle (Saale)"}, {"Halle/Saale", "Halle (Saale)"}, {"Muenster", "Münster"}},
    FixCity  = Table.TransformColumns(NoDups, {{"city", each Translate(_, CityMap), type text}}),
    SegMap   = {{"Café/Bäckerei", "Café/Bakery"}, {"Kantine", "Canteen"}, {"Systemgastronomie", "Restaurant chain"}},
    RegMap   = {{"Nord", "North"}, {"Ost", "East"}, {"Süd", "South"}},
    English  = Table.TransformColumns(FixCity, {
                   {"segment", each Translate(_, SegMap), type text},
                   {"region", each Translate(_, RegMap), type text},
                   {"customer_name", each Text.Replace(Text.Replace(_, "Systemgastronomie", "Restaurant chain"), "Kantine", "Canteen"), type text}}),
    Types    = Table.TransformColumnTypes(English, {{"onboarding_date", type date}, {"payment_terms_days", Int64.Type}}, "en-US")
in
    Types

// ---------- DimProduct ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "products.csv"), [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // German export: comma decimals (22,75) -> convert with the German locale
    Types    = Table.TransformColumnTypes(Headers, {{"list_price_eur", type number}, {"unit_cost_eur", type number}}, "de-DE"),
    FillCat  = Table.ReplaceValue(Types, "", "Unassigned", Replacer.ReplaceValue, {"category"}),
    Organic  = Table.TransformColumns(FillCat, {{"is_organic", each _ = "ja", type logical}}),
    CatMap   = {{"Fleisch & Geflügel", "Meat & Poultry"}, {"Getränke", "Beverages"}, {"Molkereiprodukte", "Dairy"}, {"Non-Food & Hygiene", "Non-food & Hygiene"}, {"Obst & Gemüse", "Fruit & Vegetables"}, {"Tiefkühlkost", "Frozen food"}, {"Trockensortiment", "Dry goods"}},
    NameMap  = {{"Fleisch Artikel", "Meat item"}, {"Getränke Artikel", "Beverage item"}, {"Molkereiprodukte Artikel", "Dairy item"}, {"Non-Food Artikel", "Non-food item"}, {"Obst Artikel", "Produce item"}, {"Tiefkühlkost Artikel", "Frozen item"}, {"Trockensortiment Artikel", "Dry goods item"}},
    UnitMap  = {{"Karton", "Carton"}, {"Kiste", "Crate"}, {"Packung", "Pack"}, {"Stk", "Piece"}},
    English  = Table.TransformColumns(Organic, {
                   {"category", each Translate(_, CatMap), type text},
                   {"unit", each Translate(_, UnitMap), type text},
                   {"product_name", each let parts = Text.Split(_, " "), prefix = Text.Combine(List.RemoveLastN(parts, 1), " ") in Translate(prefix, NameMap) & " " & List.Last(parts), type text}})
in
    English

// ---------- DimRep ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "sales_reps.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    English  = Table.TransformColumns(Headers, {{"region", each Translate(_, {{"Nord", "North"}, {"Ost", "East"}, {"Süd", "South"}}), type text}}),
    Types    = Table.TransformColumnTypes(English, {{"hire_date", type date}}, "en-US")
in
    Types

// ---------- DimDate ----------
let
    Start    = #date(2024, 1, 1),
    Dates    = List.Dates(Start, Duration.Days(#date(2025, 12, 31) - Start) + 1, #duration(1, 0, 0, 0)),
    T        = Table.FromList(Dates, Splitter.SplitByNothing(), type table [Date = date]),
    Year     = Table.AddColumn(T, "Year", each Date.Year([Date]), Int64.Type),
    Quarter  = Table.AddColumn(Year, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    MonthNo  = Table.AddColumn(Quarter, "MonthNo", each Date.Month([Date]), Int64.Type),
    Month    = Table.AddColumn(MonthNo, "Month", each Date.ToText([Date], "MMM", "en-US"), type text),
    YearMon  = Table.AddColumn(Month, "Year-Month", each Date.ToText([Date], "yyyy-MM"), type text)
in
    YearMon

// ---------- FactOrders ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "orders.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types    = Table.TransformColumnTypes(Headers, {{"order_id", Int64.Type}, {"order_date", type date}, {"promised_delivery_date", type date}, {"actual_delivery_date", type date}}, "en-US"),
    TrimId   = Table.TransformColumns(Types, {{"customer_id", Text.Trim, type text}}),
    Channel  = Table.TransformColumns(TrimId, {{"channel", each Translate(_, {{"Außendienst", "Field sales"}, {"Telefon", "Phone"}, {"Webshop", "Web shop"}}), type text}}),
    OnTime   = Table.AddColumn(Channel, "on_time", each if [actual_delivery_date] <= [promised_delivery_date] then 1 else 0, Int64.Type)
in
    OnTime

// ---------- FactSales ----------
let
    Source   = Table.NestedJoin(LinesClean, {"order_id"}, FactOrders, {"order_id"}, "o", JoinKind.LeftOuter),
    Expand   = Table.ExpandTableColumn(Source, "o", {"order_date", "customer_id", "channel"}),
    Types    = Table.TransformColumnTypes(Expand, {{"order_date", type date}, {"customer_id", type text}, {"channel", type text}})
in
    Types

// ---------- FactInvoices ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "invoices.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types    = Table.TransformColumnTypes(Headers, {{"order_id", Int64.Type}, {"invoice_date", type date}, {"due_date", type date}}, "en-US"),
    // payment_date comes in two formats (2025-03-14 and 14.03.2025) or is empty (= not paid yet)
    PayDate  = Table.TransformColumns(Types, {{"payment_date", each if _ = "" or _ = null then null else if Text.Contains(_, ".") then Date.FromText(_, [Format = "dd.MM.yyyy", Culture = "de-DE"]) else Date.FromText(_, [Format = "yyyy-MM-dd", Culture = "en-US"]), type date}}),
    Amounts  = Table.Group(LinesClean, {"order_id"}, {{"amount_eur", each List.Sum([line_amount_eur]), type number}}),
    AddAmt   = Table.ExpandTableColumn(Table.NestedJoin(PayDate, {"order_id"}, Amounts, {"order_id"}, "a", JoinKind.LeftOuter), "a", {"amount_eur"}),
    AddCust  = Table.ExpandTableColumn(Table.NestedJoin(AddAmt, {"order_id"}, FactOrders, {"order_id"}, "o", JoinKind.LeftOuter), "o", {"customer_id"}),
    Cutoff   = #date(2026, 1, 31),
    Status   = Table.AddColumn(AddCust, "status", each if [payment_date] <> null then "Paid" else if [due_date] < Cutoff then "Overdue" else "Open", type text),
    PayDays  = Table.AddColumn(Status, "days_to_pay", each if [payment_date] <> null then Duration.Days([payment_date] - [invoice_date]) else null, Int64.Type),
    Late     = Table.AddColumn(PayDays, "paid_late", each if [payment_date] <> null and [payment_date] > [due_date] then 1 else 0, Int64.Type),
    Aging    = Table.AddColumn(Late, "overdue_age", each if [status] <> "Overdue" then null else let d = Duration.Days(Cutoff - [due_date]) in if d <= 30 then "1–30 days" else if d <= 60 then "31–60 days" else if d <= 90 then "61–90 days" else "> 90 days", type text),
    AgingSrt = Table.AddColumn(Aging, "overdue_age_sort", each if [overdue_age] = null then null else if [overdue_age] = "1–30 days" then 1 else if [overdue_age] = "31–60 days" then 2 else if [overdue_age] = "61–90 days" then 3 else 4, Int64.Type),
    FinalTyp = Table.TransformColumnTypes(AgingSrt, {{"amount_eur", type number}, {"customer_id", type text}})
in
    FinalTyp
