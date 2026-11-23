# dnscope

A multi-agent domain threat-investigation platform.

## Phase 0 Scope

Phase 0 establishes the core repository scaffolding, contracts, and deterministic scoring engine:
- **Pydantic Schemas**: Strict contracts in `dnscope.schemas` defining findings for DNS, registration (RDAP), reputation (VirusTotal), scoring traces, and investigation state.
- **Deterministic Scoring Engine**: Pure rule functions in `dnscope.scoring.rules` and engine orchestration in `dnscope.scoring.engine` calculating transparent risk scores clamped to `[0, 100]`.
- **Zero Agent Logic**: Agents are deferred to Phase 1 (`dnscope.agents` contains only `__init__.py`).
- **Zero External API Calls**: All tests rely strictly on stubbed data and fixtures.

## Running Tests and Quality Checks

Prerequisites: Python 3.11+ and `uv`.

```bash
# Install dependencies
make install

# Run test suite
make test

# Run linter
make lint

# Run type checker
make typecheck
```

