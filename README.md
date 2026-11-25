# dnscope

Multi-agent domain threat investigation with deterministic scoring and LLM narration.

[![CI](https://github.com/<owner>/dnscope/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/dnscope/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/demo-live-brightgreen)](https://dnscope.example.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

dnscope is an autonomous domain threat investigation platform engineered to analyze suspicious domains in seconds. It orchestrates parallel intelligence gathering across DNS, RDAP, and VirusTotal to evaluate domain risk without creating an analyst bottleneck. Instead of relying on an opaque, hallucination-prone LLM to assign arbitrary risk scores, dnscope strictly decouples mathematical evaluation from narrative synthesis: a rule-based engine computes a deterministic 0–100 threat score, while Google Gemini translates technical findings into clear, contextual security narratives. Built with a zero-friction public demo, analysts and incident responders can immediately inspect domains and share verifiable, tamper-proof threat reports with a single URL.

## Interface

![dnscope homepage](docs/screenshot-home.png)

## Quick Start

### Tier A — Public Demo
Visit the hosted public instance at [https://dnscope.example.com](https://dnscope.example.com) to investigate any domain anonymously with zero configuration or sign-up.

### Tier B — Local Production Stack (Docker Compose)
Run the full production-parity stack (PostgreSQL 16, FastAPI backend, and Nginx reverse proxy serving the React SPA) using Docker Compose:

`ash
# Clone the repository and build images
docker compose -f docker-compose.prod.yml up --build

# Open http://localhost:3000 in your browser
# Shut down the stack cleanly when finished:
docker compose -f docker-compose.prod.yml down
`

### Tier C — Local Development Environment
Run services locally with hot-module reloading and full debug support:

`ash
# Prerequisites: Python 3.11+, Node.js 20+, Docker (for Postgres)

# 1. Start local PostgreSQL 16 container on :5432
make db-up

# 2. Run database migrations via Alembic
make migrate

# 3. Start the FastAPI backend with hot-reload on :8000
make api

# 4. Start the Vite development server on :5173 (in a separate terminal)
make web-dev
`

## How It Works

dnscope utilizes LangGraph to coordinate domain intelligence gathering across specialized concurrent agents:

`mermaid
graph LR
    A[Domain] --> B[Validate]
    B --> C[DNS Agent]
    B --> D[RDAP Agent]
    B --> E[VirusTotal Agent]
    C --> F[Scoring Engine]
    D --> F
    E --> F
    F --> G[ScoreResult 0-100]
    G --> H[Supervisor]
    H --> I[Gemini Narrates]
    G --> H
    H --> J[Structured Report]
`

### Specialized Agents
- **DNS Agent**: Resolves A, AAAA, MX, NS, TXT, and SOA records; computes Shannon entropy on domain labels; verifies MX mail host validity; and audits SPF/DKIM security configurations.
- **RDAP Agent**: Queries authoritative ICANN bootstrap endpoints; calculates registration age, domain lifetime, and days to expiration; extracts registrar identity and abuse contacts.
- **VirusTotal Agent**: Interrogates the VirusTotal API v3 for security vendor detection ratios, malicious/suspicious reputation flags, and categorization tags.

### Deterministic Scoring & 12 Security Rules
Outputs from all three agents are aggregated into a pure-function scoring engine executing 12 discrete heuristic rules:
- RULE_HIGH_ENTROPY: Detects algorithmically generated domain names (DGA) via high Shannon entropy.
- RULE_NEWLY_REGISTERED: Identifies newly created domains registered within the past 30 days.
- RULE_EXPIRING_SOON: Flags short-lived campaign domains expiring within 30 days.
- RULE_SUSPICIOUS_TLD: Checks against known high-abuse, low-reputation top-level domains.
- RULE_FREE_MAIL_PROVIDER: Highlights domains abusing free webmail providers for business identities.
- RULE_MISSING_MX: Evaluates domains advertising mail capabilities without reachable mail exchanges.
- RULE_SPF_SOFTFAIL_OR_NONE: Detects absent or permissive SPF policies that allow unauthorized email spoofing.
- RULE_VT_MALICIOUS: Triggers when multiple VirusTotal security vendors classify the domain as malicious.
- RULE_VT_SUSPICIOUS: Triggers on elevated suspicious detection ratios in VirusTotal threat feeds.
- RULE_PARKED_OR_SINKHOLE: Flags known parking nameservers, sinkhole IP spaces, and landing pages.
- RULE_FAST_FLUX: Detects short-TTL multi-IP rotations characteristic of fast-flux botnets.
- RULE_ANOMALOUS_TTL: Identifies TTL values configured specifically to evade DNS caching mechanisms.

### Supervisor & Score Invariance
The engine computes an exact 0–100 risk score and maps it to a severity tier (LOW, MEDIUM, HIGH, CRITICAL). The supervisor transmits structured findings and the fixed score to Google Gemini (or a NullExplainer fallback). Gemini generates an executive summary contextualizing the threat. Rigorous property tests verify score invariance: the LLM functions strictly as an explainer and is structurally incapable of overriding or altering the deterministic score.

## Key Features

- **Deterministic Scoring Engine**: 12 transparent heuristic rules evaluate domain entropy, age, registrar traits, and mail security configs.
- **Concurrent LangGraph Orchestration**: Gathers telemetry simultaneously across network boundaries to minimize end-to-end investigation latency.
- **Score-Invariance Guarantee**: Cryptographic and architectural constraints ensure generative AI purely narrates and cannot alter numerical risk ratings.
- **Verifiable Evidence References**: Every triggered rule explicitly cites its underlying evidence objects for auditability and manual review.
- **Surfaced Inconclusive Telemetry**: Missing, timed-out, or rate-limited upstream signals are prominently flagged rather than silently ignored or assumed clean.
- **Frictionless Anonymous Mode**: Zero-authentication public investigations backed by client IP rate limits and temporary 1-hour shareable URLs.
- **Multi-Tenant API Key Management**: High-throughput authenticated workflows using Argon2id password hashing and O(1) HMAC key prefix lookups.
- **Resilient Async Persistence**: Non-blocking database transactions via SQLAlchemy 2.0 and asyncpg with automatic connection pooling.
- **Production-Grade Test Suite**: ~300 tests spanning unit, integration, live upstream checks, and frontend UI specifications.

## Why This Is Different

Conventional security tools frequently fall into two extremes: either basic API wrappers that dump raw JSON onto the analyst, or unconstrained LLM agents that hallucinate risk ratings and produce inconsistent verdicts across identical inputs. 

dnscope treats security scoring as an exact, deterministic science and treats language models as executive communicators. By strictly isolating telemetry evaluation into pure mathematical rules, dnscope ensures reproducible threat calculations, full evidence auditability, and zero hallucinated scores.

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11, FastAPI, LangGraph, Pydantic v2, SQLAlchemy 2.0 (asyncio) |
| Threat Intelligence | dnspython, RDAP (HTTP/JSON), VirusTotal API v3, Google Gemini (google-genai) |
| Persistence & Storage | PostgreSQL 16, asyncpg, Alembic migrations |
| Frontend | React 18, Vite 5, TypeScript (strict mode), Tailwind CSS 3.4, TanStack Query 5 |
| Authentication & Security | API Key authentication (Argon2id + HMAC-SHA256 indexing), IP rate limiting |
| Observability & Tracing | Python JSON Logger (structured JSON logs), Correlation ID middleware |
| CI & Quality Assurance | GitHub Actions (Ruff, Mypy, Pytest, ESLint, Vitest, Vite build) |

## API Reference

dnscope provides both anonymous demo endpoints and authenticated tenant endpoints:

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /investigate | None | Run anonymous domain investigation (IP rate-limited to 10/hr) |
| GET | /r/{share_id} | None | Fetch shared investigation report by share token (1h TTL) |
| POST | /investigations | API Key | Submit domain for background investigation (returns job ID) |
| GET | /jobs/{id} | API Key | Poll status and progress of an asynchronous investigation job |
| GET | /investigations | API Key | List historical investigations for the authenticated tenant |
| GET | /investigations/{id} | API Key | Retrieve full investigation details, score, and rule traces |
| POST | /admin/api-keys | Admin Key | Provision and issue new tenant API keys with scoped roles |
| GET | /health | None | System liveness and database connectivity health probe |

Interactive Swagger documentation and schema explorer are available at /docs when running the API.

## Testing

The project maintains comprehensive test coverage across both backend and frontend layers:

`ash
# Backend test suites
make test               # Run backend unit and integration test suite (~247 tests)
make test-live          # Run live-network upstream tests (requires real API keys in .env)
make lint               # Check backend code formatting and linting with Ruff
make typecheck          # Run static type analysis on backend source with Mypy

# Frontend test suites
make web-test           # Run frontend Vitest component and hook test suite (~53 tests)
make web-lint           # Check frontend code with ESLint
make web-typecheck      # Verify frontend TypeScript types with tsc
make web-build          # Verify production SPA build with Vite
`

Test automation includes property-based tests verifying deterministic score calculations, invariant checks guaranteeing LLMs cannot tamper with threat levels, and mock network fixtures simulating upstream provider outages.

## Configuration

Runtime parameters are configured via environment variables. Create a .env file from .env.example:

| Variable | Description | Default |
|---|---|---|
| DATABASE_URL | PostgreSQL async connection string | postgresql+asyncpg://postgres:postgres@localhost:5432/dnscope |
| GEMINI_API_KEY | Google Gemini API key for executive narration | None (falls back to NullExplainer) |
| GEMINI_MODEL | Google Gemini model identifier | gemini-2.5-flash-lite |
| VT_API_KEY | VirusTotal API v3 key for reputation telemetry | None (agent marks VT as inconclusive) |
| API_KEY_HMAC_SECRET | Secret key used for HMAC-SHA256 key prefix lookup | dev-only-change-me |
| CORS_ALLOWED_ORIGINS | Comma-delimited list of permitted browser origins | http://localhost:5173,http://localhost:3000 |
| PUBLIC_RATE_LIMIT_PER_HOUR | Hourly request quota per client IP on /investigate | 10 |
| PUBLIC_LLM_DAILY_CAP | Global daily ceiling for anonymous LLM syntheses | 500 |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Footer

Architected and implemented via structured phased engineering — see git history and phase tags for the evolutionary development log.
