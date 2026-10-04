import pandas as pd
import numpy as np

REQUIRED = [
    "date", "voucher_type", "voucher_number", "party",
    "ledger", "amount", "direction", "narration", "payment_mode"
]

ALIASES = {
    "date": ["date", "voucher_date", "transaction_date"],
    "voucher_type": ["voucher_type", "vouchertypename", "type"],
    "voucher_number": ["voucher_number", "vouchernumber", "voucher_no"],
    "party": ["party", "party_name", "partyname"],
    "ledger": ["ledger", "ledger_name", "ledgername"],
    "amount": ["amount", "value", "transaction_amount"],
    "direction": ["direction", "dr_cr", "debit_credit"],
    "narration": ["narration", "description", "remarks"],
    "payment_mode": ["payment_mode", "mode", "instrument"],
}

def _pick(df, names):
    cols = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in cols:
            return cols[n.lower()]
    return None

def normalize_dataframe(data):
    df = data.copy()
    out = pd.DataFrame(index=df.index)

    for target, names in ALIASES.items():
        col = _pick(df, names)
        out[target] = df[col] if col else np.nan

    out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True)
    out["amount"] = pd.to_numeric(
        out["amount"].astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False),
        errors="coerce"
    ).abs()

    out["direction"] = out["direction"].fillna("").astype(str).str.upper().str.strip()
    out.loc[out["direction"].isin(["DR", "DEBIT", "PAYMENT", "OUT"]), "direction"] = "PAYMENT"
    out.loc[out["direction"].isin(["CR", "CREDIT", "RECEIPT", "IN"]), "direction"] = "RECEIPT"

    signed_col = _pick(df, ["signed_amount", "net_amount"])
    if signed_col:
        signed = pd.to_numeric(df[signed_col], errors="coerce")
        missing = out["direction"].isin(["", "NAN"])
        out.loc[missing & signed.notna(), "direction"] = np.where(
            signed[missing & signed.notna()] < 0, "PAYMENT", "RECEIPT"
        )

    for c in ["voucher_type", "voucher_number", "party", "ledger", "narration", "payment_mode"]:
        out[c] = out[c].fillna("").astype(str).str.strip()

    out["payment_mode"] = out["payment_mode"].str.upper()
    out["party_key"] = out["party"].str.upper().str.replace(r"\s+", " ", regex=True)

    return out[REQUIRED + ["party_key"]]
