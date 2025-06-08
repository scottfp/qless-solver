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

# Option 1: Using traditional pip (standard)
# Set up a Python 3.11+ virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install dependencies for development and testing
pip install -e .[dev]

# Option 2: Using uv (faster installation)
# Install uv if you don't have it already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with uv
uv venv -p 3.11
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
uv pip install -e .[dev]
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

## Running the Web UI

The Q-less Solver includes a web-based user interface built with FastAPI and HTMX. To run it locally:

1.  **Ensure Dependencies are Installed**:
    Use Python 3.11 or newer when creating your virtual environment. After activating it, install the project dependencies:
    ```bash
    pip install -e .[dev]
    ```

2.  **Run the FastAPI Application**:
    From the root directory of the project, execute the following command:
    ```bash
    python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
    ```
    - `--reload`: Enables auto-reload so the server restarts when code changes are detected (useful for development).
    - `--host 0.0.0.0`: Makes the server accessible from your local network.
    - `--port 8000`: Specifies the port number.

3.  **Access the UI**:
    Open your web browser and navigate to:
    [http://localhost:8000](http://localhost:8000)

    You should see the Q-less Solver interface where you can input letters and see potential solutions.

4.  **Capture a Photo**:
    The page provides a *Capture & Solve* form that uses your device's camera (or allows uploading an image) to detect letters automatically.

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

- **Python**: Latest stable version (3.11+)
- **Dictionary Source**: TBD (Evaluating options)
- **Testing**: pytest
- **Web Framework**: FastAPI + HTMX (Phase 2)
- **Code Quality**: Black, isort, mypy, ruff, pre-commit
- **Development**: Dev Containers, GitHub Actions
- **Data Validation**: Pydantic for robust data structures and validation

### Development Practices

- **Code Organization**: Functional approach with modules containing data structures and supporting functions
- **Branch-Based Development**: All changes should be made in feature branches, not directly on the main branch
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
