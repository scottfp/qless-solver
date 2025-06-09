import os
import sys
from collections import Counter  # Import Counter for mock solution

import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path to allow importing web.main
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the app from web.main
# This might fail if web.main has issues at import time (e.g. dictionary not found)
try:
    from web.main import app
except ImportError as e:
    print(f"Skipping web API tests: Could not import FastAPI app from web.main: {e}")
    # Define a placeholder app or skip tests if app import fails
    app = None
except Exception as e:
    print(f"An unexpected error occurred during app import for tests: {e}")
    app = None


@pytest.fixture(scope="module")
def client():
    if app is None:
        pytest.skip("FastAPI app not available for testing.")
    # Create a TestClient instance using the FastAPI app
    with TestClient(app) as c:
        yield c


def test_read_root_html(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "<title>Q-less Solver</title>" in response.text


# Test for the JSON API endpoint
def test_solve_letters_api_json(client: TestClient, monkeypatch):
    # Import models needed for mocking the response
    from qless_solver.grid_solver import (
        Grid,
        GridPosition,
        GridSolution,
        PlacedWord,
    )

    mock_solution = GridSolution(
        grid=Grid(
            words=[
                PlacedWord(
                    word="test", position=GridPosition(x=0, y=0, direction="across")
                )
            ],
            cells={(0, 0): "t"},
        ),
        used_letters=Counter("test"),
    )

    def mock_solve_qless_grid_func(letters: str, min_word_length: int):
        if letters == "test":
            return [mock_solution]
        return []

    # Patch the function in the module where it's defined and used by the endpoint
    monkeypatch.setattr("web.main.solve_qless_grid", mock_solve_qless_grid_func)

    response = client.post(
        "/api/solve/", json={"letters": "test", "min_word_length": 4}
    )
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 1
    assert json_response[0]["grid"]["words"][0]["word"] == "test"
    # Counter serializes to a dict: {'t': 2, 'e': 1, 's': 1}
    assert json_response[0]["used_letters"] == {"t": 2, "e": 1, "s": 1}

    response_no_solution = client.post(
        "/api/solve/", json={"letters": "xyz", "min_word_length": 3}
    )
    assert response_no_solution.status_code == 200
    assert len(response_no_solution.json()) == 0


# Test for the HTMX form submission endpoint
def test_solve_letters_htmx(client: TestClient, monkeypatch):
    from qless_solver.grid_solver import (
        Grid,
        GridPosition,
        GridSolution,
        PlacedWord,
    )

    mock_solution = GridSolution(
        grid=Grid(
            words=[
                PlacedWord(
                    word="htmx", position=GridPosition(x=0, y=0, direction="across")
                )
            ],
            cells={(0, 0): "h"},
        ),
        used_letters=Counter("htmx"),
    )

    test_letters = "htmxabcdefgh"  # 12 letters

    def mock_solve_qless_grid_for_htmx(letters: str, min_word_length: int):
        if letters == test_letters:
            return [mock_solution]
        return []

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solve_qless_grid_for_htmx)

    response = client.post(
        "/solve-htmx/", data={"letters": test_letters, "min_word_length": "4"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert (
        f"Found 1 solution(s) for letters: <strong>{test_letters}</strong>"
        in response.text
    )
    assert test_letters in response.text

    response_no_solution = client.post(
        "/solve-htmx/", data={"letters": "nonezzzzzzzz", "min_word_length": "4"}
    )
    assert response_no_solution.status_code == 200
    assert (
        "No solutions found for letters: <strong>nonezzzzzzzz</strong>"
        in response_no_solution.text
    )


def test_solve_api_error_handling(client: TestClient, monkeypatch):
    def mock_solver_raises_exception(letters: str, min_word_length: int):
        raise ValueError("Solver internal error")

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solver_raises_exception)
    response = client.post(
        "/api/solve/", json={"letters": "error", "min_word_length": 3}
    )
    assert response.status_code == 500
    assert "Solver internal error" in response.json()["detail"]


def test_solve_api_dictionary_not_found(client: TestClient, monkeypatch):
    def mock_solver_raises_file_not_found(letters: str, min_word_length: int):
        raise FileNotFoundError("dictionary.txt not found at expected_path")

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solver_raises_file_not_found)
    response = client.post(
        "/api/solve/", json={"letters": "dict_error", "min_word_length": 3}
    )
    assert response.status_code == 500
    # Check if the detail message contains the specific parts we expect
    detail = response.json()["detail"]
    assert "Dictionary file not found" in detail
    assert "dictionary.txt not found at expected_path" in detail


# Similar error handling test for HTMX endpoint
def test_solve_htmx_error_handling(client: TestClient, monkeypatch):
    def mock_solver_raises_exception_htmx(letters: str, min_word_length: int):
        raise ValueError("HTMX Solver internal error")

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solver_raises_exception_htmx)
    response = client.post(
        "/solve-htmx/", data={"letters": "errorhtmxabc", "min_word_length": "3"}
    )
    assert response.status_code == 200  # HTMX endpoint returns HTML with error message
    assert (
        "<strong>Error:</strong> An error occurred during solving: HTMX Solver internal error"
        in response.text
    )


def test_solve_htmx_validation(client: TestClient):
    response = client.post("/solve-htmx/", data={"letters": "short"})
    assert response.status_code == 200
    assert "Expected exactly 12 letters" in response.text

    response = client.post("/solve-htmx/", data={"letters": "abc123defghi"})
    assert response.status_code == 200
    assert "Input must contain only letters" in response.text


def test_solve_image_endpoint(client: TestClient, monkeypatch):
    from io import BytesIO

    from qless_solver.grid_solver import (
        Grid,
        GridPosition,
        GridSolution,
        PlacedWord,
    )

    mock_solution = GridSolution(
        grid=Grid(
            words=[
                PlacedWord(
                    word="img", position=GridPosition(x=0, y=0, direction="across")
                )
            ],
            cells={(0, 0): "i"},
        ),
        used_letters=Counter("img"),
    )

    test_letters_img = "imgabcdefghi"  # 12 letters

    def mock_detect_letters(_: bytes) -> str:
        return test_letters_img

    def mock_solve_qless_grid_func(letters: str, min_word_length: int):
        if letters == test_letters_img:
            return [mock_solution]
        return []

    monkeypatch.setattr("web.main.detect_letters", mock_detect_letters)
    monkeypatch.setattr("web.main.solve_qless_grid", mock_solve_qless_grid_func)

    fake_file = BytesIO(b"fake")
    response = client.post(
        "/solve-image/",
        files={"image": ("test.png", fake_file, "image/png")},
        data={"min_word_length": "3"},
    )
    assert response.status_code == 200
    assert "Found 1 solution(s)" in response.text


def test_solve_image_validation(client: TestClient, monkeypatch):
    from io import BytesIO

    def mock_detect_letters(_: bytes) -> str:
        return "abcd"

    monkeypatch.setattr("web.main.detect_letters", mock_detect_letters)

    fake_file = BytesIO(b"fake")
    response = client.post(
        "/solve-image/",
        files={"image": ("test.png", fake_file, "image/png")},
        data={"min_word_length": "3"},
    )
    assert response.status_code == 200
    assert "Expected exactly 12 letters" in response.text
