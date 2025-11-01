# utils.py (or wherever your readers live)
# utils.py (or wherever your readers live)
def _read_sap_credit_dataframe(uploaded_file):
    """
    Returns:
      credits_df: number, date, customer_name, salesman, document_total (positive)
      gp_pairs_df: customer_name, salesman, gp_total  (sum of GP over ALL rows in the file)
    """
    import pandas as pd
    from decimal import Decimal, InvalidOperation

    def _dec(x):
        s = "" if x is None else str(x)
        s = s.replace(",", "").strip()
        if s == "":
            return Decimal("0.00")
        try:
            return Decimal(s)
        except InvalidOperation:
            return Decimal("0.00")

    # --- Probe header ---
    uploaded_file.seek(0)
    probe = pd.read_excel(uploaded_file, header=None, nrows=30, dtype=str, engine="openpyxl")
    probe = probe.applymap(lambda v: v.strip() if isinstance(v, str) else v)

    expected_any = {
        "#", "Type", "Document Number", "Posting Date",
        "Customer/Supplier Name", "SlpName", "Total Amount", "GP"
    }
    header_row = 0
    for i in range(min(30, len(probe))):
        row_vals = set(str(v).strip() for v in probe.iloc[i].tolist() if v not in (None, ""))
        if len(expected_any.intersection(row_vals)) >= 3:
            header_row = i
            break

    # --- Read full sheet once ---
    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=header_row, dtype=str, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.applymap(lambda v: v.strip() if isinstance(v, str) else v)
    cols = list(df.columns)

    # Column resolvers
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

    c_type   = _pick(["Type"])
    c_date   = _pick(["Posting Date"], ["Document Date", "Date"])
    c_cust   = _pick(["Customer/Supplier Name"], ["Customer Name", "Customer", "BP Name", "BP"])
    c_sman   = _pick(["SlpName"], ["Sales Employee", "Salesman"], required=False)
    c_total  = _pick(["Total Amount"], ["Document Total", "Total", "Amount"])
    c_gp     = _pick(["GP"])  # required for this feature

    # Find the 2nd "#" if present, else Document Number
    hash_cols = [c for c in cols if c == "#" or c.startswith("#.")]
    c_num = (hash_cols[1] if len(hash_cols) >= 2 else None) or _pick(["Document Number"])

    # ---------- Build credits_df (only Type == Credit Note) ----------
    df_credit = df[df[c_type].astype(str).str.lower() == "credit note"].copy()

    credits_df = pd.DataFrame({
        "number":        df_credit[c_num].astype(str).str.strip(),
        "date_raw":      df_credit[c_date],
        "customer_name": df_credit[c_cust].astype(str).str.strip(),
        "salesman":      (df_credit[c_sman].astype(str).str.strip() if c_sman in df_credit.columns else ""),
        "amount_raw":    df_credit[c_total],
    })

    parsed = pd.to_datetime(credits_df["date_raw"], dayfirst=True, errors="coerce")
    mask_iso = parsed.isna() & credits_df["date_raw"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
    if mask_iso.any():
        parsed.loc[mask_iso] = pd.to_datetime(credits_df.loc[mask_iso, "date_raw"], errors="coerce")
    credits_df["date"] = parsed.dt.date

    credits_df["document_total"] = credits_df["amount_raw"].map(_dec).abs()
    credits_df["salesman"] = credits_df["salesman"].fillna("").astype(str).str.strip()
    credits_df = credits_df[(credits_df["number"] != "") & credits_df["date"].notna()]

    credits_df = (credits_df.groupby(["number", "date", "customer_name", "salesman"], as_index=False)
                             .agg({"document_total": "sum"}))
    credits_df = credits_df[["number", "date", "customer_name", "salesman", "document_total"]]

    # ---------- Build gp_pairs_df (ALL rows: Invoice + Credit Note) ----------

    # ---------- Build gp_pairs_df (sum of GP grouped by (customer, salesman)) ----------

    # Keep required columns, coerce GP, group by (customer, salesman)
    gp_src = pd.DataFrame({
        "date_raw":      df[c_date],
        "customer_name": df[c_cust].astype(str).str.strip(),
        "salesman":      (df[c_sman].astype(str).str.strip() if c_sman in df.columns else ""),
        "gp_raw":        df[c_gp],
    })
    parsed = pd.to_datetime(gp_src["date_raw"], dayfirst=True, errors="coerce")
    mask_iso = parsed.isna() & gp_src["date_raw"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
    if mask_iso.any():
        parsed.loc[mask_iso] = pd.to_datetime(gp_src.loc[mask_iso, "date_raw"], errors="coerce")
    gp_src["date"] = parsed.dt.date
    gp_src["gp"] = gp_src["gp_raw"].map(_dec)     # keep sign; file already carries sign for CN/Invoice
    gp_src["salesman"] = gp_src["salesman"].fillna("").astype(str).str.strip()
    gp_lines_df = gp_src[gp_src["date"].notna()][["date", "customer_name", "salesman", "gp"]]

    # ---------- Build gp_pairs_df ----------
    gp_pairs_df = (
        gp_lines_df.groupby(["customer_name", "salesman"], as_index=False)
                   .agg({"gp": "sum"})
                   .rename(columns={"gp": "gp_total"})
    )

    return credits_df, gp_pairs_df, gp_lines_df
