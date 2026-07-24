# EOD processing

Intraday EOD exits are configured for Asia/Kolkata with a default 15:20 cutoff. Delivery positions
are not eligible. Same-candle stop/target ambiguity uses the conservative stop-first rule:
`AMBIGUOUS_SAME_CANDLE_STOP_TARGET_CONSERVATIVE_STOP`.
