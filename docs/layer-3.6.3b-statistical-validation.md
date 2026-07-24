# Layer 3.6.3B — Statistical Validation

Layer 3.6.3B evaluates completed offline prediction outputs produced by Layer 3.6.2 and structurally validated by Layer 3.6.3A.

It does not perform inference. It does not load models, access current market data, access unknown targets, serve predictions, detect drift, detect anomalies, classify regimes, generate explanations, create recommendations, or create orders.

## Deterministic checks

- Probability values must be finite, non-negative, bounded by one, and sum to one within `1e-9`.
- Class labels must be unique and aligned with the probability vector.
- Classification margin is top probability minus second probability.
- Entropy is Shannon entropy using the natural logarithm; normalized entropy divides by `log(class_count)`.
- Zero-probability terms contribute zero to entropy.
- Thresholds and tolerances are policy-controlled and are never accepted from callers.
- Calibration evidence must be historical, immutable, checksummed, and sufficiently supported.
- Regression evidence records bounds, residuals, intervals, and uncertainty metadata without fitting a model.

## Persistence and lineage

Statistical requests depend on a validated Layer 3.6.3A request. Statistical evidence, results, manifests, events, calibration evidence, regression evidence, reference-distribution evidence, and lifecycle corrections are immutable records. Corrections use new invalidation or supersession records and never update completed results.

## API boundary

Administrative request and execute endpoints require authentication. Read endpoints expose statistical requests, results, manifests, events, and lifecycle history. No public prediction or trading endpoint is provided.

## Explicit exclusions

This layer does not implement OOD detection, anomaly detection, feature or concept drift, market-regime validation, calibration-model training, automatic recalibration, threshold optimization, deployment, serving, recommendations, BUY/SELL/HOLD signals, paper trading, or live trading.

`LIVE_TRADING_ENABLED=false` remains required.
