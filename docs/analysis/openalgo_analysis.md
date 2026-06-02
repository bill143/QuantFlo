# Source Analysis — `marketcalls/openalgo`

> QUANTFLO Stage 1 repo analysis. Real file paths relative to `_research/openalgo/`.
> QUANTFLO scope: CME index futures (NQ MNQ ES MES YM MYM).

## 1. License (authoritative)

- **SPDX:** `AGPL-3.0` (GitHub Licenses API; `License.md` = GNU Affero GPL v3).
- **Classification:** **STRONGEST (NETWORK) COPYLEFT.** Even SaaS/network use of
  derivative code triggers source-disclosure obligations.
- **Clean-room required?** **YES — MANDATORY, and most cautious of all sources.** Do
  NOT copy, port, or paste any openalgo source into QUANTFLO. Extract only
  *abstractions, contracts, and behavioral specs* and reimplement from a clean spec
  written by someone who has not read the implementation. The cited paths confirm a
  feature *exists*; they are not a copy source.

## 2. Architecture summary

Self-hosted Flask (Python 3.12) + React 19 algo-trading platform. Defining trait: a
**broker-agnostic abstraction** where one OpenAlgo order/symbol/data vocabulary fans
out to 30+ Indian-broker plugins via dynamic `importlib` loading. Three layers matter
for QUANTFLO: (1) a **service layer** (`services/`) with a uniform
`(success, response, status_code)` envelope; (2) **per-broker plugin adapters**
(`broker/{name}/`) translating OpenAlgo ↔ broker format for REST + WS; (3) a **unified
market-data pipeline** (broker WS adapter → ZeroMQ PUB → unified WS proxy → clients).
Distinctive: **mode-switching at the service boundary** — every order service checks
`get_analyze_mode()` and transparently routes to a `sandbox/` paper-trade engine with
identical request/response shapes. India-broker-specific, but the *patterns* transfer.

| Path | Purpose |
|------|---------|
| `services/` | broker-neutral business logic; uniform envelope |
| `broker/{name}/` | per-broker plugin: `api/`, `mapping/`, `streaming/`, `plugin.json` |
| `websocket_proxy/` | unified WS server + `base_adapter.py` (abstract + ZMQ) |
| `sandbox/` | paper-trade engine (execution, fund/margin, square-off) |
| `restx_api/` | Flask-RESTX `/api/v1/` (thin; delegate to services) |
| `utils/event_bus.py` + `events/` | in-process typed pub/sub |
| `database/auth_db.py` | Argon2 key hashing + Fernet token-at-rest encryption |

## 3. Candidate features — ELITE / NOT-ELITE (all AGPL → clean-room)

| # | Feature | Path | Verdict | Why |
|---|---------|------|---------|-----|
| 1 | Broker adapter plugin pattern (capability-driven) | `utils/plugin_loader.py`, `broker/*/plugin.json`, `services/place_order_service.py` (`import_broker_module`) | **ELITE** | Capability-registry + dynamic-dispatch + format-transform = the "unified broker API" the traders team needs; transfers to a Tradovate/CME adapter. |
| 2 | Smart Order (target-position delta executor) | `broker/*/api/order_api.py` (`place_smartorder_api`), `services/place_smart_order_service.py` | **ELITE** | Declarative "converge to target position" with flip/no-op edge cases — the right primitive for autonomous execution. |
| 3 | Sandbox/Analyzer paper-trade w/ transparent mode-switch | `sandbox/execution_engine.py`, `fund_manager.py`, `squareoff_manager.py`, `services/place_order_service.py` (mode routing) | **ELITE** | "Same API, flip a flag to paper-trade" — invaluable for governance/risk validation. |
| 4 | Unified WebSocket market-data normalization pipeline | `websocket_proxy/base_adapter.py`, `mapping.py`, `broker/*/streaming/*_adapter.py` | **ELITE** | Normalize→ZMQ-bus→fanout decoupling (broker feed never blocks slow clients) + LTP/Quote/Depth capability negotiation; transfers to CME depth feeds. |
| 5 | Auth-token-at-rest encryption + API-key hashing | `database/auth_db.py` (Argon2 + Fernet/PBKDF2, boot-time pepper validation) | **ELITE (pattern)** | "Broker creds never in plaintext, validated at boot" discipline for risk-compliance/governance holding Tradovate creds. |
| 6 | Stale-token auto-recovery + cache invalidation | `websocket_proxy/base_adapter.py` (`get_fresh_auth_token`, `handle_auth_error_and_retry`), `auth_db.py` | **ELITE (pattern)** | Robust session/token-refresh for 24/5 autonomous CME trading where sessions expire. |
| 7 | In-process event bus decoupling order side-effects | `utils/event_bus.py`, `events/`, `subscribers/` | **ELITE (pattern)** | Monitoring/governance subscribe to the same order events the trader emits; clean multi-team fit. |
| 8 | Configurable per-endpoint rate-limiting | `limiter.py`, `restx_api/place_order.py` | **NOT-ELITE** | Commodity Flask-Limiter wrapper; QUANTFLO wants exchange/broker-aware throttling, not IP-based web limits. |

### Rejected / NOT-ELITE (with reason)
- CSP/CORS/security headers (`csp.py`, `cors.py`) — standard env-driven Flask middleware; trivial to rebuild.
- Rate limiter (`limiter.py`) — thin wrapper (#8).
- REST/Flask-RESTX endpoints (`restx_api/*`) — thin controllers; value is in `services/`. Many endpoints (`option_chain`, `option_greeks`, `iv_smile`, `gex`, `max_pain`) are India-options-specific, out of scope.
- GTT/basket/split/Action-Center order types — India-broker-feature-shaped.
- Telegram/WhatsApp bots (incl. duplicate `_v2`/`_fixed` files signalling churn) — non-differentiating alerting.
- 30+ concrete broker adapters (`broker/aliceblue`…`zebu`) — all Indian brokers; value is only the *pattern* (#1), not any implementation.
- DuckDB historify / no-code Flow builder — orthogonal, India/equity-options oriented.

## 4. Feasibility probe — **DEFERRED (commands specified; blocker recorded)**

Several flagship patterns have **creds-free, mock-based** tests, but **blocker:** they
require installing the full Flask app stack via `uv`. Deferred. **Exact creds-free
commands (validate before clean-room):**

- Feature #2 (best clean-room reference — 12-case truth table): `uv run pytest test/test_smartorder_logic.py -v`
- Feature #3 (sandbox): `uv run pytest test/sandbox/ -v` (`test_fund_manager.py`, `test_margin_scenarios.py`, …)
- Feature #8: `uv run python test/test_rate_limits_mock.py`
- Feature #1 (contract shape, no install): `python -c "import json,glob; [print(json.load(open(p))) for p in glob.glob('broker/*/plugin.json')]"`

Features #1–#7 marked **ELITE (probe deferred)**.

## 5. License-compatibility note (AGPL-3.0)

**Clean-room mandatory; network-copyleft risk.** Reimplement only patterns from clean
specs. The single best clean-room reference is the **SmartOrder delta truth-table**
(`test/test_smartorder_logic.py`) — port the *spec table*, not the broker code. Features
whose only value is concrete code (flag — NOT worth reimplementing from scratch): the
30+ broker adapter bodies, the CSP/CORS/limiter wrappers, the options-greeks endpoints.
Worth clean-rooming (patterns): #1 plugin/capability dispatch, #2 SmartOrder logic, #3
sandbox mode-switch, #4 WS normalization + ZMQ fanout, #5/#6 token security, #7 event
bus. Target modules: #1/#2 → `execution/`; #3 → testers + governance; #4 → `data/` +
`teams/data_engineering`; #5/#6 → `core/config` + `teams/risk_compliance`; #7 →
`orchestration` state bus.
