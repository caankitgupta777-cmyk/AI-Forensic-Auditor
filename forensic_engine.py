import re
import pandas as pd
from rules import get_rules

def _is_cash(row):
    mode = str(row["payment_mode"]).upper()
    text = f"{row['ledger']} {row['narration']} {mode}".upper()
    return any(x in text for x in ["CASH", "BY CASH", "CASH PAYMENT", "CASH RECEIPT"])

def _risk(points):
    if points >= 81:
        return "CRITICAL"
    if points >= 61:
        return "HIGH"
    if points >= 41:
        return "REVIEW"
    if points >= 21:
        return "MONITOR"
    return "LOW"

def _finding(rule, severity, row, amount, description, action, clause, score):
    return {
        "rule_id": rule,
        "severity": severity,
        "risk_score": score,
        "date": row.get("date"),
        "voucher_type": row.get("voucher_type"),
        "voucher_number": row.get("voucher_number"),
        "party": row.get("party"),
        "ledger": row.get("ledger"),
        "amount": float(amount or 0),
        "description": description,
        "evidence_required": action,
        "3cd_area": clause,
    }

def run_forensic_audit(df, fy):
    r = get_rules(fy)
    findings = []

    work = df.copy()
    work["is_cash"] = work.apply(_is_cash, axis=1)

    # 40A(3): group by date + party because aggregate payment to one person in a day matters.
    pay = work[(work["direction"] == "PAYMENT") & work["is_cash"]].copy()
    if not pay.empty:
        grouped = pay.groupby(["date", "party_key"], dropna=False)
        for (dt, party), g in grouped:
            total = g["amount"].sum()
            if total > r.cash_payment_threshold:
                first = g.iloc[0]
                findings.append(_finding(
                    "40A3-CASH", "HIGH", first, total,
                    "Potential cash expenditure exceeding the applicable daily threshold to one payee.",
                    "Obtain invoice, payment proof, payee identity and evaluate Rule 6DD exceptions.",
                    "Clause 21 / 40A(3)", 70
                ))

    # 269ST: aggregate cash receipt from same person on same day.
    rec = work[(work["direction"] == "RECEIPT") & work["is_cash"]].copy()
    if not rec.empty:
        grouped = rec.groupby(["date", "party_key"], dropna=False)
        for (dt, party), g in grouped:
            total = g["amount"].sum()
            if total >= r.cash_receipt_threshold:
                first = g.iloc[0]
                findings.append(_finding(
                    "269ST-CASH", "CRITICAL", first, total,
                    "Potential receipt covered by the cash-receipt restriction threshold.",
                    "Establish nature of receipt, transaction/event linkage and statutory exceptions.",
                    "Clause 31 / 269ST", 90
                ))

    # 269SS: loan/deposit-like receipts.
    loan_words = r"\b(LOAN|DEPOSIT|BORROW|ADVANCE FROM)\b"
    for _, row in rec.iterrows():
        text = f"{row['ledger']} {row['narration']}".upper()
        if re.search(loan_words, text) and row["amount"] >= r.loan_deposit_threshold:
            findings.append(_finding(
                "269SS-CASH", "HIGH", row, row["amount"],
                "Cash receipt appears loan/deposit-like and reaches the statutory threshold.",
                "Verify legal nature, account-payee banking trail, exceptions and supporting agreements.",
                "Clause 31 / 269SS", 75
            ))

    # 269T: loan/deposit repayment-like cash payments.
    repay_words = r"\b(REPAY|REPAYMENT|LOAN RETURN|DEPOSIT RETURN)\b"
    for _, row in pay.iterrows():
        text = f"{row['ledger']} {row['narration']}".upper()
        if re.search(repay_words, text) and row["amount"] >= r.loan_repayment_threshold:
            findings.append(_finding(
                "269T-CASH", "HIGH", row, row["amount"],
                "Cash payment appears to be repayment of a loan/deposit and reaches the statutory threshold.",
                "Verify nature, lender/depositor, banking mode and statutory exceptions.",
                "Clause 31 / 269T", 75
            ))

    # Threshold splitting: exact or near-threshold cash payments.
    for _, row in pay.iterrows():
        amt = row["amount"]
        if abs(amt - r.cash_payment_threshold) < 0.01:
            findings.append(_finding(
                "THRESHOLD-EXACT", "REVIEW", row, amt,
                "Exact threshold cash payment detected; review for artificial splitting.",
                "Review preceding/following transactions, same payee/day, invoice sequence and business rationale.",
                "Forensic working paper", 55
            ))
        elif r.cash_payment_threshold * 0.85 <= amt < r.cash_payment_threshold:
            findings.append(_finding(
                "THRESHOLD-NEAR", "MONITOR", row, amt,
                "Cash payment is close to the statutory threshold.",
                "Check whether related invoices/payments were split across vouchers or dates.",
                "Forensic working paper", 30
            ))

    # Year-end entries.
    if not work.empty:
        year_end = work[
            (work["date"].dt.month == 3) &
            (work["date"].dt.day >= 25)
        ]
        for _, row in year_end.iterrows():
            if row["amount"] >= 100000:
                findings.append(_finding(
                    "YEAR-END", "REVIEW", row, row["amount"],
                    "Material transaction posted in the final seven days of the financial year.",
                    "Check cut-off, invoice date, delivery/service evidence, subsequent reversal and authorization.",
                    "Forensic working paper", 50
                ))

    # TDS-sensitive keywords.
    tds_words = r"\b(CONTRACT|LABOUR|PROFESSIONAL|CONSULTANCY|COMMISSION|RENT|INTEREST|SUBCONTRACT)\b"
    for _, row in work.iterrows():
        text = f"{row['ledger']} {row['narration']}".upper()
        if re.search(tds_words, text) and row["amount"] > 0:
            findings.append(_finding(
                "TDS-RISK", "REVIEW", row, row["amount"],
                "Ledger/narration indicates an expense nature that may require TDS review.",
                "Check payee status, PAN, applicable section, threshold, deduction, deposit and return reporting.",
                "Clause 34 / TDS", 45
            ))

    # Partner/capital indicators.
    related_words = r"\b(PARTNER|CAPITAL|DRAWING|DRAWINGS|PARTNER INTEREST|PARTNER SALARY)\b"
    for _, row in work.iterrows():
        text = f"{row['ledger']} {row['narration']}".upper()
        if re.search(related_words, text):
            findings.append(_finding(
                "PARTNER-RELATED", "REVIEW", row, row["amount"],
                "Partner/capital-related transaction identified for tax and disclosure review.",
                "Verify partnership deed, section 40(b) limits, authorization and disclosure requirements.",
                "Clause 21 / 34 / related disclosures", 45
            ))

    # Round-number forensic indicator.
    for _, row in work.iterrows():
        if row["amount"] >= 50000 and float(row["amount"]) % 10000 == 0:
            findings.append(_finding(
                "ROUND-AMOUNT", "MONITOR", row, row["amount"],
                "Material round-number transaction identified as a forensic review indicator.",
                "Inspect invoice/supporting document and compare with normal transaction patterns.",
                "Forensic working paper", 25
            ))

    findings.sort(key=lambda x: (x["risk_score"], x["amount"]), reverse=True)

    clause_map = []
    for clause in sorted(set(f["3cd_area"] for f in findings)):
        related = [f for f in findings if f["3cd_area"] == clause]
        clause_map.append({
            "3CD area": clause,
            "finding_count": len(related),
            "highest_risk": max(f["risk_score"] for f in related),
            "status": "REVIEW REQUIRED"
        })

    high_critical = sum(1 for f in findings if f["severity"] in ("HIGH", "CRITICAL"))
    potential_amount = sum(f["amount"] for f in findings if f["severity"] in ("HIGH", "CRITICAL"))

    return {
        "findings": findings,
        "clause_map": clause_map,
        "high_critical_count": high_critical,
        "potential_amount": potential_amount,
    }
