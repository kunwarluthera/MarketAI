# Market AI — Layer 2 Market Intelligence Platform

## Review status

Proposal only. No application code or Layer 1 behavior is changed by this document.

Layer 1 remains frozen:

- paper trading
- execution and transaction handling
- retries and savepoints
- reconciliation
- alerts and idempotency
- EOD and stop/target behavior
- `LIVE_TRADING_ENABLED=false`

## 1. Objective

Layer 2 is a reusable market-intelligence foundation. It collects, normalizes, validates, enriches, versions, stores, and exposes market facts.

Layer 2 does **not**:

- generate BUY/SELL recommendations
- place or simulate trades
- train ML models
- call LLMs
- make autonomous decisions

Future ML models, agentic systems, and strategies consume Layer 2 read APIs and persisted intelligence records rather than fetching raw sources directly.

## 2. Architectural principles

1. Facts and calculations are separate from decisions.
2. Raw source data is immutable; normalized and derived data is versioned.
3. Every derived record carries source time, calculation time, freshness, and provenance.
4. Calculations are deterministic and reproducible from stored inputs and calculation version.
5. Every pipeline stage is independently testable.
6. Read APIs are stable contracts for future Layer 3 and Layer 4 consumers.
7. Data quality is explicit, queryable, and never hidden behind a fabricated value.
8. Layer 2 has no write path into Layer 1 financial tables.

## 3. Target architecture

```text
External market sources
        |
        v
Source adapters --> Raw market store (immutable)
        |
        v
Normalization + validation + canonical timestamps
        |
        +--> Market Data Engine
        |       candles, indices, sectors, instruments, freshness
        |
        +--> Feature Store
        |       indicators, trend, momentum, volatility, S/R
        |
        +--> Breadth Engine
        |       A/D, participation, sector strength, leaders/laggards
        |
        +--> News Intelligence
        |       dedupe, sentiment, symbols, confidence, importance
        |
        +--> Regime Engine
                trending, sideways, volatile, gap, expiry, news-driven
        |
        v
Read-only Research API
        |
        +--> Layer 3 ML models
        +--> Layer 4 AI agents
        +--> Future strategies
```

Layer 2 may read market-related source data already present in the repository, but it must not call `approve_and_fill()`, `exit_position()`, or any Layer 1 execution function.

## 4. Service boundaries

### 4.1 Source Adapter Boundary

Responsible for external-provider-specific behavior:

- request and response handling
- rate limits and retries at the provider boundary
- provider symbol mapping
- provider timestamps and response metadata
- raw payload persistence

It returns a canonical adapter DTO and does not calculate indicators.

Suggested package:

```text
app/intelligence/sources/
├── base.py
├── simulated.py
├── historical.py
├── index.py
├── sector.py
└── news.py
```

### 4.2 Market Data Engine

Responsible for:

- historical OHLCV candles
- index observations
- sector observations
- instrument metadata
- canonical UTC timestamps
- market-session/calendar metadata
- validation and freshness

It publishes normalized market facts to the intelligence store.

### 4.3 Feature Store

Responsible for deterministic, versioned calculations:

- EMA
- RSI
- VWAP
- MACD
- ATR
- Bollinger Bands
- ADX
- relative volume
- volatility
- trend and momentum descriptors
- support and resistance levels

It consumes canonical candles only. It never emits a trade action.

### 4.4 Breadth Engine

Responsible for cross-sectional facts:

- advances and declines
- sector strength
- index participation
- leaders and laggards

Breadth outputs describe the market; they do not rank trade recommendations.

### 4.5 News Intelligence

Responsible for:

- source ingestion
- canonical article identity
- deduplication
- symbol/entity detection
- deterministic or versioned sentiment classification
- confidence and importance
- article freshness and expiration

If an NLP classifier is introduced later, its model version becomes part of provenance. Layer 2 still exposes facts, not recommendations.

### 4.6 Regime Engine

Responsible for descriptive market state:

- trending
- sideways
- volatile
- gap day
- expiry day
- news driven

Regime is a market fact with evidence and calculation version, not a BUY/SELL signal.

### 4.7 Research API

Read-only API boundary for all downstream consumers. It returns structured JSON and stable identifiers, timestamps, provenance, quality, and freshness.

## 5. Database schema proposal

Use a separate Layer 2 schema or table namespace (`intelligence`) so Layer 1 tables remain protected.

### Source and metadata tables

```text
intelligence_sources
- id
- provider
- source_type (market, index, sector, news)
- provider_version
- active

instruments_metadata
- instrument_id
- symbol
- exchange
- isin/provider_symbol
- sector_id
- instrument_type
- trading_calendar
- valid_from / valid_to
- source_id
- source_timestamp
- ingested_at

indices
- id
- symbol
- name
- exchange
- source_id
```

### Raw and canonical market data

```text
raw_market_payloads
- id
- source_id
- external_key
- payload_json
- source_timestamp
- ingested_at
- checksum

market_candles
- id
- instrument_id
- interval
- open/high/low/close (NUMERIC)
- volume
- started_at
- ended_at
- session_date
- is_complete
- source_id
- source_record_id
- ingested_at
- validation_status
- validation_errors_json
- checksum

index_observations
- id
- index_id
- value
- open/high/low/close
- volume, when available
- observed_at
- source_id
- freshness_seconds
- validation_status

sector_observations
- id
- sector_id
- value/change/relative_strength
- observed_at
- source_id
- freshness_seconds
- validation_status
```

### Features

```text
feature_calculation_runs
- id
- feature_set_version
- input_interval
- calculation_started_at
- calculation_completed_at
- code_version

instrument_feature_snapshots
- id
- instrument_id
- interval
- source_candle_end_at
- calculated_at
- feature_set_version
- ema_json
- rsi_json
- vwap_json
- macd_json
- atr_json
- bollinger_json
- adx_json
- volume_json
- volatility_json
- trend_json
- momentum_json
- support_resistance_json
- quality_status
- freshness_seconds
- confidence
- provenance_json

market_regime_snapshots
- id
- scope_type (market, index, sector, instrument)
- scope_id
- regime
- effective_at
- calculated_at
- source_feature_snapshot_id
- feature_set_version
- confidence
- evidence_json
- freshness_seconds
- provenance_json
```

### Breadth

```text
market_breadth_snapshots
- id
- market/session_date
- observed_at
- calculated_at
- advances
- declines
- unchanged
- advance_decline_ratio
- participation_json
- leaders_json
- laggards_json
- quality_status
- freshness_seconds
- provenance_json

sector_strength_snapshots
- id
- sector_id
- observed_at
- calculated_at
- return_periods_json
- rank
- breadth_json
- quality_status
- freshness_seconds
```

### News

```text
news_articles
- id
- canonical_url
- headline
- body_hash
- publisher
- published_at
- ingested_at
- updated_at
- language
- raw_source_id
- freshness_seconds
- dedupe_key

news_symbol_mentions
- article_id
- instrument_id
- detection_method
- confidence
- evidence_json

news_classifications
- article_id
- classifier_version
- sentiment
- sentiment_score
- importance
- classification_confidence
- classified_at
- freshness_seconds
- provenance_json
```

All tables should have unique constraints appropriate to their source identity and a validation status rather than silently accepting invalid data.

## 6. Data quality model

Every market or derived record should expose:

```json
{
  "quality_status": "valid",
  "source_timestamp": "2026-07-22T09:30:00Z",
  "calculated_at": "2026-07-22T09:30:03Z",
  "freshness_seconds": 3,
  "confidence": 0.98,
  "source_id": "provider-a",
  "calculation_version": "features-1.0.0",
  "validation_errors": []
}
```

Validation rules include:

- `high >= max(open, close, low)`
- `low <= min(open, close, high)`
- positive prices
- non-negative volume
- monotonic or explicitly corrected timestamps
- no duplicate source record
- session/calendar consistency
- completed candles are immutable
- future timestamps are rejected or quarantined

Invalid data is quarantined and reported through data-quality APIs; it is never turned into a synthetic valid observation.

## 7. API contracts

All endpoints are read-only and versioned under `/api/v2/intelligence`.

### Market summary

```http
GET /api/v2/intelligence/market-summary?as_of=...
```

```json
{
  "as_of": "2026-07-22T10:00:00Z",
  "indices": [],
  "breadth": {},
  "regime": {},
  "quality": {},
  "provenance": {}
}
```

### Sector summary

```http
GET /api/v2/intelligence/sectors/{sector_id}/summary?as_of=...
```

Returns returns, relative strength, participation, breadth, freshness, and quality.

### Instrument feature snapshot

```http
GET /api/v2/intelligence/instruments/{instrument_id}/features?interval=1d&as_of=...
```

Returns the complete feature snapshot plus source candle, calculation version, freshness, quality, and confidence.

### Regime

```http
GET /api/v2/intelligence/regime?scope_type=market&scope_id=nse&as_of=...
```

Returns descriptive regime and evidence. It does not return an action.

### Breadth

```http
GET /api/v2/intelligence/breadth?as_of=...
```

Returns advances, declines, participation, leaders, laggards, and quality metadata.

### Top movers

```http
GET /api/v2/intelligence/top-movers?universe=nse&as_of=...
```

Returns observed movers and their measured change. It must not call the decision engine.

### Watchlist candidates

```http
GET /api/v2/intelligence/watchlist/{watchlist_id}?as_of=...
```

Returns descriptive facts for a configured watchlist. The name “candidates” means research inputs, not trade recommendations.

### Data quality and freshness

```http
GET /api/v2/intelligence/data-quality?scope=...
GET /api/v2/intelligence/freshness?scope=...
```

These endpoints expose missing, stale, quarantined, and delayed sources.

## 8. Ingestion pipeline

```text
1. Schedule source pull
2. Persist immutable raw payload and checksum
3. Normalize provider symbols and timestamps
4. Validate schema and market invariants
5. Quarantine invalid records
6. Upsert canonical market facts idempotently
7. Calculate feature snapshots from canonical inputs
8. Calculate breadth and regime snapshots
9. Ingest/dedupe/classify news
10. Publish read-model freshness and quality
```

Each stage should have a durable run record with:

- source
- scope
- started/completed time
- input watermark
- output count
- rejected count
- error summary
- code/calculation version

Retries belong to the ingestion job boundary and must never mutate Layer 1 financial state.

## 9. Testing strategy

### Unit tests

- indicator formulas with hand-calculated fixtures
- timestamp and session conversion
- OHLCV validation
- deduplication keys
- freshness calculations
- breadth calculations
- regime classification
- news normalization and classification contracts

### Property tests

- OHLC invariants
- deterministic repeatability
- no future data leakage
- idempotent ingestion
- feature snapshots are reproducible from identical inputs

### Integration tests

- source adapter to raw store
- raw store to canonical candles
- canonical candles to features
- features to breadth/regime
- news deduplication and symbol linking
- read APIs return provenance and quality

### Contract tests

Freeze JSON schemas for Layer 3 and Layer 4 consumers. Test backward-compatible additions and explicit version changes.

### Isolation tests

- Layer 2 cannot write Layer 1 order/trade/position tables
- intelligence jobs do not call execution services
- no API returns BUY/SELL recommendation fields
- development database is never used by integration tests

## 10. Milestone breakdown

### Phase 1 — Market Data Engine

Deliver:

- source adapter interface
- raw payload store
- canonical candles
- index and sector observations
- instrument metadata
- validation and freshness
- ingestion run records
- read endpoints for market facts and quality

Exit criteria: deterministic replay of a historical session with no future-data leakage.

### Phase 2 — Feature Store

Deliver:

- versioned feature calculations
- EMA, RSI, VWAP, MACD, ATR, Bollinger, ADX
- relative volume, volatility, trend, momentum
- support/resistance
- feature freshness and provenance APIs

Exit criteria: identical inputs and version produce identical snapshots.

### Phase 3 — Market Breadth

Deliver:

- A/D
- sector strength
- index participation
- leaders/laggards
- breadth APIs

Exit criteria: breadth reconciles against the canonical instrument universe.

### Phase 4 — News Intelligence

Deliver:

- article ingestion
- canonical dedupe
- symbol detection
- sentiment/classification versioning
- confidence and importance
- freshness APIs

Exit criteria: duplicate articles collapse deterministically and classifications are reproducible for a fixed classifier version.

### Phase 5 — Market Regime

Deliver:

- descriptive regime engine
- evidence and confidence
- market/index/sector/instrument scopes
- regime API

Exit criteria: regime output contains evidence and never emits a trade action.

### Phase 6 — Research APIs

Deliver:

- stable read-only JSON contracts
- pagination/as-of semantics
- quality/freshness envelope
- consumer contract tests

Exit criteria: a future ML or agent consumer can operate using Layer 2 APIs without raw-source access.

## 11. Layer 3 and Layer 4 compatibility

Layer 3 ML consumes:

- canonical candles
- feature snapshots
- breadth snapshots
- news classifications
- regime snapshots
- quality/freshness metadata

Layer 4 agentic AI consumes:

- research APIs
- explanations/evidence
- provenance
- freshness and confidence
- explicit data-quality warnings

Neither consumer should need to know the provider-specific ingestion format. Adding ML or agents later should not require changing Layer 2 contracts; only new consumers and model/agent-specific storage should be added.

## 12. Review decisions required before implementation

1. Which market-data providers are in scope for Phase 1?
2. Which exchanges, instruments, indices, and sectors are supported first?
3. Which candle intervals are required?
4. Which trading calendars and holidays are authoritative?
5. Should raw payloads use PostgreSQL JSONB or object storage plus metadata?
6. Which news classifier is permitted in Phase 4, if any?
7. How long should raw and derived data be retained?
8. Which API authentication and rate limits apply to research consumers?
9. What feature-set versioning policy should be frozen for Layer 3?
10. What confidence and quality thresholds should APIs expose?

## 13. Proposed implementation order after approval

Do not begin implementation until this proposal is approved. Once approved, implement one phase at a time, with schema migrations, unit tests, integration tests, and API contract tests for each phase.

---

# Approved Architecture Revision

The following decisions are now incorporated into the proposal.

## A. Revised architecture summary

Layer 2 is a bar-based, PostgreSQL-native market-intelligence platform. It stores immutable raw inputs, validated canonical bars, typed core features, versioned lineage, breadth, news facts, and descriptive regimes. It exposes read-only research contracts to future ML and agent consumers.

Layer 2 does not write to Layer 1 financial tables and does not produce recommendations.

## B. Bar granularity and VWAP semantics

Initial scope is bar-based, not tick-level.

Supported initial intervals:

- `1m`
- `5m`
- `15m`
- `1h`
- `1d`

OHLCV bars come from configured historical or market-data source adapters. Tick ingestion and exchange tick-by-tick calculations are deferred.

`session_bar_vwap` means VWAP calculated from available bars within a market session. It is not guaranteed to equal exchange-reported tick VWAP.

For bars `i` in a session:

```text
typical_price_i = (high_i + low_i + close_i) / 3
session_bar_vwap = Σ(typical_price_i × volume_i) / Σ(volume_i)
```

Rules:

- incomplete bars are excluded;
- bars must belong to the same instrument, interval, and trading session;
- session boundaries come from the configured exchange calendar;
- zero total volume produces an explicit unavailable/quality state;
- all arithmetic uses Decimal-compatible numeric semantics.

## C. Hybrid feature-store schema

Frequently queried core features use typed columns. JSON is retained only for experimental/uncommon features, calculation metadata, explanation metadata, and future extensibility.

`instrument_feature_snapshots` core columns:

```text
rsi_14 NUMERIC
ema_9 NUMERIC
ema_20 NUMERIC
ema_50 NUMERIC
macd NUMERIC
macd_signal NUMERIC
macd_histogram NUMERIC
atr_14 NUMERIC
adx_14 NUMERIC
session_bar_vwap NUMERIC
relative_volume NUMERIC
realized_volatility NUMERIC
momentum_1d NUMERIC
momentum_5d NUMERIC
```

JSON columns:

```text
experimental_features_json
calculation_metadata_json
explanation_metadata_json
```

Feature graduation process:

1. New feature starts in `experimental_features_json` with a definition version.
2. It receives usage, correctness, and performance evidence.
3. Its formula and null semantics are frozen in a feature-definition version.
4. A migration adds a typed nullable column.
5. Backfill is performed from reproducible source inputs.
6. APIs expose the typed field as canonical while retaining the old JSON value during a compatibility window.
7. The feature becomes a core indexed/queryable field only after contract tests pass.

Core ML access paths never require JSON parsing.

## D. Time-series partitioning

Initial deployment uses PostgreSQL-native monthly range partitioning. TimescaleDB is an optional future deployment enhancement, not an implementation dependency.

Partitioned tables:

| Table | Partition key | Example partition |
|---|---|---|
| `market_candles` | `started_at` | `market_candles_2026_07` |
| `instrument_feature_snapshots` | `calculated_at` | `feature_snapshots_2026_07` |
| `market_breadth_snapshots` | `observed_at` | `breadth_snapshots_2026_07` |
| `index_observations` | `observed_at` | `index_observations_2026_07` |
| `news_articles` | `published_at` | `news_articles_2026_07` |

Partition strategy:

- create the next month’s partition before ingestion reaches it;
- use a controlled default partition only for operational quarantine;
- name partitions `<logical_table>_YYYY_MM`;
- maintain local development partitions through migrations or a setup command;
- archive old partitions to compressed object storage before dropping them;
- retain metadata and quality summaries after raw data archival;
- never cascade-delete historical facts because an instrument becomes inactive.

Indexes are created on each partition and include the partition-local leading access keys, for example:

```text
market_candles: (instrument_id, interval, started_at DESC)
feature_snapshots: (instrument_id, interval, source_candle_end_at DESC)
breadth: (market, observed_at DESC)
```

PostgreSQL uniqueness on partitioned tables must include the partition key. Therefore candle identity is enforced as:

```text
(instrument_id, interval, started_at, source, started_at partition key)
```

The logical uniqueness columns already include `started_at`, satisfying PostgreSQL’s partitioned unique-index requirement.

Migration strategy:

1. create new partitioned replacement table;
2. copy and validate existing rows;
3. add indexes and constraints;
4. atomically swap names;
5. retain rollback metadata until verified;
6. create future partitions through a migration-managed maintenance task.

## E. Candle integrity and identity

Canonical candle constraints:

```text
ended_at > started_at
volume >= 0
trade_count >= 0, when present
open > 0, high > 0, low > 0, close > 0
high >= low
high >= open
high >= close
low <= open
low <= close
```

Candle identity is unique by:

```text
instrument_id + interval + started_at + source
```

Duplicate records with the same identity and checksum are idempotent no-ops. A corrected/revised candle creates a new source revision record, marks the prior record superseded, and triggers deterministic downstream recomputation. Historical rows are not silently overwritten.

## F. Instrument lifecycle

Use a stable internal `instrument_id` as the identity. Symbol, token, exchange, and sector metadata are time-valid attributes.

Required metadata:

```text
is_active
valid_from
valid_to
symbol_history_json or instrument_aliases table
provider_token_history
exchange_history
delisted_at
```

Symbol changes, token changes, exchange changes, and delisting create new metadata validity intervals. Historical market facts retain the stable ID and are never cascade-deleted when the instrument becomes inactive.

## G. Feature lineage and leakage prevention

Every feature snapshot must record:

```text
calculation_version
feature_definition_version
source_interval
source_window
data_cutoff_at
calculated_at
source_provider
source_record_id or source_candle_start/end range
input_quality_status
freshness_seconds
confidence, where applicable
```

`data_cutoff_at` is the latest timestamp permitted as an input. Layer 3 training and inference queries must filter:

```text
source_timestamp <= prediction_timestamp
data_cutoff_at <= prediction_timestamp
```

This prevents future-data leakage even when later corrections or backfills exist in the database.

## H. News deduplication

Deduplication is deterministic and two-stage.

### Stage 1: exact identity

Calculate normalized values and compare:

- canonical URL;
- source article ID;
- normalized headline hash;
- normalized body hash.

Any exact match is the same article or a provider duplicate.

### Stage 2: configurable similarity

For records not matched exactly, compare:

- normalized-title similarity;
- publication-time proximity;
- affected-symbol overlap;
- source similarity;
- configurable text-similarity threshold.

The decision and threshold are persisted as deduplication evidence. Initial implementation uses deterministic token/character similarity. MinHash or embeddings are future options and are not required initially.

## I. Layer 3 read-performance access patterns

| Workload | Query shape | Index/partition behavior | JSON parsing |
|---|---|---|---|
| 500 sequential snapshots for one instrument | `WHERE instrument_id=? AND interval=? ORDER BY source_candle_end_at LIMIT 500` | instrument/interval index and month pruning | none |
| One timestamp across universe | `WHERE source_candle_end_at=?` | timestamp index; targeted partitions | none |
| Date range and regime | join typed feature columns to regime by scope/time | month pruning plus `(calculated_at, scope)` indexes | none for core fields |
| Features plus future labels | feature cutoff range joined to label table on instrument/time | aligned time indexes and partition pruning | none |
| Valid at prediction time | `data_cutoff_at <= prediction_time AND quality_status='valid'` | composite quality/cutoff index | none |

Typed core columns are mandatory for these paths. JSON is only read for optional experimental features.

## J. Architecture decision records

### ADR-001: PostgreSQL versus TimescaleDB

Decision: use PostgreSQL-native monthly range partitioning initially.

Reason: available deployment, simpler local development, no extension dependency, and sufficient query/index capabilities. TimescaleDB may be evaluated later for hypertables, compression, and continuous aggregates.

### ADR-002: Bar data versus tick data

Decision: start with OHLCV bars.

Reason: lower storage/operational complexity and sufficient initial feature coverage. Tick ingestion is deferred.

### ADR-003: Typed features versus JSON

Decision: hybrid schema with typed core features and JSON extension fields.

Reason: predictable ML query performance and type safety without blocking experimentation.

### ADR-004: Exact versus fuzzy news deduplication

Decision: exact identity first, deterministic fuzzy similarity second.

Reason: exact hashes are explainable; similarity handles syndicated and lightly edited articles without embeddings or LLMs.

### ADR-005: Soft deletion versus cascade deletion

Decision: soft lifecycle/inactivation and validity intervals; no cascade deletion of historical intelligence.

Reason: reproducibility, auditability, and historical model training require old facts to remain addressable.

## K. Revised six-phase milestones

### Phase 1 — Market Data Engine

**Scope:** source adapters, raw payloads, canonical bars, indices, sectors, metadata, validation, freshness, monthly partitions.

**Schema:** source tables, raw payloads, partitioned candles, index/sector observations, lifecycle metadata, constraints, source identity uniqueness.

**Services/APIs:** ingestion adapter interface, validation service, market summary, data quality, freshness APIs.

**Tests:** adapter contract, OHLC constraints, duplicate/revision handling, timestamp/session boundaries, partition routing, replay determinism.

**Acceptance:** clean historical replay produces identical canonical rows and rejects invalid/future data.

**Exclusions:** no indicators, news classification, ML, agents, recommendations, or Layer 1 writes.

**Closure evidence:** migration output, validation counts, replay checksum, API contract tests, and partition/index explain plans.

### Phase 2 — Feature Store

**Scope:** typed core feature columns, JSON extensions, feature versions, bar-based VWAP, lineage, leakage-safe cutoff.

**Schema:** feature calculation runs, partitioned feature snapshots, typed columns, metadata JSON, lineage fields.

**Services/APIs:** deterministic feature calculator and instrument feature snapshot API.

**Tests:** formula fixtures, Decimal behavior, incomplete-bar exclusion, reproducibility, backfill, cutoff leakage tests, query performance.

**Acceptance:** identical input window/version produces identical typed feature values and complete lineage.

**Exclusions:** no trained model, recommendation, agent, or tick VWAP.

**Closure evidence:** formula comparison report, lineage samples, leakage test, migration/backfill report, and query plans.

### Phase 3 — Market Breadth

**Scope:** advances/declines, participation, sector strength, leaders/laggards, monthly breadth partitions.

**Schema:** breadth and sector-strength snapshots with quality, freshness, and provenance.

**Services/APIs:** breadth engine and breadth/sector summary APIs.

**Tests:** universe reconciliation, missing constituent handling, deterministic ranking, session boundary, partition pruning.

**Acceptance:** breadth facts reconcile to the canonical instrument universe for a session.

**Exclusions:** no trade ranking or BUY/SELL output.

**Closure evidence:** constituent counts, reconciliation report, API contract and replay tests.

### Phase 4 — News Intelligence

**Scope:** ingestion, exact identity, deterministic similarity dedupe, symbol mentions, sentiment metadata, confidence, importance, freshness.

**Schema:** raw articles, canonical articles, mention links, classifications, dedupe evidence.

**Services/APIs:** news adapter, dedupe service, classifier interface, news research API.

**Tests:** URL/source/hash duplicates, fuzzy threshold matrix, time proximity, symbol overlap, freshness, classifier version reproducibility.

**Acceptance:** syndicated duplicates collapse with explainable evidence and no embeddings/LLMs required.

**Exclusions:** no LLM calls, autonomous interpretation, or trading recommendations.

**Closure evidence:** dedupe precision/recall sample, classification version report, freshness tests, API contract tests.

### Phase 5 — Market Regime

**Scope:** trending, sideways, volatile, gap, expiry, and news-driven descriptive states with evidence.

**Schema:** regime snapshots, evidence, confidence, feature/source lineage, monthly partitioning where volume warrants.

**Services/APIs:** regime calculator and regime research API.

**Tests:** deterministic state fixtures, calendar handling, evidence completeness, cutoff leakage, stale-input behavior.

**Acceptance:** regime output is descriptive, reproducible, quality-aware, and never an action.

**Exclusions:** no BUY/SELL generation, ML model, or agent.

**Closure evidence:** state matrix, replay report, lineage samples, and API contract tests.

### Phase 6 — Research APIs

**Scope:** stable read-only contracts for market, sector, features, regime, breadth, movers, watchlists, quality, and freshness.

**Schema:** API contract/version metadata and optional materialized read models.

**Services/APIs:** `/api/v2/intelligence/*` endpoints with as-of and provenance semantics.

**Tests:** OpenAPI contract, backward compatibility, pagination, as-of consistency, authorization, query plans, consumer fixtures.

**Acceptance:** future ML and agent consumers need no raw-source access and no Layer 1 integration.

**Exclusions:** no model training, LLM calls, agents, recommendations, or execution.

**Closure evidence:** published OpenAPI schema, contract test report, performance report, quality/freshness examples.

## L. Deferred items

- tick-level ingestion and exchange tick VWAP;
- TimescaleDB deployment;
- embeddings or MinHash-based news similarity optimization;
- trained ML models;
- LLMs and agentic workflows;
- broker integration and live trading;
- real-time feature streaming;
- automated feature selection;
- cross-provider learned entity resolution.

## M. New risks

- Monthly partition maintenance can fail if future partitions are not created.
- Typed-column migrations require careful backfill and compatibility windows.
- Source corrections can cause downstream feature revisions and model reproducibility concerns.
- Bar-based VWAP may differ materially from exchange tick VWAP.
- Fuzzy news dedupe thresholds may over-merge or under-merge syndicated articles.
- Instrument lifecycle errors can incorrectly join historical facts.
- Feature cutoff errors can introduce training leakage.
- Provider timestamp/session semantics may differ across exchanges.

## N. Decisions still requiring approval

1. Initial market-data providers and licensing limits.
2. Initial exchange, universe, sector taxonomy, and intervals.
3. Calendar authority and holiday source.
4. Raw payload retention duration and object-storage requirement.
5. Core feature definition versions and null semantics.
6. News source list and initial similarity threshold.
7. API authentication, quotas, and consumer tenancy.
8. Partition retention and archive policy.

## O. Recommended first implementation milestone

Start with **Phase 1 — Market Data Engine**.

The first implementation increment should deliver only:

- source adapter interfaces;
- immutable raw payload storage;
- canonical bar normalization;
- candle integrity constraints;
- stable instrument lifecycle metadata;
- monthly PostgreSQL partitions;
- freshness and data-quality envelope;
- deterministic replay tests;
- read-only market-data and quality endpoints.

Do not begin Feature Store calculations until Phase 1 replay, partitioning, validation, and lineage evidence is accepted.
