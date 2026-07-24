# Risk controls

The execution path checks kill-switch state, evidence readiness, regime eligibility, recommendation
expiry, minimum risk/reward, available cash, position size, duplicate symbols, stale data, and idempotency. Position size is the
smaller of risk-budget sizing and the per-trade capital cap. Strategies cannot create orders.

Configured future controls include daily realised/total loss, portfolio and sector exposure,
liquidity/spread/ATR thresholds, consecutive losses, cooldown, duplicate symbols, and correlation
warnings. Until implemented, they must not be presented as passing checks.
