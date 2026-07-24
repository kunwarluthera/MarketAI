# Layer 3.6.3B Acceptance Matrix

| Area | Evidence | Status |
|---|---|---|
| Policy registry | Migration 0040 and seeded policy | Implemented |
| Probability structure | `statistical_validation.core` and focused tests | Implemented |
| Confidence, margin, entropy | Deterministic core functions and tests | Implemented |
| Calibration evidence | Migration 0043, model, metric checks | Implemented |
| Regression evidence | Migration 0044, model, bounds/interval checks | Implemented |
| Reference distribution | Migration 0045, model and compatibility checks | Implemented |
| Class support | Deterministic support validator and tests | Implemented |
| Resource controls | Class/sample limits and tests | Implemented |
| Manifests/events | Migration 0041 and immutable persistence | Implemented |
| Invalidation/supersession | Migration 0042 and authenticated lifecycle APIs | Implemented |
| Replay/comparison | Migration 0046, deterministic replay service and APIs | Implemented |
| Evidence read APIs | Authenticated calibration/regression/reference endpoints | Implemented |
| Authentication | Focused unauthenticated API tests | Implemented |
| Full isolated regression | 117 passed, 0 failed after clean reset | Verified |
| Ruff/compilation | Final checks passed | Verified |
| Full statistical orchestration | No single persisted aggregate workflow covering every requested rule group | Pending |
| Exhaustive security matrix | Focused coverage exists; full threat matrix is not implemented | Pending |
| Production calibration registry workflow | Evidence persistence exists; approval/expiry workflow is not implemented | Pending |

## Decision

The implemented scope is verified, but the rows marked Pending prevent the milestone from being represented as fully complete against the original specification.

**Layer 3.6.3B — NOT VERIFIED COMPLETE**
