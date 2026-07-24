# Security

This is a local single-user product. CORS permits the local UI only. Inputs are schema validated;
the UI never receives configured secrets; order keys are stored as hashes; audit events are
append-only. The included fixed demo bearer token is only for keyless demo operation and must be
replaced by signed, expiring sessions before any non-local deployment.
