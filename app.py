import io
import pandas as pd
import streamlit as st

from tally_parser import parse_tally_xml
from normalizer import normalize_dataframe
from forensic_engine import run_forensic_audit
from reporting import build_excel_report

st.set_page_config(page_title="AI Forensic Auditor", layout="wide")

def make_12_point_report(df, result):
    findings = result.get("findings", [])
    def f(rule): return [x for x in findings if x.get("rule_id") == rule]
    def amt(xs): return sum(float(x.get("amount") or 0) for x in xs)

    critical = [x for x in findings if x["severity"] == "CRITICAL"]
    high = [x for x in findings if x["severity"] == "HIGH"]
    review = [x for x in findings if x["severity"] == "REVIEW"]
    monitor = [x for x in findings if x["severity"] == "MONITOR"]

    risk = ("CRITICAL" if critical else "HIGH" if high else
            "REVIEW" if review else "MONITOR" if monitor else
            "NO RULE-BASED EXCEPTION")

    cash, r269st = f("40A3-CASH"), f("269ST-CASH")
    r269ss, r269t = f("269SS-CASH"), f("269T-CASH")
    split = [x for x in findings if x["rule_id"] in ("THRESHOLD-EXACT","THRESHOLD-NEAR")]
    tds, partner = f("TDS-RISK"), f("PARTNER-RELATED")
    yearend, roundamt = f("YEAR-END"), f("ROUND-AMOUNT")

    return [
        {"No":"01","Section":"Executive Summary",
         "Conclusion":f"Overall rule-based risk: {risk}. {len(findings):,} findings from {len(df):,} transaction rows.",
         "Key Metrics":f"Critical {len(critical)} | High {len(high)} | Review {len(review)} | Monitor {len(monitor)} | High/Critical amount ₹{amt(high+critical):,.2f}",
         "Recommended Action":"Prioritise Critical/High items. Final tax conclusions require CA review."},
        {"No":"02","Section":"Cash Expenditure – Section 40A(3)",
         "Conclusion":f"{len(cash)} potential cash expenditure exception(s).",
         "Key Metrics":f"Potential amount ₹{amt(cash):,.2f}",
         "Recommended Action":"Verify payee/day aggregation, payment mode and Rule 6DD exceptions."},
        {"No":"03","Section":"Cash Receipts – Section 269ST",
         "Conclusion":f"{len(r269st)} potential 269ST receipt exception(s).",
         "Key Metrics":f"Potential amount ₹{amt(r269st):,.2f}",
         "Recommended Action":"Verify person, date, transaction/event and statutory exceptions."},
        {"No":"04","Section":"Loans / Deposits – Sections 269SS & 269T",
         "Conclusion":f"269SS indicators: {len(r269ss)}; 269T indicators: {len(r269t)}.",
         "Key Metrics":f"269SS ₹{amt(r269ss):,.2f} | 269T ₹{amt(r269t):,.2f}",
         "Recommended Action":"Verify legal nature, parties, agreements, banking trail and exceptions."},
        {"No":"05","Section":"Threshold Splitting & Structuring",
         "Conclusion":f"{len(split)} exact/near-threshold indicators.",
         "Key Metrics":f"Exact {sum(x['rule_id']=='THRESHOLD-EXACT' for x in split)} | Near {sum(x['rule_id']=='THRESHOLD-NEAR' for x in split)}",
         "Recommended Action":"Compare adjacent vouchers, invoice sequences and repeated payees."},
        {"No":"06","Section":"TDS / Withholding Tax Risk",
         "Conclusion":f"{len(tds)} TDS-sensitive expense indicators.",
         "Key Metrics":f"Indicative amount ₹{amt(tds):,.2f}",
         "Recommended Action":"Verify section, threshold, PAN, deduction/deposit and return reporting."},
        {"No":"07","Section":"Partner / Related-Party Review",
         "Conclusion":f"{len(partner)} partner/capital-related indicators.",
         "Key Metrics":f"Indicative amount ₹{amt(partner):,.2f}",
         "Recommended Action":"Verify deed, section 40(b), remuneration, interest, drawings and capital."},
        {"No":"08","Section":"Statutory Payments & Rule 6DD",
         "Conclusion":"Statutory-payment patterns require documentary review; no automatic Rule 6DD conclusion.",
         "Key Metrics":"Evidence-led review",
         "Recommended Action":"Verify Government/statutory nature and retain payment proof."},
        {"No":"09","Section":"Journal & Year-End Forensics",
         "Conclusion":f"{len(yearend)} year-end and {len(roundamt)} material round-number indicators.",
         "Key Metrics":f"Year-end ₹{amt(yearend):,.2f} | Round-number ₹{amt(roundamt):,.2f}",
         "Recommended Action":"Check cut-off, invoices, authorization, reversals and subsequent events."},
        {"No":"10","Section":"Capital Expenditure & Depreciation",
         "Conclusion":"Capital/depreciation conclusions require fixed-asset-register and put-to-use evidence.",
         "Key Metrics":"Evidence-led review",
         "Recommended Action":"Reconcile additions, capitalization dates, asset class, rate and put-to-use date."},
        {"No":"11","Section":"Forensic Risk & Priority Matrix",
         "Conclusion":f"Critical {len(critical)}, High {len(high)}, Review {len(review)}, Monitor {len(monitor)}.",
         "Key Metrics":"0–20 Low | 21–40 Monitor | 41–60 Review | 61–80 High | 81–100 Critical",
         "Recommended Action":"Investigate in risk order and record auditor disposition."},
        {"No":"12","Section":"3CD Working-Paper & Evidence Plan",
         "Conclusion":f"{len(result.get('clause_map', []))} 3CD areas have rule-based findings/indicators.",
         "Key Metrics":"Working-paper aid only",
         "Recommended Action":"Complete clause-wise verification and evidence before final 3CA/3CB/3CD reporting."},
    ]

st.title("AI Forensic Auditor")
st.caption("Made by CA Ankit Gupta")
st.info("Client data is analysed dynamically. No client-specific transaction values are embedded in this application.")

fy = st.selectbox("Financial Year",
    ["2018-19","2019-20","2020-21","2021-22","2022-23","2023-24","2024-25","2025-26","2026-27"])
audit_type = st.selectbox("Audit / reporting basis",
    ["Tax audit – Form 3CB + 3CD","Tax audit – Form 3CA + 3CD","Forensic review only"])
uploaded = st.file_uploader("Upload accounting data", type=["xml","csv","xlsx"])

if uploaded:
    try:
        if uploaded.name.lower().endswith(".xml"):
            raw = parse_tally_xml(uploaded.getvalue())
        elif uploaded.name.lower().endswith(".csv"):
            raw = pd.read_csv(io.BytesIO(uploaded.getvalue()))
        else:
            raw = pd.read_excel(io.BytesIO(uploaded.getvalue()))

        df = normalize_dataframe(raw)
        st.subheader("Normalized transactions")
        st.dataframe(df.head(100), use_container_width=True)

        if st.button("Run Forensic Audit", type="primary"):
            result = run_forensic_audit(df, fy)
            report12 = make_12_point_report(df, result)

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Transactions tested", len(df))
            c2.metric("Findings", len(result["findings"]))
            c3.metric("High / Critical", result["high_critical_count"])
            c4.metric("Potential amount", f"₹{result['potential_amount']:,.2f}")

            st.subheader("12-Point Forensic Audit Report")
            st.markdown(f"### Overall Risk: **{report12[0]['Conclusion'].split('risk: ')[-1].split('.')[0]}**")
            st.dataframe(pd.DataFrame(report12), use_container_width=True)

            st.subheader("Priority Findings")
            if result["findings"]:
                priority = sorted(result["findings"], key=lambda x:(x["risk_score"],x["amount"]), reverse=True)[:30]
                st.dataframe(pd.DataFrame(priority), use_container_width=True)
            else:
                st.success("No rule-based exception was detected. This is not a substitute for professional audit procedures.")

            with st.expander("3CD Working-Paper Map"):
                st.dataframe(pd.DataFrame(result["clause_map"]), use_container_width=True)

            report = build_excel_report(df, result, fy, audit_type)
            st.download_button(
                "Download Excel Working Paper",
                data=report,
                file_name="AI_Forensic_Auditor_12_Point_Working_Paper.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as exc:
        st.error(f"Unable to process the uploaded file: {exc}")
else:
    st.markdown("""
### 12-point audit analysis
1. Executive Summary
2. 40A(3) Cash Expenditure
3. 269ST Cash Receipts
4. 269SS / 269T Loans & Deposits
5. Threshold Splitting
6. TDS Risk
7. Partner / Related Party
8. Statutory Payments / Rule 6DD
9. Journal & Year-End Forensics
10. Capital Expenditure / Depreciation
11. Forensic Risk Matrix
12. 3CD Working-Paper & Evidence Plan
""")
