# Contributing to OpenWorld

Thank you for your interest in contributing to OpenWorld.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Set up the development environment (see `docs/development.md`)
4. Create a feature branch
5. Make your changes
6. Run tests and linting
7. Submit a pull request

## Development Setup

```bash
# Backend
pip install -e ".[dev]"
uvicorn apps.api.main:app --reload

# Frontend
cd apps/web && npm install && npm run dev

# Tests
pytest tests/ -v
ruff check core/ apps/ packages/ tests/
```

## Code Standards

- Python: Ruff for linting, type hints encouraged
- TypeScript: ESLint + Prettier
- Write tests for new functionality
- Keep commits focused and descriptive
- No secrets in code

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Fill out the PR template
4. Request review

## Code of Conduct

Be respectful, constructive, and professional in all interactions.
