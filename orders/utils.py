def read_simple_lines(uploaded_file):
    import pandas as pd
    from decimal import Decimal, InvalidOperation
    import re

    def _dec(x):
        if x is None:
            return Decimal("0")
        s = str(x).strip()
        # (123.45) -> -123.45
        paren = s.startswith("(") and s.endswith(")")
        if paren:
            s = s[1:-1].strip()
        s = s.replace("−", "-")                # unicode minus
        s = re.sub(r"[,\s]", "", s)            # commas / spaces
        if s in ("", "-"):
            val = Decimal("0")
        else:
            try:
                val = Decimal(s)
            except InvalidOperation:
                val = Decimal("0")
        return -val if paren and val >= 0 else val

    def _parse_dates(series):
        s = series.astype(str).str.strip()
        dt = pd.to_datetime(s, format="%d.%m.%Y", errors="coerce")
        dt = dt.fillna(pd.to_datetime(s, format="%d.%m.%y",  errors="coerce"))
        dt = dt.fillna(pd.to_datetime(s, format="%Y-%m-%d",  errors="coerce"))
        dt = dt.fillna(pd.to_datetime(s, format="%d/%m/%Y",  errors="coerce"))
        dt = dt.fillna(pd.to_datetime(s, format="%d/%m/%y",  errors="coerce"))
        # Excel serials (e.g., 45678)
        mask_num = s.str.fullmatch(r"\d+(\.\d+)?")
        if mask_num.any():
            dt_num = pd.to_datetime(s[mask_num].astype(float), unit="D", origin="1899-12-30", errors="coerce")
            dt.loc[mask_num] = dt_num
        return dt.dt.date

    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=0, dtype=str, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    # modern pandas prefers DataFrame.map over applymap
    df = df.map(lambda v: v.strip() if isinstance(v, str) else v)

    col_map = {
        "doc_type_code": "DocumentTypeCode",
        "doc_type": "Document Type",
        "number": "Document Number",
        "date": "PostingDate",
        "customer_code": "Customer Code",
        "customer_name": "Customer Name",
        "salesman": "Sales Employee",
        "item_code": "ItemCode",
        "item_desc": "Item Description",
        "item_mfr": "Item Manufacturer",
        "qty": "Quantity",
        "net": "Net Sales",
        "gp": "Gross Profit",
    }
    for k, v in col_map.items():
        if v not in df.columns:
            raise ValueError(f"Missing column: {v}")

    out = pd.DataFrame({
        "doc_type_code": df[col_map["doc_type_code"]].astype(str).str.strip(),
        "doc_type":      df[col_map["doc_type"]].astype(str).str.strip(),
        "number":        df[col_map["number"]].astype(str).str.strip(),
        "date":          _parse_dates(df[col_map["date"]]),
        "customer_code": df[col_map["customer_code"]].astype(str).str.strip(),
        "customer_name": df[col_map["customer_name"]].astype(str).str.strip(),
        "salesman":      df[col_map["salesman"]].astype(str).str.strip(),
        "item_code":     df[col_map["item_code"]].astype(str).str.strip(),
        "item_desc":     df[col_map["item_desc"]].astype(str).str.strip(),
        "item_mfr":      df[col_map["item_mfr"]].astype(str).str.strip(),
        "quantity":      df[col_map["qty"]].map(_dec),     # keep Excel sign
        "net_sales":     df[col_map["net"]].map(_dec),     # keep Excel sign
        "gross_profit":  df[col_map["gp"]].map(_dec),      # keep Excel sign
    })

    # keep only rows that parsed a date successfully
    out = out[out["date"].notna()].copy()

    # keep doc_type text as-is (no sign logic)
    out["doc_type"] = out["doc_type"].fillna("")

    out["row_idx"] = range(1, len(out) + 1)
    return out
