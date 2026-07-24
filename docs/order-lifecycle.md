# Order lifecycle

An actionable decision creates a pending approval. Manual approval validates expiry, kill switch,
cash, duplicate position, and the persisted risk result. It then atomically creates a filled paper
BUY, order event, trade, position, ledger entries, snapshot, and audit events. An exit creates a
SELL trade and review in the same transaction. Replaying an idempotency key returns the original
order; changing its payload is a conflict.
