# AI Forensic Auditor – Made by CA Ankit Gupta

Generic audit-assistance and forensic accounting engine.

**Data policy:** No client-specific values from the reference Tally XML are embedded in this project. Sample data is synthetic only.

Run:
```bash
pip install -r requirements.txt
streamlit run app.py
```

Architecture:
- `src/tally_parser.py` – generic Tally XML extraction
- `src/normalizer.py` – common transaction schema
- `src/rules.py` – configurable FY thresholds
- `src/forensic_engine.py` – deterministic audit tests
- `src/reporting.py` – Excel working paper
- `app.py` – Streamlit interface

Findings are review points, not final tax conclusions. Final 3CA/3CB/3CD reporting requires CA review and supporting evidence.
