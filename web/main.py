from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Add the cli directory to the Python path so qless_solver package is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cli_path = os.path.join(project_root, "cli")
if cli_path not in sys.path:
    sys.path.insert(0, cli_path)

try:
    from qless_solver.dictionary import Dictionary
    from qless_solver.generator import generate_random_roll
    from qless_solver.grid_solver import Grid, GridSolution, solve_qless_grid
    from qless_solver.image_detection import detect_letters
except ImportError as e:
    print(f"Error importing solver modules: {e}")
    Dictionary = None  # type: ignore[assignment,misc]
    generate_random_roll = None  # type: ignore[assignment]
    solve_qless_grid = None  # type: ignore[assignment]
    GridSolution = None  # type: ignore[assignment,misc]
    Grid = None  # type: ignore[assignment,misc]
    detect_letters = None  # type: ignore[assignment]

_DICTIONARY_INSTANCE: Optional[Dictionary] = None


def get_dictionary() -> Optional[Dictionary]:
    """Return a shared cached Dictionary instance for web requests."""
    global _DICTIONARY_INSTANCE
    if Dictionary is None:
        return None
    if _DICTIONARY_INSTANCE is None:
        _DICTIONARY_INSTANCE = Dictionary()
        # Warm the bitmask index once so subsequent solves stay fast
        _DICTIONARY_INSTANCE.get_valid_words("rmtoepngtnxc")
    return _DICTIONARY_INSTANCE


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Warm the shared dictionary and bitmask index on startup."""
    get_dictionary()
    yield


app = FastAPI(title="Q-less Solver UI & API", lifespan=lifespan)

# Setup Jinja2 templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


class SolveRequestBody(BaseModel):
    letters: str
    min_word_length: int = 3
    max_solutions: int = Field(default=10, ge=1, le=50)


def validate_letter_input(
    letters: str, min_word_length: int = 3
) -> tuple[str, Optional[str]]:
    """Validate and normalize rolled dice letters and minimum word length."""
    cleaned = letters.strip().lower()
    if not cleaned or not (cleaned.isascii() and cleaned.isalpha()):
        return cleaned, "Please enter letters only (A-Z)."
    if len(cleaned) != 12:
        return cleaned, f"Expected exactly 12 letters, got {len(cleaned)}."
    if min_word_length < 2 or min_word_length > 12:
        return cleaned, "Minimum word length must be between 2 and 12."
    return cleaned, None


def _serialize_solutions(solutions: list[GridSolution]) -> list[dict[str, object]]:
    """Serialize solved grids into JSON-safe row arrays and metadata for the UI carousel."""
    serialized: list[dict[str, object]] = []
    for sol in solutions:
        board = sol.to_board()
        width, height = board.dimensions()
        words = [pw.word.upper() for pw in sol.grid.words]
        serialized.append(
            {
                "rows": board.to_rows(),
                "words": words,
                "word_count": len(words),
                "dimensions": f"{width}x{height}",
            }
        )
    return serialized


@app.get("/healthz", tags=["Health"])
async def healthz() -> JSONResponse:
    """Health check endpoint verifying solver and dictionary readiness."""
    if solve_qless_grid is None:
        raise HTTPException(status_code=503, detail="Solver unavailable")
    dictionary = get_dictionary()
    if dictionary is None or not dictionary.words:
        raise HTTPException(status_code=503, detail="Dictionary unavailable")
    return JSONResponse({"status": "ok", "dictionary_words": len(dictionary.words)})


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request) -> HTMLResponse:
    """Serves the main HTML page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/roll/", tags=["API"])
async def roll_dice_endpoint() -> JSONResponse:
    """Generate a random 12-letter roll using the authentic Q-Less dice distribution."""
    if generate_random_roll is None:
        raise HTTPException(
            status_code=500, detail="Dice generator not available due to import error."
        )
    return JSONResponse({"letters": generate_random_roll().lower()})


@app.post("/solve-htmx/", response_class=HTMLResponse)
async def solve_letters_htmx(
    request: Request,
    letters: str = Form(...),
    min_word_length: int = Form(3),
    max_solutions: int = Form(10),
) -> HTMLResponse:
    """Endpoint for HTMX form submission returning an interactive HTML results snippet."""
    if solve_qless_grid is None:
        return HTMLResponse(
            "<div class='error'>Solver is not available due to an import error.</div>",
            status_code=500,
        )

    cleaned, validation_error = validate_letter_input(letters, min_word_length)
    clamped_max = max(1, min(max_solutions, 50))
    solutions: list[GridSolution] = []
    error_message = validation_error

    if error_message is None:
        try:
            solutions = await asyncio.to_thread(
                solve_qless_grid,
                letters=cleaned,
                min_word_length=min_word_length,
                dictionary=get_dictionary(),
                max_solutions=clamped_max,
                timeout_seconds=3.0,
            )
        except FileNotFoundError as e:
            error_message = f"Dictionary file not found: {e}"
            print(error_message)
        except Exception as e:
            error_message = f"An error occurred during solving: {e!s}"
            print(error_message)

    return templates.TemplateResponse(
        request,
        "results_snippet.html",
        {
            "solutions": solutions,
            "serialized_solutions": _serialize_solutions(solutions),
            "error_message": error_message,
            "info_message": None,
            "letters_submitted": cleaned,
            "min_word_length_submitted": min_word_length,
        },
    )


@app.post("/solve-image/", response_class=HTMLResponse)
async def solve_letters_image(
    request: Request,
    image: UploadFile = File(...),
    min_word_length: int = Form(3),
) -> HTMLResponse:
    """Handle image upload, detect letters, and return solutions."""
    if solve_qless_grid is None or detect_letters is None:
        return HTMLResponse(
            "<div class='error'>Solver or detection unavailable.</div>",
            status_code=500,
        )

    content = await image.read()
    detected = detect_letters(content)

    if not detected:
        return templates.TemplateResponse(
            request,
            "results_snippet.html",
            {
                "solutions": [],
                "serialized_solutions": [],
                "error_message": None,
                "info_message": (
                    "Automatic photo letter detection is not implemented yet. "
                    "Please enter your 12 rolled letters manually above."
                ),
                "letters_submitted": "",
                "min_word_length_submitted": min_word_length,
            },
        )

    cleaned, validation_error = validate_letter_input(detected, min_word_length)
    solutions: list[GridSolution] = []
    error_message = validation_error

    if error_message is None:
        try:
            solutions = await asyncio.to_thread(
                solve_qless_grid,
                letters=cleaned,
                min_word_length=min_word_length,
                dictionary=get_dictionary(),
                max_solutions=10,
                timeout_seconds=3.0,
            )
        except FileNotFoundError as e:
            error_message = f"Dictionary file not found: {e}"
            print(error_message)
        except Exception as e:
            error_message = f"An error occurred during solving: {e!s}"
            print(error_message)

    return templates.TemplateResponse(
        request,
        "results_snippet.html",
        {
            "solutions": solutions,
            "serialized_solutions": _serialize_solutions(solutions),
            "error_message": error_message,
            "info_message": None,
            "letters_submitted": cleaned,
            "min_word_length_submitted": min_word_length,
        },
    )


@app.post("/api/solve/", response_model=list[GridSolution], tags=["API"])
async def solve_letters_api(request_body: SolveRequestBody) -> list[GridSolution]:
    """
    JSON API endpoint. Accepts 12 rolled letters and optional constraints.
    Returns a list of valid grid solutions.
    """
    if solve_qless_grid is None:
        raise HTTPException(
            status_code=500,
            detail="Solver function not available due to an import error.",
        )

    cleaned, validation_error = validate_letter_input(
        request_body.letters, request_body.min_word_length
    )
    if validation_error is not None:
        raise HTTPException(status_code=422, detail=validation_error)

    try:
        return await asyncio.to_thread(
            solve_qless_grid,
            letters=cleaned,
            min_word_length=request_body.min_word_length,
            dictionary=get_dictionary(),
            max_solutions=request_body.max_solutions,
            timeout_seconds=3.0,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Dictionary file not found: {e}")
    except Exception as e:
        print(f"Error during API solving: {e}")
        raise HTTPException(
            status_code=500, detail=f"An error occurred during solving: {e!s}"
        )


# To run (from project root):
# python -m uvicorn web.main:app --reload
