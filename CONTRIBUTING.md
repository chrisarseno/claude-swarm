# Contributing to Claude Swarm

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

### Prerequisites

- Python >=3.10
- Git

### Setup

1. **Fork** the repository on GitHub
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/claude-swarm.git
   cd claude-swarm
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
5. **Copy environment config**:
   ```bash
   cp .env.example .env
   ```

## Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Run the test suite:
   ```bash
   PYTHONPATH=src python -m pytest tests/ -v
   ```
4. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   git commit -m "feat: add new feature"
   ```
5. Push to your fork and open a Pull Request

### Commit Message Format

- `feat:` � New feature
- `fix:` � Bug fix
- `docs:` � Documentation only
- `test:` � Adding or updating tests
- `refactor:` � Code change that neither fixes a bug nor adds a feature
- `chore:` � Maintenance tasks

## Code Style

- Format with [black](https://github.com/psf/black)
- Lint with [ruff](https://github.com/astral-sh/ruff)

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Keep PRs focused � one feature or fix per PR
4. Write a clear description of what changed and why

## Reporting Issues

- Use GitHub Issues to report bugs or request features
- Include steps to reproduce for bug reports
- Check existing issues before opening a new one

## License

By contributing, you agree that your contributions will be licensed under the [AGPL-3.0 License](LICENSE).
