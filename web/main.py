from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict # Added Dict
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from cli.qless_solver.grid_solver import solve_qless_grid, GridSolution, Grid # Added Grid
    from cli.qless_solver.dictionary import Dictionary # To handle potential init errors
except ImportError as e:
    print(f"Error importing solver modules: {e}")
    # Handle as appropriate, e.g. by disabling features or raising an error at startup
    solve_qless_grid = None # Make it None if import fails
    GridSolution = None
    Grid = None


app = FastAPI(title="Q-less Solver UI & API")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

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
async def solve_letters_htmx(request: Request, letters: str = Form(...), min_word_length: int = Form(3)):
    """
    Endpoint for HTMX form submission.
    Accepts letters and min_word_length from form data.
    Returns an HTML snippet with the solutions.
    """
    if solve_qless_grid is None:
        return HTMLResponse("<div class='error'>Solver is not available due to an import error.</div>", status_code=500)

    solutions: List[GridSolution] = []
    error_message = None
    try:
        solutions = solve_qless_grid(
            letters=letters,
            min_word_length=min_word_length
        )
    except FileNotFoundError as e:
        error_message = f"Dictionary file not found: {e}"
        print(error_message) # Log it
    except Exception as e:
        error_message = f"An error occurred during solving: {str(e)}"
        print(error_message) # Log it

    # Render an HTML snippet template with the solutions or error
    return templates.TemplateResponse("results_snippet.html", {
        "request": request,
        "solutions": solutions,
        "error_message": error_message,
        "letters_submitted": letters,
        "min_word_length_submitted": min_word_length
    })


# Optional: Keep the JSON API endpoint if direct API access is also desired
@app.post("/api/solve/", response_model=List[GridSolution], tags=["API"])
async def solve_letters_api(request_body: SolveRequestBody) -> List[GridSolution]:
    """
    JSON API endpoint. Accepts a string of letters and an optional minimum word length.
    Returns a list of possible grid solutions.
    """
    if solve_qless_grid is None:
        raise HTTPException(status_code=500, detail="Solver function not available due to an import error.")
    try:
        solutions = solve_qless_grid(
            letters=request_body.letters,
            min_word_length=request_body.min_word_length
        )
        return solutions
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Dictionary file not found: {e}")
    except Exception as e:
        print(f"Error during API solving: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during solving: {str(e)}")


# To run (from project root):
# python -m uvicorn web.main:app --reload
