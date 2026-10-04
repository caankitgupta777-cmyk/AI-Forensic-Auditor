from io import BytesIO
import pandas as pd

def build_excel_report(df, result, fy, audit_type):
    output = BytesIO()
    findings = pd.DataFrame(result["findings"])
    clauses = pd.DataFrame(result["clause_map"])

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([{
            "Financial Year": fy,
            "Audit Type": audit_type,
            "Transactions Tested": len(df),
            "Findings": len(findings),
            "High/Critical Findings": result["high_critical_count"],
            "Potential Amount Flagged": result["potential_amount"],
            "Note": "Draft working paper only – professional review required."
        }]).to_excel(writer, sheet_name="Summary", index=False)

        findings.to_excel(writer, sheet_name="Forensic Findings", index=False)
        clauses.to_excel(writer, sheet_name="3CD Clause Map", index=False)
        df.to_excel(writer, sheet_name="Normalized Data", index=False)

        evidence = pd.DataFrame([
            {
                "Finding Type": r["rule_id"],
                "Evidence / verification required": r["evidence_required"],
                "Final conclusion": "To be determined by auditor after verification"
            }
            for r in result["findings"]
        ])
        evidence.to_excel(writer, sheet_name="Evidence Checklist", index=False)

    return output.getvalue()
