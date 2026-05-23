# Stack Research

**Domain:** Hybrid AI trading system for MetaTrader 5 with web dashboard
**Researched:** 2026-05-23
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Primary language | MT5 package requires Python on Windows; 3.12+ for performance improvements and latest library support |
| MQL5 | MT5 built-in | Expert Advisor language | Non-negotiable — MT5 EAs must be written in MQL5 |
| MetaTrader5 (Python) | 5.0.5735 | MT5 data & order API | Official Python connector from MetaQuotes; provides `copy_rates_*`, `order_send`, `account_info`, etc. Windows-only |
| ZeroMQ (pyzmq) | 27.1.0 | EA ↔ Python IPC | Most reliable real-time communication pattern between MQL5 EA and Python AI process; battle-tested in algo trading |
| FastAPI | 0.136+ | Web API backend | Async-first, auto-docs (Swagger), Pydantic validation, WebSocket support for real-time dashboard updates, fastest Python web framework |
| Uvicorn | 0.47.0 | ASGI server | Production server for FastAPI; `uvicorn[standard]` includes uvloop for performance |
| SvelteKit | 2.x | Web dashboard frontend | Smallest bundle, simplest mental model, excellent for dashboards, developer new to frontend can learn faster than React |
| PyTorch | 2.x | ML/AI framework | Industry standard for custom neural networks; flexible, debuggable, extensive trading ML literature. Better than TensorFlow for research iteration speed |
| scikit-learn | 1.6+ | Classical ML & feature engineering | Random forests, gradient boosting for signal quality classification; preprocessing pipelines; faster to train than deep learning for tabular features |
| PostgreSQL | 16+ | Persistent data store | Trade history, model parameters, system state. More reliable than SQLite for concurrent writes from AI process + API server |
| Redis | 7.x+ | Real-time state & pub/sub | Market data cache, WebSocket message broker between AI process and dashboard, session storage |
| Docker | — | Containerization | Package the Python stack (FastAPI, AI process, workers) for reproducible deployment; MT5 itself runs natively on Windows host |

### MQL5 EA Layer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| MQL5 ZeroMQ binding | mql5-lib | EA ZeroMQ integration | Standard MQL5 header/library for ZeroMQ; enables EA to publish parameters and subscribe to AI signals via TCP sockets |
| MQL5 Standard Library | MT5 built-in | Data structures, trade operations | Official MQL5 stdlib for `CTrade`, `CSymbolInfo`, `CPositionInfo` — avoids reinventing wheel |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 2.2+ | Time-series manipulation | All data pipeline work — OHLCV DataFrame handling, feature computation |
| numpy | 2.x | Numerical computation | Required by PyTorch, TA-Lib, pandas; direct array ops for indicator math |
| TA-Lib | 0.6.8 | Technical indicators | 150+ indicators (RSI, MACD, Bollinger, ATR, etc.) with Cython-based performance; now has Windows wheels so no manual C lib install |
| stable-baselines3 | 2.8.0 | Reinforcement learning algorithms | If pursuing RL approach for policy learning (PPO, SAC, DQN); well-documented, sklearn-like API |
| gymnasium | 1.0+ | RL environment interface | Required by stable-baselines3; defines trading environment observation/action spaces |
| SQLAlchemy | 2.x | ORM for PostgreSQL | Async-compatible ORM for FastAPI; Alembic for migrations |
| Alembic | 1.13+ | Database migrations | Schema evolution as data models change |
| pydantic | 2.x | Data validation | FastAPI dependency; defines settings models, API schemas, AI parameter contracts |
| python-dotenv | 1.0+ | Environment configuration | Load API keys, DB URLs, broker credentials from `.env` — never hardcode secrets |
| structlog | 24.x+ | Structured logging | JSON logs for production, human-readable for dev; integrates with FastAPI |
| httpx | 0.27+ | Async HTTP client | Used by FastAPI TestClient; also useful for any external API calls |
| websockets | 12.x+ | WebSocket client | If needing WebSocket client connections from Python to external services |

### Frontend Libraries

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| SvelteKit | 2.x | Dashboard framework | SSR + CSR hybrid, file-based routing, excellent DX |
| TradingView Lightweight Charts | 4.x | Financial charting | Industry-standard candlestick/indicator charts; framework-agnostic, tiny bundle |
| Tailwind CSS | 4.x | Styling | Utility-first CSS; fast iteration without writing custom CSS |
| skeleton-ui | 3.x (orFlowbite Svelte) | Component library | Pre-built dashboard components (tables, cards, nav) for Svelte with Tailwind |
| socket.io-client | 4.x | WebSocket client | Auto-reconnect, event-based API; simpler raw WebSocket alternative with reconnection logic |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Testing framework | Python standard; use `pytest-asyncio` for FastAPI tests |
| pytest-asyncio | Async test support | Required for testing FastAPI endpoints and async AI processes |
| black | Code formatting | Opinionated, zero-config, eliminates style debates |
| ruff | Linting | Replaces flake8, isort; extremely fast Rust-based linter |
| mypy | Type checking | Trading systems benefit enormously from static typing — parameter contracts, order types |
| Docker Compose | Multi-container orchestration | Define Postgres + Redis + API + AI process as a stack |
| GitHub Actions | CI/CD | Free for personal repos; run tests on push |

## Installation

```bash
# Core Python dependencies
pip install "MetaTrader5>=5.0.5735"
pip install "pyzmq>=27.1.0"
pip install "fastapi[standard]>=0.136"
pip install "uvicorn[standard]>=0.47"
pip install "torch>=2.0"          # PyTorch (install from pytorch.org for GPU support)
pip install "scikit-learn>=1.6"
pip install "pandas>=2.2"
pip install "numpy>=2.0"
pip install "TA-Lib>=0.6.8"      # Now has Windows wheels
pip install "sqlalchemy[asyncio]>=2.0"
pip install "alembic>=1.13"
pip install "pydantic>=2.0"
pip install "pydantic-settings>=2.0"
pip install "python-dotenv>=1.0"
pip install "structlog>=24.1"
pip install "httpx>=0.27"

# RL (if pursuing reinforcement learning)
pip install "stable-baselines3>=2.8.0"
pip install "gymnasium>=1.0"

# Dev dependencies
pip install "pytest>=8.0"
pip install "pytest-asyncio>=0.23"
pip install "black>=24.0"
pip install "ruff>=0.4"
pip install "mypy>=1.10"
```

```bash
# Frontend (SvelteKit)
npm create svelte@latest dashboard
cd dashboard
npm install
npm install lightweight-charts   # TradingView charts
npm install -D tailwindcss @tailwindcss/vite
npm install socket.io-client
```

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|--------------------------|
| Web Framework | FastAPI | Django | If you need built-in admin panel, ORM, auth — adds complexity we don't need |
| Web Framework | FastAPI | Flask | Flask is synchronous and slower; no async, no auto-docs. Only if team has deep Flask experience |
| Web Framework | FastAPI | Litestar | Newer alternative, similar async. Smaller community = fewer tutorials. Revisit in 6 months |
| Frontend | SvelteKit | React + Next.js | If you plan to open-source and want largest community; more ecosystem libraries. Higher learning curve |
| Frontend | SvelteKit | Vue + Nuxt | Good middle ground, larger community than Svelte. More verbose than Svelte |
| ML Framework | PyTorch | TensorFlow/Keras | Only if using pre-trained TF models; PyTorch dominates research and trading ML |
| ML Framework | PyTorch | JAX | Only for advanced research requiring XLA compilation; overkill here |
| RL Library | stable-baselines3 | CleanRL | If you need simpler, more readable implementations for one-off experiments |
| RL Library | stable-baselines3 | Ray RLlib | If distributed RL training across multiple nodes; significant complexity overhead |
| Database | PostgreSQL | SQLite | Servicable for single-user, but no concurrent write support, no pub/sub. Risky for trading data |
| Cache/Pub-sub | Redis | SQLite + polling | No real-time push, polling adds latency. Only for absolute minimum setups |
| Cache/Pub-sub | Redis | Memcached | No pub/sub, no persistence. Redis is a superset of Memcached |
| Charts | Lightweight Charts | Chart.js | Chart.js is generic; not designed for financial data (candlesticks, volume profiles) |
| Charts | Lightweight Charts | D3.js | Maximum flexibility, massive complexity. 10x more code for same chart |
| IPC | ZeroMQ | Named pipes | Simpler but no proper framing, no multi-client, platform quirks |
| IPC | ZeroMQ | File-based communication | Race conditions, no real-time guarantee. Only for batch processing |
| IPC | ZeroMQ | HTTP REST between EA→Python | Higher latency, more overhead. ZeroMQ is designed for low-latency IPC |
| ORM | SQLAlchemy | Tortoise ORM | Async-native, but smaller community, fewer features. Consider if SQLAlchemy async feels too complex |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| MetaTrader4 (MT4) | MT5 is the current platform; MT4 is legacy, no depth of market, no hedging support | MetaTrader5 |
| MQL4 | MT4 language; incompatible with MT5 | MQL5 |
| tensorflow/keras | PyTorch dominates trading ML research; TF 2.x API confusion; slower debug cycle | PyTorch |
| websockets (Python) for EA↔Python | MQL5 native WebSocket client is immature and poorly documented | ZeroMQ (pyzmq + mql5-lib) |
| sqlite for production data | Concurrent writes from AI + API will lock; no WAL reliability for trading data | PostgreSQL |
| Flask | No native async, no WebSocket support, slower performance | FastAPI |
| Django REST Framework | Massive overhead for a dashboard API; async support is bolted on | FastAPI |
| multiprocessing for EA↔Python | ZeroMQ is purpose-built for this; multiprocessing adds complexity without benefits | ZeroMQ |
| Named pipes for EA↔Python | No framing protocol, blocking reads, platform-specific behavior | ZeroMQ (pyzmq + mql5-lib) |
| pandas-ta | Slower, less maintained than TA-Lib; Cython-based TA-Lib is 2-4x faster | TA-Lib |
| ta (technical-analysis lib) | Pure Python, significantly slower than TA-Lib's C implementation | TA-Lib |
| CSV file IPC | Race conditions, encoding issues, no real-time capability | ZeroMQ |
| React for this project | Heavier learning curve than Svelte for single developer; more boilerplate for dashboards | SvelteKit |
| SocketRocket (MQL5 WebSocket) | Poorly maintained, limited documentation, not production-ready | ZeroMQ |

## Stack Patterns by Variant

**If GPU is available for training:**
- Install PyTorch with CUDA support from pytorch.org
- Use `device="cuda"` for model training
- Inference can run on CPU (trading models are typically small)

**If no GPU (CPU-only development machine):**
- Install CPU-only PyTorch (`pip install torch --index-url https://download.pytorch.org/whl/cpu`)
- Smaller models only (LSTM/GRU with < 100k parameters)
- Consider scikit-learn models as primary (RF, Gradient Boosting) for faster iteration
- Use cloud GPU (Google Colab free tier) for periodic full training runs

**If reinforcement learning approach is chosen:**
- Add `stable-baselines3` and `gymnasium` dependencies
- Start with PPO (most stable for financial RL)
- Custom trading environment implements gymnasium `Env` interface
- Requires significantly more research time; flag as Phase 3+ not Phase 1

**If only classical ML (no deep learning):**
- Drop PyTorch dependency entirely
- Use scikit-learn + XGBoost/LightGBM as primary models
- Faster iteration, easier debugging, smaller deployment footprint
- Add `xgboost>=2.0` or `lightgbm>=4.0` for gradient boosting

**If deploying on a VPS (cloud hosting):**
- MT5 must run on a Windows VPS (Hetzner, Contabo offer Windows VPS cheaply)
- Python stack runs in Docker on same VPS or separate Linux VPS
- ZeroMQ works over TCP — EA on Windows VPS, Python on Linux VPS is viable
- Use Cloudflare Tunnel for dashboard access instead of exposing ports directly

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| MetaTrader5 | Windows only, Python 3.6-3.14 | **Linux/macOS not supported** — must use Windows for MT5 connection |
| pyzmq | Python 3.8+, all platforms | Bundles libzmq; no separate installation needed |
| FastAPI 0.136+ | Python 3.10+, Pydantic 2.x | Pydantic v1 is NOT compatible with FastAPI 0.100+ |
| PyTorch 2.x | numpy <3 (CPU), various CUDA versions | Check pytorch.org for exact CUDA compatibility |
| stable-baselines3 2.8+ | Python 3.10+, PyTorch 2.x, gymnasium 1.0+ | Not compatible with old `gym` (use `gymnasium`) |
| TA-Lib 0.6.x | numpy 2.x, Python 3.9-3.14 | 0.4.x supports numpy 1.x; 0.5.x is transition; 0.6.x is current |
| SvelteKit 2.x | Node 18+ | Requires modern Node.js |
| SQLAlchemy 2.x | Python 3.10+, asyncio support | Fully async-compatible with FastAPI |
| Pydantic 2.x | Python 3.10+ | Breaking changes from v1; must use v2 with modern FastAPI |

## Critical Architecture Note: Communication Layers

The system has **three distinct communication channels**, each with a purpose:

```
┌─────────────────────────────────────────────────────────────────┐
│ MT5 Terminal (Windows)                                          │
│  ┌──────────────┐                                               │
│  │   MQL5 EA    │──── ZeroMQ (TCP 5555+) ────┐                  │
│  │              │                              │                  │
│  └──────────────┘                              │                  │
│                                                │                  │
│  ┌──────────────┐                              │                  │
│  │  MT5 Python  │──── Direct API call ─────────┼──┐              │
│  │   Package    │                              │  │              │
│  └──────────────┘                              │  │              │
└─────────────────────────────────────────────────┘  │  │           │
                                                     │  │           │
┌─────────────────────────────────────────────────┐  │  │           │
│ Python AI Process                                │  │  │           │
│  ┌──────────────┐    ┌──────────────┐            │  │           │
│  │   AI Models  │    │   Trading    │◄───────────┘  │           │
│  │  (PyTorch/   │───►│   Engine     │◄──────────────┘           │
│  │   sklearn)   │    │              │                            │
│  └──────────────┘    └──────┬───────┘                            │
│                             │                                    │
│  ┌──────────────┐           │  FastAPI                           │
│  │  Data Layer  │           │  (REST + WebSocket)                 │
│  │ (pandas/     │           │                                    │
│  │  TA-Lib)     │           │                                    │
│  └──────────────┘           │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │  PostgreSQL + Redis │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │   SvelteKit Dashboard│
                    │   (WebSocket client) │
                    └────────────────────┘
```

**Channel 1: MT5 Python Package → MT5 Terminal**
- Purpose: Data retrieval (OHLCV, ticks, account info), order execution
- Direction: Python → MT5 (bidirectional but initiated by Python)
- Runs on: Same Windows machine as MT5
- Key functions: `mt5.initialize()`, `mt5.copy_rates_from()`, `mt5.order_send()`, `mt5.account_info()`

**Channel 2: ZeroMQ → MQL5 EA**
- Purpose: Real-time parameter updates from AI → EA
- Direction: Bidirectional (EA sends market events, Python sends parameter updates)
- Pattern: PUB/SUB for market data flow, REQ/REP for parameter commands
- Key advantage: Decoupled — EA keeps running even if Python restarts

**Channel 3: FastAPI WebSocket → Dashboard**
- Purpose: Push real-time updates to browser dashboard
- Direction: Server → Client (with REST for commands to server)
- Pattern: WebSocket for live data, REST for CRUD operations

## Sources

- PyPI MetaTrader5 — verified latest version 5.0.5735 (Apr 2026), Windows-only, Python 3.6-3.14 — HIGH confidence
- PyPI pyzmq — verified latest version 27.1.0 (Sep 2025) — HIGH confidence
- PyPI FastAPI — verified latest version 0.136.1 (Apr 2026) — HIGH confidence
- PyPI uvicorn — verified latest version 0.47.0 (May 2026) — HIGH confidence
- PyPI stable-baselines3 — verified latest version 2.8.0 (Apr 2026) — HIGH confidence
- PyPI TA-Lib — verified latest version 0.6.8 (Oct 2025), now has Windows wheels — HIGH confidence
- MQL5 official docs — verified Python API functions and capabilities — HIGH confidence
- Context7 PyTorch — verified library ID, versions 2.5-2.11+ — HIGH confidence
- MQL5 ZeroMQ bindings — based on community knowledge (mql5-lib/ZMQ headers) — MEDIUM confidence (specific repos change; recommend verifying in phase planning)
- SvelteKit/Svelte ecosystem — based on training data through 2025 — MEDIUM confidence (verify latest version during implementation)

---
*Stack research for: Hybrid AI trading system for MetaTrader 5 with web dashboard*
*Researched: 2026-05-23*