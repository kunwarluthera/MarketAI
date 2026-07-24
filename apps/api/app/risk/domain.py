from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class RuleResult:
    rule_name: str
    threshold: str
    observed: str
    passed: bool
    reason_code: str


def evaluate(
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    cash: Decimal,
    kill_switch: bool,
    existing_position: bool,
    stale: bool = False,
) -> tuple[int, list[RuleResult]]:
    risk_reward = (target - entry) / (entry - stop) if entry > stop else Decimal(0)
    rules = [
        RuleResult(
            "global_kill_switch",
            "false",
            str(kill_switch).lower(),
            not kill_switch,
            "KILL_SWITCH_ACTIVE",
        ),
        RuleResult(
            "data_freshness", "fresh", "stale" if stale else "fresh", not stale, "DATA_STALE"
        ),
        RuleResult(
            "minimum_risk_reward",
            "1.5",
            str(risk_reward),
            risk_reward >= Decimal("1.5"),
            "RISK_REWARD_TOO_LOW",
        ),
        RuleResult(
            "duplicate_symbol",
            "false",
            str(existing_position).lower(),
            not existing_position,
            "DUPLICATE_POSITION",
        ),
    ]
    per_share = entry - stop
    qty = (
        int(
            min(
                cash * Decimal("0.005") / per_share, cash * Decimal("0.10") / entry
            ).to_integral_value(rounding=ROUND_DOWN)
        )
        if per_share > 0
        else 0
    )
    rules.append(RuleResult("position_size", ">0", str(qty), qty > 0, "INSUFFICIENT_CASH"))
    return qty, rules
