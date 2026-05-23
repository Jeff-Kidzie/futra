# AGENTS.md

<!-- GSD:project-start source:PROJECT.md -->
## Project

Futra is a hybrid AI-powered automated trading system for MetaTrader 5 with a web interface. An AI layer (Python) adapts trading parameters — stop-loss, take-profit, position sizing — based on real-time market conditions, while an MQL5 Expert Advisor executes trades on MT5 using those AI-tuned parameters. A web dashboard provides monitoring of system performance, AI parameter decisions, and trade history from anywhere. The platform evolves over time from a monitoring dashboard toward a full web trading platform with manual trading, charts, and AI controls.

**Core Value:** Consistent profit with manageable drawdowns — the system must deliver steady returns while keeping risk under control.

**Key Constraint:** Test-Driven Development (TDD) — all code must be built with tests first and must be testable locally.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

**EA Side:** MQL5 (MetaTrader 5 Expert Advisor)
**AI Side:** Python — scikit-learn for regime detection, PyTorch for future deep learning
**Data:** MetaTrader5 Python package, pandas, numpy, TA-Lib
**IPC:** File-based (DWX Connect pattern) between EA and Python
**Web Backend:** FastAPI + WebSocket for real-time updates
**Web Frontend:** SvelteKit + Tailwind CSS
**Database:** SQLite (single-user, WAL mode for concurrent reads)
**Testing:** pytest (Python), MQL5 Test Framework
**Deployment:** Windows VPS (MT5 requires Windows)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- Test-Driven Development: write tests first, then implement
- All components must be testable locally without live MT5 connection (use mocks/fakes)
- EA (MQL5) uses hardcoded safe defaults when AI is unavailable
- File-based IPC for EA ↔ Python communication (DWX Connect pattern)
- Python AI process is advisory; EA is the execution authority
- Financial calculations use decimal precision appropriate to each symbol
- Error handling wraps all MT5 API calls (returns None on failure)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Not yet mapped. Will populate after Phase 1 development establishes patterns.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` — do not edit manually.
<!-- GSD:profile-end -->