# qless-solver

A Python CLI application for solving the Q-Less solitaire dice game by finding valid words from given letter inputs.

## About Q-Less

Q-Less is a solitaire dice game where players attempt to create words using the available letter dice. This solver helps find all possible valid words from a given set of letters.

## Features

- Command-line interface for quick solving
- Accepts string input via argparse
- Validates words against a dictionary (Merriam-Webster)
- Returns all possible valid words from the given letters

### Planned Features

- Simple web interface using FastAPI + HTMX (Phase 2)
- Computer vision to detect letters from a photo of the game (Future)

## Installation

```bash
# Clone the repository
git clone https://github.com/username/qless-solver.git
cd qless-solver

# Set up a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Usage

```bash
# Basic usage
qless-solver --letters "abcdefghijkl"

# Generate a random roll
qless-solver --generate

# Show all possible words
qless-solver --letters "abcdefghijkl" --all-words

# For help
qless-solver --help
```

## Development

### Using Dev Containers

This project supports development using [VS Code Dev Containers](https://code.visualstudio.com/docs/remote/containers). To use:

1. Install Docker and the VS Code Remote - Containers extension
2. Open the project folder in VS Code
3. When prompted, click "Reopen in Container"
   - Or use the command palette: "Remote-Containers: Reopen in Container"
4. VS Code will build the container and set up the development environment automatically

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. To set up:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

The hooks will run automatically on git commit. You can also run them manually:

```bash
pre-commit run --all-files
```

## Technical Notes

### Technology Stack

- **Python**: Latest stable version (3.12+)
- **Dictionary Source**: TBD (Evaluating options)
- **Testing**: pytest
- **Web Framework**: FastAPI + HTMX (Phase 2)
- **Code Quality**: Black, isort, mypy, ruff, pre-commit
- **Development**: Dev Containers, GitHub Actions
- **Data Validation**: Pydantic for robust data structures and validation

### Development Practices

- **Code Organization**: Functional approach with modules containing data structures and supporting functions
- **Testing**:
  - Unit tests for all core functionality
  - End-to-end tests to verify full application flow
  - Test fixtures for common input patterns
- **Type Hints**: Comprehensive type annotations
- **Documentation**: Docstrings following Google style guidelines
- **CI/CD**: GitHub Actions for automated testing and linting

### Project Structure

```
qless-solver/
│
├── cli/
│   └── qless_solver/
│       ├── __init__.py
│       ├── cli.py          # Command-line interface
│       ├── solver.py       # Core solving logic
│       ├── dictionary.py   # Dictionary lookup functionality
│       └── generator.py    # Input string generation utility
│
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── e2e/                # End-to-end tests
│
├── web/                    # Future web interface (Phase 2)
│
├── .github/                # GitHub Actions configuration
├── .devcontainer/          # Dev container configuration
├── .pre-commit-config.yaml # Pre-commit hooks configuration
├── README.md
├── LICENSE
├── pyproject.toml
└── .gitignore
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Scott Pritchard
