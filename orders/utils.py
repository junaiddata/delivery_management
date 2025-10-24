# utils.py (or wherever your readers live)
def _read_sap_credit_dataframe(uploaded_file):
    """
    Reads the credit export:
      Columns typically seen:
        ['#', 'Type', 'Document Number', 'Posting Date',
         'Customer/Supplier No.', 'Customer/Supplier Name', 'SlpName',
         'ItemCode', 'Dscription', 'FirmName', 'Quantity', 'Rate',
         'Total Amount', 'GP']

    Rules:
      - Keep ONLY rows where Type == 'Credit Note'
      - Ignore the first '#' column; use the 2nd '#' if present; otherwise use 'Document Number'
      - Use Posting Date, Customer/Supplier Name, SlpName, Total Amount
      - Amount is stored as POSITIVE (abs) and later subtracted in analysis
      - Aggregate multiple lines per credit number/customer/salesman/date
    """
    import pandas as pd
    from decimal import Decimal, InvalidOperation

    def _dec(x):
        s = "" if x is None else str(x)
        s = s.replace(",", "").strip()
        if not s:
            return Decimal("0.00")
        try:
            return Decimal(s)
        except InvalidOperation:
            return Decimal("0.00")

    # 1) Probe header
    uploaded_file.seek(0)
    probe = pd.read_excel(uploaded_file, header=None, nrows=30, dtype=str, engine="openpyxl")
    probe = probe.applymap(lambda v: v.strip() if isinstance(v, str) else v)
    expected_any = {
        "#", "Type", "Document Number", "Posting Date",
        "Customer/Supplier Name", "SlpName", "Total Amount"
    }
    header_row = 0
    for i in range(min(30, len(probe))):
        row_vals = set(str(v).strip() for v in probe.iloc[i].tolist() if v not in (None, ""))
        if len(expected_any.intersection(row_vals)) >= 3:
            header_row = i
            break

    # 2) Read full with detected header
    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=header_row, dtype=str, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.applymap(lambda v: v.strip() if isinstance(v, str) else v)
    cols = list(df.columns)

    # Resolve columns robustly
    def _pick(names, variants=None, required=True):
        lc = {c.lower(): c for c in cols}
        for n in names:
            c = lc.get(n.lower())
            if c: return c
        if variants:
            for v in variants:
                c = lc.get(v.lower())
                if c: return c
        if required:
            raise ValueError(f"Missing required column among {names} / {variants}. Seen: {cols}")
        return None

    c_type  = _pick(["Type"])
    c_date  = _pick(["Posting Date"], ["Document Date", "Date"])
    c_cust  = _pick(["Customer/Supplier Name"], ["Customer Name", "Customer", "BP Name", "BP"])
    c_sman  = _pick(["SlpName"], ["Sales Employee", "Salesman"], required=False)
    c_total = _pick(["Total Amount"], ["Document Total", "Total", "Amount"])
    # 2nd '#' if present, else Document Number
    hash_cols = [c for c in cols if c == "#" or c.startswith("#.")]
    c_num = (hash_cols[1] if len(hash_cols) >= 2 else None) or _pick(["Document Number"])

    # 3) Keep ONLY Credit Note type
    df = df[df[c_type].astype(str).str.strip().str.lower() == "credit note"].copy()

    # 4) Build normalized frame
    out = pd.DataFrame({
        "number": df[c_num].astype(str).str.strip(),
        "date_raw": df[c_date],
        "customer_name": df[c_cust].astype(str).str.strip(),
        "salesman": (df[c_sman].astype(str).str.strip() if c_sman in df.columns else ""),
        "amount_raw": df[c_total],
    })

    # Parse date robustly
    parsed = pd.to_datetime(out["date_raw"], dayfirst=True, errors="coerce")
    mask_iso = parsed.isna() & out["date_raw"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
    if mask_iso.any():
        parsed.loc[mask_iso] = pd.to_datetime(out.loc[mask_iso, "date_raw"], errors="coerce")
    out["date"] = parsed.dt.date

    # Amount as positive (abs) so we always subtract later
    out["document_total"] = out["amount_raw"].map(_dec).abs()

    # Trims & drop invalids
    out["salesman"] = out["salesman"].fillna("").astype(str).str.strip()
    out = out[(out["number"] != "") & out["date"].notna()]

    # 5) Aggregate multiple lines per credit number/customer/salesman/date
    out = (out.groupby(["number", "date", "customer_name", "salesman"], as_index=False)
              .agg({"document_total": "sum"}))

    return out[["number", "date", "customer_name", "salesman", "document_total"]]
