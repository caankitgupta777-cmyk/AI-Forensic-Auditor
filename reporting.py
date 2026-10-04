from io import BytesIO
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

def build_12_point_report(df, result, fy, audit_type):
    fs = result.get("findings", [])
    def rows(rule): return [x for x in fs if x.get("rule_id")==rule]
    def amt(xs): return sum(float(x.get("amount") or 0) for x in xs)
    critical=[x for x in fs if x["severity"]=="CRITICAL"]
    high=[x for x in fs if x["severity"]=="HIGH"]
    review=[x for x in fs if x["severity"]=="REVIEW"]
    monitor=[x for x in fs if x["severity"]=="MONITOR"]
    if critical: risk="CRITICAL"
    elif high: risk="HIGH"
    elif review: risk="REVIEW"
    elif monitor: risk="MONITOR"
    else: risk="NO RULE-BASED EXCEPTION"
    cash=rows("40A3-CASH"); r269st=rows("269ST-CASH"); r269ss=rows("269SS-CASH")
    r269t=rows("269T-CASH"); split=[x for x in fs if x["rule_id"] in ("THRESHOLD-EXACT","THRESHOLD-NEAR")]
    tds=rows("TDS-RISK"); partner=rows("PARTNER-RELATED"); yearend=rows("YEAR-END"); roundamt=rows("ROUND-AMOUNT")
    sections=[
      ("01","Executive Summary",f"Overall rule-based risk is {risk}. {len(fs):,} findings were generated from {len(df):,} normalized transaction rows.",f"Critical {len(critical)} | High {len(high)} | Review {len(review)} | Monitor {len(monitor)} | High/Critical amount ₹{amt(high+critical):,.2f}","Prioritise Critical/High items; no automated finding is a final tax conclusion."),
      ("02","Cash Expenditure – Section 40A(3)",f"{len(cash)} potential cash expenditure exception(s) detected.",f"Potential amount ₹{amt(cash):,.2f}","Verify payee/day aggregation, payment mode, business purpose and Rule 6DD exceptions."),
      ("03","Cash Receipts – Section 269ST",f"{len(r269st)} potential 269ST receipt exception(s) detected.",f"Potential amount ₹{amt(r269st):,.2f}","Verify person, date, transaction/event and statutory exceptions."),
      ("04","Loans / Deposits – Sections 269SS & 269T",f"269SS indicators: {len(r269ss)}; 269T indicators: {len(r269t)}.",f"269SS ₹{amt(r269ss):,.2f} | 269T ₹{amt(r269t):,.2f}","Verify legal nature, parties, agreements, banking trail and exceptions."),
      ("05","Threshold Splitting & Structuring",f"{len(split)} exact/near-threshold indicator(s) detected.",f"Exact {sum(x['rule_id']=='THRESHOLD-EXACT' for x in split)} | Near {sum(x['rule_id']=='THRESHOLD-NEAR' for x in split)}","Compare adjacent vouchers, invoice sequences, same-day transactions and repeated payees."),
      ("06","TDS / Withholding Tax Risk",f"{len(tds)} TDS-sensitive expense indicator(s) detected.",f"Indicative amount ₹{amt(tds):,.2f}","Verify section, threshold, PAN, deduction/deposit dates and return reporting."),
      ("07","Partner / Related-Party Review",f"{len(partner)} partner/capital-related indicator(s) detected.",f"Indicative amount ₹{amt(partner):,.2f}","Verify deed, section 40(b), remuneration, interest, drawings and capital movements."),
      ("08","Statutory Payments & Rule 6DD", "Statutory-payment patterns require documentary review; the engine does not automatically approve Rule 6DD.", "Evidence-led review","Verify Government/statutory nature and retain payment proof."),
      ("09","Journal & Year-End Forensics",f"{len(yearend)} year-end and {len(roundamt)} material round-number indicator(s) detected.",f"Year-end ₹{amt(yearend):,.2f} | Round-number ₹{amt(roundamt):,.2f}","Check cut-off, invoices, authorization, reversals and subsequent events."),
      ("10","Capital Expenditure & Depreciation", "Capital/depreciation conclusions require fixed-asset-register and put-to-use evidence.", "Evidence-led review","Reconcile additions, capitalization dates, asset class, rate and put-to-use date."),
      ("11","Forensic Risk & Priority Matrix",f"Critical {len(critical)}, High {len(high)}, Review {len(review)}, Monitor {len(monitor)}.","0–20 Low | 21–40 Monitor | 41–60 Review | 61–80 High | 81–100 Critical","Investigate in risk order and record auditor disposition."),
      ("12","3CD Working-Paper & Evidence Plan",f"{len(result.get('clause_map',[]))} 3CD areas have rule-based findings/indicators.","Working-paper aid only","Complete clause-wise verification and evidence before final 3CA/3CB/3CD reporting.")
    ]
    top=[]
    for x in sorted(fs,key=lambda z:(z["risk_score"],z["amount"]),reverse=True)[:30]:
        top.append({"Date":x["date"],"Voucher":x["voucher_number"],"Party":x["party"],"Ledger":x["ledger"],"Amount":x["amount"],"Risk":x["severity"],"Rule":x["rule_id"],"Finding":x["description"],"Evidence Required":x["evidence_required"]})
    return {"overall_risk":risk,"sections":sections,"top_findings":top}

def build_excel_report(df,result,fy,audit_type):
    r=build_12_point_report(df,result,fy,audit_type)
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        pd.DataFrame([{"Financial Year":fy,"Audit Type":audit_type,"Overall Risk":r["overall_risk"],"Transactions Tested":len(df),"Findings":len(result["findings"]),"Potential High/Critical Amount":result["potential_amount"]}]).to_excel(w,sheet_name="Executive Summary",index=False)
        pd.DataFrame(r["sections"],columns=["No","Section","Conclusion","Key Metrics","Recommended Action"]).to_excel(w,sheet_name="12 Point Report",index=False)
        pd.DataFrame(r["top_findings"]).to_excel(w,sheet_name="Priority Findings",index=False)
        pd.DataFrame(result["findings"]).to_excel(w,sheet_name="All Findings",index=False)
        pd.DataFrame(result["clause_map"]).to_excel(w,sheet_name="3CD Clause Map",index=False)
        df.to_excel(w,sheet_name="Normalized Data",index=False)
        pd.DataFrame([{"Rule":x["rule_id"],"Party":x["party"],"Amount":x["amount"],"Evidence Required":x["evidence_required"],"Auditor Disposition":"Pending review"} for x in result["findings"]]).to_excel(w,sheet_name="Evidence Checklist",index=False)
        for ws in w.book.worksheets:
            for c in ws[1]: c.font=Font(bold=True)
            ws.freeze_panes="A2"
            for col in ws.columns:
                ws.column_dimensions[get_column_letter(col[0].column)].width=min(max(len(str(c.value or "")) for c in col)+2,60)
    return out.getvalue()
