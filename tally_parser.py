from io import BytesIO
from lxml import etree
import re
import pandas as pd

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

def _clean(value):
    if value is None:
        return ""
    return CONTROL_CHARS.sub("", str(value)).strip()

def _first_text(node, names):
    for name in names:
        found = node.find(".//" + name)
        if found is not None and found.text:
            return _clean(found.text)
    return ""

def parse_tally_xml(data: bytes) -> pd.DataFrame:
    rows = []
    context = etree.iterparse(BytesIO(data), events=("end",), tag="VOUCHER", recover=True, huge_tree=True)

    for _, voucher in context:
        date = _first_text(voucher, ["DATE"])
        vtype = _first_text(voucher, ["VOUCHERTYPENAME"])
        vno = _first_text(voucher, ["VOUCHERNUMBER"])
        party = _first_text(voucher, ["PARTYNAME"])
        narration = _first_text(voucher, ["NARRATION"])

        # Extract ledger entries. Tally XML structures differ between exports;
        # this intentionally keeps the parser generic and lets normalization handle fields.
        ledger_entries = voucher.findall(".//ALLLEDGERENTRIES.LIST")
        if not ledger_entries:
            ledger_entries = voucher.findall(".//LEDGERENTRIES.LIST")

        for entry in ledger_entries:
            ledger = _first_text(entry, ["LEDGERNAME"])
            amount_text = _first_text(entry, ["AMOUNT"])
            mode = _first_text(entry, ["BANKALLOCATIONS.LIST/TRANSACTIONTYPE"])
            if not mode:
                mode = _first_text(entry, ["BANKALLOCATIONS.LIST/INSTRUMENTNUMBER"])

            try:
                amount = float(amount_text.replace(",", "")) if amount_text else None
            except ValueError:
                amount = None

            # Preserve Tally's signed amount. ISDEEMEDPOSITIVE can be used later
            # for a stronger debit/credit interpretation.
            rows.append({
                "date": date,
                "voucher_type": vtype,
                "voucher_number": vno,
                "party": party,
                "ledger": ledger,
                "amount": abs(amount) if amount is not None else None,
                "signed_amount": amount,
                "direction": "",
                "narration": narration,
                "payment_mode": mode,
            })

        voucher.clear()
        while voucher.getprevious() is not None:
            del voucher.getparent()[0]

    return pd.DataFrame(rows)
