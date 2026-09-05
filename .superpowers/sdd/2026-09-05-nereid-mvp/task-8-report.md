

## Fix round 1

- Replaced client-authored export envelope/rows with a validated bounded plan and explicit `(wmo, cycle, source_profile_index)` selections. The API re-executes locally, accepts only QC-eligible returned representations, rejects altered IDs, and builds provenance from server-owned rows.
- Section grouping now expands each WMO/cycle to all representations and identifies coordinates with source representation and sampling scheme; interpolation never crosses them.
- The query evaluator now invokes configured AzurePlanner and independently compares all expected fields, failing below 27/30. Its fake-planner unit test tests comparison only. On this host it returned exit 2: `planner evaluation BLOCKED: Azure configuration unavailable; no score measured`.
- Receipt now offers explicit representation checkboxes; E2E selects exactly two and sends only their IDs to export.

Focused green checks: API export/evaluator/store tests: 9 passed; web unit tests: 18 passed; winning-flow Playwright: passed. Planner gate remains BLOCKED, so Task 8 is not fully satisfied until configured Azure evaluation reaches 27/30.
