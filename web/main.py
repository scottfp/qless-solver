import os
import sys
from typing import List  # Added Dict

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add the cli directory to the Python path so qless_solver package is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cli_path = os.path.join(project_root, "cli")
if cli_path not in sys.path:
    sys.path.insert(0, cli_path)

try:
    from qless_solver.grid_solver import Grid, GridSolution, solve_qless_grid
    from qless_solver.image_detection import detect_letters
except ImportError as e:
    print(f"Error importing solver modules: {e}")
    # Handle as appropriate, e.g. by disabling features or raising an error at startup
    solve_qless_grid = None
    GridSolution = None
    Grid = None
    detect_letters = None


app = FastAPI(title="Q-less Solver UI & API")

# Setup Jinja2 templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


# This model is for the JSON API, which we might keep for programmatic access
class SolveRequestBody(BaseModel):
    letters: str
    min_word_length: int = 3


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})


# This is the endpoint HTMX will call. It needs to return an HTML snippet.
@app.post("/solve-htmx/", response_class=HTMLResponse)
async def solve_letters_htmx(
    request: Request, letters: str = Form(...), min_word_length: int = Form(3)
):
    """
    Endpoint for HTMX form submission.
    Accepts letters and min_word_length from form data.
    Returns an HTML snippet with the solutions.
    """
    letters = letters.strip()
    if solve_qless_grid is None:
        error_message = "Solver is not available due to an import error."
        return templates.TemplateResponse(
            "results_snippet.html",
            {
                "request": request,
                "solutions": [],
                "error_message": error_message,
                "letters_submitted": letters,
                "min_word_length_submitted": min_word_length,
            },
        )
    solutions: List[GridSolution] = []
    error_message = None

    if len(letters) != 12 or not letters.isalpha():
        error_message = "Please enter exactly 12 alphabetic letters."
    else:
        try:
            solutions = solve_qless_grid(
                letters=letters, min_word_length=min_word_length
            )
        except FileNotFoundError as e:
            error_message = f"Dictionary file not found: {e}"
            print(error_message)  # Log it
        except Exception as e:
            error_message = f"An error occurred during solving: {str(e)}"
            print(error_message)  # Log it

    # Render an HTML snippet template with the solutions or error
    return templates.TemplateResponse(
        "results_snippet.html",
        {
            "request": request,
            "solutions": solutions,
            "error_message": error_message,
            "letters_submitted": letters,
            "min_word_length_submitted": min_word_length,
        },
    )


@app.post("/solve-image/", response_class=HTMLResponse)
async def solve_letters_image(
    request: Request,
    image: UploadFile = File(...),
    min_word_length: int = Form(3),
):
    """Handle image upload, detect letters, and return solutions."""
    if solve_qless_grid is None or detect_letters is None:
        error_message = "Solver or detection unavailable."
        return templates.TemplateResponse(
            "results_snippet.html",
            {
                "request": request,
                "solutions": [],
                "error_message": error_message,
                "letters_submitted": "",
                "min_word_length_submitted": min_word_length,
            },
        )

    content = await image.read()
    detected = detect_letters(content)

    solutions: List[GridSolution] = []
    error_message = None
    if len(detected) != 12 or not detected.isalpha():
        error_message = "Detected letters were not exactly 12 alphabetic characters."
    else:
        try:
            solutions = solve_qless_grid(
                letters=detected,
                min_word_length=min_word_length,
            )
        except FileNotFoundError as e:
            error_message = f"Dictionary file not found: {e}"
            print(error_message)
        except Exception as e:
            error_message = f"An error occurred during solving: {str(e)}"
            print(error_message)
    # Render an HTML snippet template with the solutions or error
    return templates.TemplateResponse(
        "results_snippet.html",
        {
            "request": request,
            "solutions": solutions,
            "error_message": error_message,
            "letters_submitted": detected,
            "min_word_length_submitted": min_word_length,
        },
    )


# Optional: Keep the JSON API endpoint if direct API access is also desired
@app.post("/api/solve/", response_model=List[GridSolution], tags=["API"])
async def solve_letters_api(request_body: SolveRequestBody) -> List[GridSolution]:
    """
    JSON API endpoint. Accepts a string of letters and an optional minimum word length.
    Returns a list of possible grid solutions.
    """
    if solve_qless_grid is None:
        raise HTTPException(
            status_code=500,
            detail="Solver function not available due to an import error.",
        )
    letters = request_body.letters.strip()
    if len(letters) != 12 or not letters.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Letters must be exactly 12 alphabetic characters.",
        )
    try:
        solutions = solve_qless_grid(
            letters=letters, min_word_length=request_body.min_word_length
        )
        return solutions
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Dictionary file not found: {e}")
    except Exception as e:
        print(f"Error during API solving: {e}")
        raise HTTPException(
            status_code=500, detail=f"An error occurred during solving: {str(e)}"
        )


# To run (from project root):
# python -m uvicorn web.main:app --reload
