


def _read_sap_unified_dataframe(uploaded_file):
    """
    Returns 4 dataframes:
      invoices_df: number, date, customer_code, customer_name, salesman, document_total (float, +)
      credits_df : number, date, customer_code, customer_name, salesman, document_total (float, +)
      gp_lines_df: date,  customer_code, customer_name, salesman, gp (float, signed, aggregated)
      lines_df   : doc_type, number, date, customer_code, customer_name, salesman,
                   item_code, item_desc, quantity (signed), rate, amount (signed), gp (signed)
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

    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=0, dtype=str, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.applymap(lambda v: v.strip() if isinstance(v, str) else v)

    # Exact columns from your file
    EXACT = {
        "type": "Type",
        "number": "Document Number",
        "date": "Posting Date",
        "cust_code": "Customer/Supplier No.",
        "cust_name": "Customer/Supplier Name",
        "salesman": "SlpName",
        "amount": "Total Amount",
        "gp": "GP",
        "item_code": "ItemCode",
        "item_desc": "Dscription",
        "qty": "Quantity",
        "rate": "Rate",
    }

    VARIANTS = {
        "type": ["Doc Type", "Document Type"],
        "number": ["Doc Num", "Document No."],
        "date": ["Document Date", "Date"],
        "cust_code": ["CustomerCode", "CardCode", "BP Code", "Customer Code"],
        "cust_name": ["Customer Name", "BP Name", "Customer"],
        "salesman": ["Sales Employee", "Salesman"],
        "amount": ["Document Total", "Total", "Amount"],
        "gp": ["Gross Profit", "G.P."],
        "item_code": ["Item Code", "Code"],
        "item_desc": ["Description", "Item Description"],
        "qty": ["Qty", "Quantity Sold"],
        "rate": ["Unit Price", "Price"],
    }

    def pick(primary, required=True):
        lc = {c.lower(): c for c in df.columns}
        p = EXACT[primary]
        if p.lower() in lc:
            return lc[p.lower()]
        for v in VARIANTS.get(primary, []):
            if v.lower() in lc:
                return lc[v.lower()]
        if required:
            raise ValueError(f"Missing required column: {primary}")
        return None

    c_type  = pick("type")
    c_num   = pick("number")
    c_date  = pick("date")
    c_code  = pick("cust_code")
    c_name  = pick("cust_name")
    c_sman  = pick("salesman", required=False)
    c_amt   = pick("amount")
    c_gp    = pick("gp", required=False)
    c_ic    = pick("item_code")
    c_idesc = pick("item_desc", required=False)
    c_qty   = pick("qty", required=False)
    c_rate  = pick("rate", required=False)

    # Parse date
    parsed_date = pd.to_datetime(df[c_date], dayfirst=True, errors="coerce")
    df["_date"] = parsed_date.dt.date

    # Clean fields
    df["_number"]        = df[c_num].astype(str).str.strip()
    df["_customer_code"] = df[c_code].astype(str).str.strip()
    df["_customer_name"] = df[c_name].astype(str).str.strip()
    df["_salesman"]      = df[c_sman].astype(str).str.strip() if c_sman in df.columns else ""
    df["_amount"]        = df[c_amt].map(_dec)
    df["_gp"]            = df[c_gp].map(_dec) if c_gp in df.columns else Decimal("0.00")
    df["_item_code"]     = df[c_ic].astype(str).str.strip()
    df["_item_desc"]     = df[c_idesc].astype(str).str.strip() if c_idesc in df.columns else ""
    df["_qty"]           = df[c_qty].map(_dec) if c_qty in df.columns else Decimal("0.00")
    df["_rate"]          = df[c_rate].map(_dec) if c_rate in df.columns else Decimal("0.00")

    valid = df[df["_date"].notna()].copy()
    t = valid[c_type].astype(str).str.lower()
    is_invoice = t.isin(["invoice", "a/r invoice", "ar invoice"])
    is_credit  = t.str.contains("credit", na=False)

    # --- Invoices
    inv_raw = valid[is_invoice & (valid["_number"] != "")]
    invoices_df = (
        inv_raw.groupby(["_number", "_date", "_customer_code", "_customer_name", "_salesman"], as_index=False)
        .agg(_document_total=("_amount", "sum"))
        .rename(columns={
            "_number":"number","_date":"date","_customer_code":"customer_code",
            "_customer_name":"customer_name","_salesman":"salesman","_document_total":"document_total"
        })
    )

    # --- Credits
    cr_raw = valid[is_credit & (valid["_number"] != "")]
    cr_raw["_amount"] = cr_raw["_amount"].abs()
    credits_df = (
        cr_raw.groupby(["_number", "_date", "_customer_code", "_customer_name", "_salesman"], as_index=False)
        .agg(_document_total=("_amount", "sum"))
        .rename(columns={
            "_number":"number","_date":"date","_customer_code":"customer_code",
            "_customer_name":"customer_name","_salesman":"salesman","_document_total":"document_total"
        })
    )

    # --- GP lines aggregated by unique key
    gp_src = valid[["_date","_customer_code","_customer_name","_salesman","_gp"]].copy()
    gp_lines_df = (
        gp_src.groupby(["_date","_customer_code","_customer_name","_salesman"], as_index=False)
        .agg(_gp_sum=("_gp", "sum"))
        .rename(columns={
            "_date":"date","_customer_code":"customer_code","_customer_name":"customer_name",
            "_salesman":"salesman","_gp_sum":"gp"
        })
    )

    # --- Item lines (credits negative)
    def signed(val, sign=-1):
        return val * sign

    inv_lines = valid[is_invoice & (valid["_number"] != "")]
    inv_lines = inv_lines.assign(
        doc_type="Invoice",
        quantity=inv_lines["_qty"],
        amount=inv_lines["_amount"],
        gp=inv_lines["_gp"]
    )

    cr_lines = valid[is_credit & (valid["_number"] != "")]
    cr_lines = cr_lines.assign(
        doc_type="Credit",
        quantity=signed(cr_lines["_qty"], -1),
        amount=signed(cr_lines["_amount"].abs(), -1),
        gp=cr_lines["_gp"]
    )

    lines_df = pd.concat([inv_lines, cr_lines], ignore_index=True, sort=False)[[
        "doc_type","_number","_date","_customer_code","_customer_name","_salesman",
        "_item_code","_item_desc","quantity","_rate","amount","gp"
    ]].rename(columns={
        "_number":"number","_date":"date","_customer_code":"customer_code","_customer_name":"customer_name",
        "_salesman":"salesman","_item_code":"item_code","_item_desc":"item_desc","_rate":"rate"
    })

    # Final numeric types
    for col in ["document_total"]: invoices_df[col] = invoices_df[col].astype(float)
    for col in ["document_total"]: credits_df[col]  = credits_df[col].astype(float)
    gp_lines_df["gp"] = gp_lines_df["gp"].astype(float)
    lines_df[["quantity","rate","amount","gp"]] = lines_df[["quantity","rate","amount","gp"]].astype(float)

    return invoices_df, credits_df, gp_lines_df, lines_df
