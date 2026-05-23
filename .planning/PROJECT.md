# Futra

## What This Is

Futra is a hybrid AI-powered automated trading system for MetaTrader 5. It combines an AI layer (Python) that adapts trading parameters — stop-loss, take-profit, position sizing, trailing stops — based on real-time market conditions, with an MQL5 Expert Advisor bot layer that executes trades on MT5 using those AI-tuned parameters. Built for a single personal account trading forex, indices, and commodities.

## Core Value

Consistent profit with manageable drawdowns — the system must deliver steady returns over time while keeping risk under control. If it can't preserve capital during bad markets, nothing else matters.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] AI model adapts trading parameters (stop-loss, take-profit, position sizing) based on market conditions
- [ ] MQL5 Expert Advisor executes trades on MT5 using AI-tuned parameters
- [ ] System supports multi-asset trading: forex pairs, indices, and commodities
- [ ] Backtesting framework validates strategies against historical data before live deployment
- [ ] Paper trading mode for forward-testing without real capital
- [ ] Risk management: max drawdown limits, position sizing controls, daily loss caps
- [ ] Data pipeline from MT5 to Python AI models and back to EA
- [ ] Dashboard or monitoring to view system performance and AI parameter decisions

### Out of Scope

- Crypto trading — focused on traditional assets only
- Copy trading / signal service for others — personal account only
- Mobile app — desktop-first
- Multiple broker accounts simultaneously — single instance for one account
- High-frequency trading (HFT) — not targeting sub-millisecond execution

## Context

- Developer (Python background) new to trading — system design must include learning about market mechanics, MT5 platform, and trading strategy fundamentals
- MT5 provides historical data and a Python API (MetaTrader5 package) for data access and order management
- MQL5 is MT5's native language for Expert Advisors — different from Python but well-documented
- Hybrid architecture: Python AI process runs alongside MT5, communicating parameters to the EA
- Minimal cost approach: leverage free data (MT5 historical data), open-source ML tools (PyTorch/scikit-learn), and local compute
- Need to validate thoroughly before risking real capital — developer is new to trading

## Constraints

- **Tech Stack**: MQL5 (EA side), Python (AI side) — non-negotiable, MT5 ecosystem requires this split
- **Budget**: Minimal — free/open-source tools, local machine compute, MT5 provided data
- **Experience**: New to trading — system must include proper backtesting and paper trading before live deployment
- **Platform**: MetaTrader 5 desktop — single platform target
- **Scope**: Single personal trading account — no multi-tenant or SaaS requirements

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid AI + Bot architecture | AI adapts parameters dynamically, bot executes reliably — each does what it's best at | — Pending |
| Adaptive parameters over predictive direction | Adapting strategy parameters is more robust than predicting price direction — market regimes change but good risk management persists | — Pending |
| Multi-asset focus (forex, indices, commodities) | Diversification across asset classes reduces correlated risk | — Pending |
| Minimal cost stack | Developer budget is limited; MT5 provides data, Python has mature free ML ecosystem | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-23 after initialization*