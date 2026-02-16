# Contributing to ACE

First off, thank you for considering contributing to the Autonomous Content Engine!

## Architecture Philosophy

ACE is built on a distributed microservices model. Before submitting PRs, please understand:
1.  **Immutability**: Containers should be stateless where possible.
2.  **Strict Typing**: All new Python code must use `typing` hints and pass `mypy` checks.
3.  **Resilience**: New integrations must have a fallback strategy (Circuit Breaker pattern).

## Development Workflow

1.  **Fork** the repository.
2.  **Create** a branch: `git checkout -b feature/amazing-feature`.
3.  **Test**: Ensure `python run_daily_batch.py` completes a full cycle.
4.  **Commit**: Use conventional commits (e.g., `feat: add new voice synthesis module`).
5.  **Push**: `git push origin feature/amazing-feature`.
6.  **Open** a Pull Request.

## Coding Standards

- **Python**: Follow PEP 8.
- **Docker**: Minimize layer count; use multi-stage builds.
- **Documentation**: Update `README.md` if architectural changes are made.

---
*By contributing, you agree that your code will be licensed under the MIT License.*
