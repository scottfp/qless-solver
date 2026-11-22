# qless-solver

A Python CLI application for solving the Q-Less solitaire dice game by finding valid words from given letter inputs.

## About Q-Less

Q-Less is a solitaire dice game where players attempt to create words using the available letter dice. This solver helps find all possible valid words from a given set of letters.

## Features

- Command-line interface for quick solving
- Accepts string input via argparse
- Validates words against a dictionary (`dictionary.txt` NWL word list)
- Returns valid words from the given letters
- FastAPI + HTMX web interface with dark mode support

### Planned Features

- Complete 2D grid-based crossword solver
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
pip install -e ".[dev]"

# Optional: install OCR dependencies and system packages
pip install -e ".[dev,ocr]"
sudo apt-get update
sudo apt-get install -y tesseract-ocr libgl1 libglib2.0-0

# Option 2: Using uv (faster installation)
# Install uv if you don't have it already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with uv
uv venv -p 3.11
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Optional: include OCR dependencies with uv
uv pip install -e ".[dev,ocr]"
```

## Usage

```bash
# Solve a 12-letter roll and print up to 5 ranked crossword grids
qless-solver --letters "rmtoepngtnxc"

# Show up to 10 solutions with a minimum word length of 4
qless-solver --letters "rmtoepngtnxc" --max-solutions 10 --min-word-length 4

# Generate a random roll
qless-solver --generate

# Show all valid dictionary words formable from the letters
qless-solver --letters "rmtoepngtnxc" --all-words

# For help
qless-solver --help
```

### Generating Candidate Golden Files

To regenerate the thresholded images used by the OCR tests, run the helper
script with an input image and the desired output path:

```bash
python scripts/generate_golden_file.py --input tests/images/input_01.png --output candidate_threshold.png
```

Inspect the generated file and move it into `tests/images` if it should replace
an existing golden image.

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

## Remote Hosting (Fly.io)

To package and deploy the web app on Fly.io (`iad`, `256mb`, `suspend`-on-idle, stateless Docker image), see [docs/deploy-fly.md](docs/deploy-fly.md).

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
- **Dictionary Source**: `dictionary.txt` (NWL word list)
- **Testing**: pytest
- **Web Framework**: FastAPI + HTMX
- **Code Quality**: Black, isort, mypy, ruff, pre-commit
- **Development**: Dev Containers, GitHub Actions
- **Data Validation**: Pydantic for robust data structures and validation
- **Computer Vision/OCR (optional `[ocr]` extra)**: OpenCV, EasyOCR, and Tesseract OCR

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
│       ├── board.py            # 2D Board model, canonicalization, and strict validator
│       ├── cli.py              # Command-line interface
│       ├── dice.py             # Authentic 12-die Q-Less distribution and DiceSet model
│       ├── dictionary.py       # Cached dictionary lookup and bitmask word filtering
│       ├── generator.py        # Random roll generation utility
│       ├── grid_solver.py      # Intersection-aware 2D crossword grid solver
│       ├── image_detection.py  # OCR letter detection stub (Phase 4)
│       └── preprocess.py       # Image adaptive thresholding helper
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── e2e/                    # End-to-end tests
│
├── web/                        # FastAPI + HTMX web interface
│
├── .github/                    # GitHub Actions configuration
├── .devcontainer/              # Dev container configuration
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
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
