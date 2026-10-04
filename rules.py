from dataclasses import dataclass

@dataclass(frozen=True)
class RuleProfile:
    cash_payment_threshold: float = 10000.0
    goods_carriage_threshold: float = 35000.0
    loan_deposit_threshold: float = 20000.0
    loan_repayment_threshold: float = 20000.0
    cash_receipt_threshold: float = 200000.0

# Keep thresholds configurable. Do not embed client data here.
# Validate each FY profile against the law applicable to that assessment year
# before production filing/reporting.
RULE_PROFILES = {
    "2018-19": RuleProfile(),
    "2019-20": RuleProfile(),
    "2020-21": RuleProfile(),
    "2021-22": RuleProfile(),
    "2022-23": RuleProfile(),
    "2023-24": RuleProfile(),
    "2024-25": RuleProfile(),
    "2025-26": RuleProfile(),
    "2026-27": RuleProfile(),
}

def get_rules(fy):
    return RULE_PROFILES[fy]
