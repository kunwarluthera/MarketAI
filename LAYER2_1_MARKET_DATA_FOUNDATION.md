# Layer 2.1 — Market Data Foundation

Layer 2.1 is an isolated, read-only intelligence foundation. It does not alter Layer 1 execution tables or trading behaviour. `intelligence_instruments` provides stable IDs and lifecycle history; `intelligence_candles` stores validated OHLCV bars with provider, session, source timestamps, freshness and deterministic revisions. Candles are range-partitioned monthly by `started_at`; the default partition supports local development before scheduled partitions are created.

## Ingestion contract

`validate_candle` rejects invalid ranges, future source timestamps, non-positive prices, inconsistent OHLC, negative counts and incomplete closed bars. A duplicate identity `(instrument_id, interval, started_at, source)` is idempotent. A corrected payload increments `revision` and updates validation status without changing the identity. Invalid records remain auditable with `validation_errors`.

## Lifecycle and calendar

Instrument rows are never cascade-deleted. Symbol/token changes create a new validity interval while preserving the stable internal ID lineage. Trading sessions record holidays, half sessions and open/close boundaries.

## APIs

Authenticated GET endpoints under `/api/v2/intelligence`: `instruments`, `candles?instrument_id=...`, `sessions`, `freshness`, and `providers`. Responses expose raw observations and quality metadata only; no indicators, regime, recommendations or ML output are present.

## Verification plan

Unit/property tests cover validation and freshness; database tests cover duplicate/revision behaviour, constraints and partition routing; API contract tests cover all read endpoints; Layer 1 regression tests must remain green. Apply migrations from zero before closure and record the complete test output.

Deferred: tick ingestion, technical indicators, news, regime detection, ML, LLMs, agents and opportunity discovery.
