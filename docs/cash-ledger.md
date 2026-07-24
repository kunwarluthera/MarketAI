# Cash ledger

Cash is the sum of append-only `cash_ledger.amount`: initial capital, buy debits, sell credits,
brokerage, and tax. Normal services never update or delete entries. `/paper/reconcile` compares the
ledger against executed trades and reports the exact difference.
