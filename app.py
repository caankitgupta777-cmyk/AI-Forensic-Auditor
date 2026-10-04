import io
import pandas as pd
import streamlit as st

from src.tally_parser import parse_tally_xml
from src.normalizer import normalize_dataframe
from src.forensic_engine import run_forensic_audit
from src.reporting import build_excel_report

st.set_page_config(page_title="AI Forensic Auditor", layout="wide")

st.title("AI Forensic Auditor")
st.caption("Made by CA Ankit Gupta")
st.info("Client data is analysed dynamically. This software contains no client-specific transaction values.")

fy = st.selectbox(
    "Financial Year",
    ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24",
     "2024-25", "2025-26", "2026-27"],
    index=0,
)

audit_type = st.selectbox(
    "Audit / reporting basis",
    ["Tax audit – Form 3CB + 3CD", "Tax audit – Form 3CA + 3CD",
     "Forensic review only"]
)

uploaded = st.file_uploader("Upload accounting data", type=["xml", "csv", "xlsx"])

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

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Transactions tested", len(df))
            c2.metric("Findings", len(result["findings"]))
            c3.metric("High / Critical", int(result["high_critical_count"]))
            c4.metric("Potential amount flagged", f"₹{result['potential_amount']:,.2f}")

            st.subheader("Findings")
            if result["findings"]:
                findings_df = pd.DataFrame(result["findings"])
                st.dataframe(findings_df, use_container_width=True)
            else:
                st.success("No rule-based exception was detected. This is not a substitute for professional audit procedures.")

            st.subheader("3CD working-paper map")
            st.dataframe(pd.DataFrame(result["clause_map"]), use_container_width=True)

            report = build_excel_report(df, result, fy, audit_type)
            st.download_button(
                "Download Excel Working Paper",
                data=report,
                file_name="AI_Forensic_Auditor_Working_Paper.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as exc:
        st.error(f"Unable to process the uploaded file: {exc}")
else:
    st.markdown("""
### What this engine checks

**Cash / payment tests**
- 40A(3) potential cash-payment exceptions
- 40A(3A) potential unpaid/converted liabilities
- Rule 6DD review indicators
- 269SS loan/deposit indicators
- 269T repayment indicators
- 269ST receipt indicators
- threshold-splitting patterns

**Forensic tests**
- repeated exact-threshold payments
- near-threshold payments
- year-end unusual entries
- round-number transactions
- reversals
- suspicious narration
- negative cash indicators
- partner/capital indicators
- TDS-sensitive expense indicators

Every finding is labelled as a **review point / potential issue**, not a final tax conclusion.
""")
