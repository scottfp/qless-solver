from __future__ import annotations

import asyncio
import os
import re
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
    from qless_solver.dictionary import (
        DEFAULT_DICTIONARY_NAME,
        Dictionary,
        DictionaryName,
        normalize_dictionary_name,
    )
    from qless_solver.generator import generate_random_roll
    from qless_solver.grid_solver import Grid, GridSolution, solve_qless_grid
    from qless_solver.image_detection import detect_letters
except ImportError as e:
    print(f"Error importing solver modules: {e}")
    DEFAULT_DICTIONARY_NAME = "full"  # type: ignore[assignment]
    Dictionary = None  # type: ignore[assignment,misc]
    DictionaryName = str  # type: ignore[assignment,misc]
    normalize_dictionary_name = None  # type: ignore[assignment]
    generate_random_roll = None  # type: ignore[assignment]
    solve_qless_grid = None  # type: ignore[assignment]
    GridSolution = None  # type: ignore[assignment,misc]
    Grid = None  # type: ignore[assignment,misc]
    detect_letters = None  # type: ignore[assignment]

_DICTIONARY_INSTANCE: Optional[Dictionary] = None
DICTIONARY_LABELS: dict[str, str] = {
    "full": "Full Scrabble",
    "common": "Common English",
}


def get_dictionary(
    mode: DictionaryName = DEFAULT_DICTIONARY_NAME,
) -> Optional[Dictionary]:
    """Return a shared zero-copy Dictionary view for web requests."""
    global _DICTIONARY_INSTANCE
    if Dictionary is None:
        return None
    if _DICTIONARY_INSTANCE is None:
        _DICTIONARY_INSTANCE = Dictionary(mode=DEFAULT_DICTIONARY_NAME)
        # Warm the unified bitmask index once so subsequent solves stay fast
        _DICTIONARY_INSTANCE.get_valid_words("rmtoepngtnxc")
    return _DICTIONARY_INSTANCE.with_mode(mode)


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
    excluded_words: list[str] = Field(default_factory=list)
    dictionary: DictionaryName = DEFAULT_DICTIONARY_NAME


def _resolve_form_dictionary(
    raw_dictionary: str,
) -> tuple[DictionaryName, Optional[str]]:
    if normalize_dictionary_name is None:
        return DEFAULT_DICTIONARY_NAME, None
    try:
        return normalize_dictionary_name(raw_dictionary), None
    except ValueError as exc:
        return DEFAULT_DICTIONARY_NAME, str(exc)


def parse_excluded_words(raw: Optional[str | list[str]]) -> list[str]:
    """Normalize comma/whitespace-separated or list-based excluded words."""
    if not raw:
        return []
    items = [raw] if isinstance(raw, str) else raw
    excluded: list[str] = []
    seen: set[str] = set()
    for item in items:
        for token in re.split(r"[,\s]+", item.strip().lower()):
            if token and token.isascii() and token.isalpha() and token not in seen:
                seen.add(token)
                excluded.append(token)
    return excluded


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


def _build_word_entries(
    sol: GridSolution, board_words: list[str], definitions: dict[str, Optional[str]]
) -> list[dict[str, object]]:
    """Pair each solution word with its definition and normalized tile coordinates."""
    runs: dict[str, list[list[list[int]]]] = {}
    board = sol.to_board().normalize()
    for run in sorted(
        board.extract_runs(min_length=2), key=lambda r: (r.y, r.x, r.direction)
    ):
        runs.setdefault(run.word.upper(), []).append([[x, y] for x, y in run.cells()])
    entries: list[dict[str, object]] = []
    for word in board_words:
        matches = runs.get(word)
        cells = matches.pop(0) if matches else []
        entries.append(
            {"word": word, "definition": definitions.get(word), "cells": cells}
        )
    return entries


def _serialize_solutions(
    solutions: list[GridSolution], dictionary: Optional[Dictionary] = None
) -> list[dict[str, object]]:
    """Serialize solved grids into JSON-safe row arrays and metadata for the UI carousel."""
    all_words = {pw.word.upper() for sol in solutions for pw in sol.grid.words}
    definitions: dict[str, Optional[str]] = (
        dictionary.get_definitions(sorted(all_words)) if dictionary else {}
    )
    serialized: list[dict[str, object]] = []
    for sol in solutions:
        board = sol.to_board()
        width, height = board.dimensions()
        words = [pw.word.upper() for pw in sol.grid.words]
        serialized.append(
            {
                "rows": board.to_rows(),
                "words": words,
                "word_entries": _build_word_entries(sol, words, definitions),
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
    full_dict = get_dictionary("full")
    common_dict = get_dictionary("common")
    if full_dict is None or common_dict is None or not full_dict.words:
        raise HTTPException(status_code=503, detail="Dictionary unavailable")
    full_count = len(full_dict)
    common_count = len(common_dict)
    return JSONResponse(
        {
            "status": "ok",
            "dictionary_words": full_count,
            "dictionaries": {
                "full": full_count,
                "common": common_count,
            },
        }
    )


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
    excluded_words: str = Form(""),
    dictionary: str = Form(DEFAULT_DICTIONARY_NAME),
) -> HTMLResponse:
    """Endpoint for HTMX form submission returning an interactive HTML results snippet."""
    if solve_qless_grid is None:
        return HTMLResponse(
            "<div class='error'>Solver is not available due to an import error.</div>",
            status_code=500,
        )

    cleaned, validation_error = validate_letter_input(letters, min_word_length)
    dict_mode, dict_error = _resolve_form_dictionary(dictionary)
    clamped_max = max(1, min(max_solutions, 50))
    excluded = parse_excluded_words(excluded_words)
    solutions: list[GridSolution] = []
    error_message = validation_error or dict_error
    active_dict = get_dictionary(dict_mode) if error_message is None else None

    if error_message is None:
        try:
            solutions = await asyncio.to_thread(
                solve_qless_grid,
                letters=cleaned,
                min_word_length=min_word_length,
                dictionary=active_dict,
                max_solutions=clamped_max,
                timeout_seconds=3.0,
                excluded_words=excluded or None,
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
            "serialized_solutions": await asyncio.to_thread(
                _serialize_solutions, solutions, active_dict
            ),
            "error_message": error_message,
            "info_message": None,
            "letters_submitted": cleaned,
            "min_word_length_submitted": min_word_length,
            "excluded_words_submitted": [w.upper() for w in excluded],
            "dictionary_submitted": dict_mode,
            "dictionary_label": DICTIONARY_LABELS.get(dict_mode, dict_mode.title()),
        },
    )


@app.post("/solve-image/", response_class=HTMLResponse)
async def solve_letters_image(
    request: Request,
    image: UploadFile = File(...),
    min_word_length: int = Form(3),
    dictionary: str = Form(DEFAULT_DICTIONARY_NAME),
) -> HTMLResponse:
    """Handle image upload, detect letters, and return solutions."""
    if solve_qless_grid is None or detect_letters is None:
        return HTMLResponse(
            "<div class='error'>Solver or detection unavailable.</div>",
            status_code=500,
        )

    dict_mode, dict_error = _resolve_form_dictionary(dictionary)
    content = await image.read()
    detected = detect_letters(content)

    if not detected:
        return templates.TemplateResponse(
            request,
            "results_snippet.html",
            {
                "solutions": [],
                "serialized_solutions": [],
                "error_message": dict_error,
                "info_message": (
                    None
                    if dict_error
                    else (
                        "Automatic photo letter detection is not implemented yet. "
                        "Please enter your 12 rolled letters manually above."
                    )
                ),
                "letters_submitted": "",
                "min_word_length_submitted": min_word_length,
                "excluded_words_submitted": [],
                "dictionary_submitted": dict_mode,
                "dictionary_label": DICTIONARY_LABELS.get(dict_mode, dict_mode.title()),
            },
        )

    cleaned, validation_error = validate_letter_input(detected, min_word_length)
    solutions: list[GridSolution] = []
    error_message = validation_error or dict_error
    active_dict = get_dictionary(dict_mode) if error_message is None else None

    if error_message is None:
        try:
            solutions = await asyncio.to_thread(
                solve_qless_grid,
                letters=cleaned,
                min_word_length=min_word_length,
                dictionary=active_dict,
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
            "serialized_solutions": await asyncio.to_thread(
                _serialize_solutions, solutions, active_dict
            ),
            "error_message": error_message,
            "info_message": None,
            "letters_submitted": cleaned,
            "min_word_length_submitted": min_word_length,
            "excluded_words_submitted": [],
            "dictionary_submitted": dict_mode,
            "dictionary_label": DICTIONARY_LABELS.get(dict_mode, dict_mode.title()),
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

    excluded = parse_excluded_words(request_body.excluded_words)
    active_dict = get_dictionary(request_body.dictionary)

    try:
        return await asyncio.to_thread(
            solve_qless_grid,
            letters=cleaned,
            min_word_length=request_body.min_word_length,
            dictionary=active_dict,
            max_solutions=request_body.max_solutions,
            timeout_seconds=3.0,
            excluded_words=excluded or None,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Dictionary file not found: {e}")
    except Exception as e:
        print(f"Error during API solving: {e}")
        raise HTTPException(
            status_code=500, detail=f"An error occurred during solving: {e!s}"
        )


@app.get("/api/define/{word}", tags=["API"])
async def define_word_api(word: str) -> JSONResponse:
    """Look up the dictionary definition for a single word."""
    cleaned = word.strip()
    if not cleaned or not (cleaned.isascii() and cleaned.isalpha()):
        raise HTTPException(
            status_code=422, detail="Word must contain only letters (A-Z)."
        )
    dictionary = get_dictionary("full")
    if dictionary is None:
        raise HTTPException(status_code=503, detail="Dictionary unavailable")
    definition = await asyncio.to_thread(dictionary.get_definition, cleaned)
    if definition is None:
        raise HTTPException(
            status_code=404, detail=f"No definition found for '{cleaned.upper()}'."
        )
    return JSONResponse({"word": cleaned.upper(), "definition": definition})


# To run (from project root):
# python -m uvicorn web.main:app --reload
