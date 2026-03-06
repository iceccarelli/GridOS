# Contributing to GridOS

Thank you for your interest in contributing to GridOS! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Issues

- Use [GitHub Issues](https://github.com/your-org/GridOS/issues) to report bugs or request features
- Search existing issues before creating a new one
- Include steps to reproduce, expected behaviour, and actual behaviour for bugs
- Include your environment details (OS, Python version, GridOS version)

### Submitting Changes

1. **Fork** the repository
2. **Create a branch** from `develop`:
   ```bash
   git checkout -b feature/your-feature-name develop
   ```
3. **Make your changes** following the coding standards below
4. **Write tests** for new functionality
5. **Run the test suite**:
   ```bash
   pytest tests/ -v --cov=gridos
   ```
6. **Run linting**:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   ```
7. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add support for SunSpec protocol adapter"
   ```
8. **Push** and create a **Pull Request** against `develop`

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Description |
|--------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `test:` | Adding or updating tests |
| `refactor:` | Code refactoring |
| `perf:` | Performance improvement |
| `ci:` | CI/CD changes |
| `chore:` | Maintenance tasks |

### Coding Standards

- **Python 3.10+** with type hints on all public functions
- **Pydantic v2** for data models
- **async/await** for all I/O operations
- **Ruff** for linting and formatting
- **pytest** for testing with >80% coverage target
- **Docstrings** in NumPy style for all public classes and functions
- **Logging** via `logging.getLogger(__name__)` — no `print()` statements

### Adding a New Protocol Adapter

1. Create `src/gridos/adapters/your_protocol.py`
2. Inherit from `BaseAdapter`
3. Implement `connect()`, `disconnect()`, `read_telemetry()`, `write_command()`
4. Add tests in `tests/test_adapters.py`
5. Update `src/gridos/adapters/__init__.py`
6. Document in `docs/architecture.md`

### Adding a New Physics Model

1. Create `src/gridos/digital_twin/models/your_component.py`
2. Implement `update(dt, grid_state)` method
3. Register in `GridModel` class
4. Add tests in `tests/test_digital_twin.py`

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/GridOS.git
cd GridOS

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/
```

## Questions?

Open a [Discussion](https://github.com/your-org/GridOS/discussions) or reach out to the maintainers.
