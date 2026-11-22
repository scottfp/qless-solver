import os
import sys
from collections import Counter

import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path to allow importing web.main
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from web.main import app
except Exception as e:
    print(f"Skipping web API tests: Could not import FastAPI app from web.main: {e}")
    app = None


@pytest.fixture(scope="module")
def client():
    if app is None:
        pytest.skip("FastAPI app not available for testing.")
    with TestClient(app) as c:
        yield c


def test_healthz_endpoint(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["dictionary_words"], int)
    assert data["dictionary_words"] > 1000


def test_read_root_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "<title>Q-less Solver</title>" in response.text
    assert 'id="dark-mode-toggle"' in response.text
    assert 'id="roll-dice-btn"' in response.text
    assert 'id="default-grid-wrapper"' not in response.text


def test_roll_endpoint(client: TestClient) -> None:
    response = client.get("/roll/")
    assert response.status_code == 200
    data = response.json()
    letters = data["letters"]
    assert isinstance(letters, str)
    assert len(letters) == 12
    assert letters.isascii() and letters.isalpha() and letters.islower()


def test_solve_letters_api_json_mocked(client: TestClient, monkeypatch) -> None:
    from qless_solver.grid_solver import Grid, GridPosition, GridSolution, PlacedWord

    mock_solution = GridSolution(
        grid=Grid(
            words=[
                PlacedWord(
                    word="test", position=GridPosition(x=0, y=0, direction="across")
                )
            ],
            cells={(0, 0): "t", (1, 0): "e", (2, 0): "s", (3, 0): "t"},
        ),
        used_letters=Counter("test"),
    )

    def mock_solve_qless_grid_func(letters: str, min_word_length: int, **_kwargs):
        if letters == "rmtoepngtnxc":
            return [mock_solution]
        return []

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solve_qless_grid_func)

    response = client.post(
        "/api/solve/", json={"letters": "rmtoepngtnxc", "min_word_length": 4}
    )
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 1
    assert json_response[0]["grid"]["words"][0]["word"] == "test"
    assert json_response[0]["used_letters"] == {"t": 2, "e": 1, "s": 1}

    response_no_solution = client.post(
        "/api/solve/", json={"letters": "bcdfghjklmnp", "min_word_length": 3}
    )
    assert response_no_solution.status_code == 200
    assert len(response_no_solution.json()) == 0


def test_solve_letters_api_live(client: TestClient) -> None:
    from qless_solver.board import Board, validate_board
    from qless_solver.dictionary import Dictionary

    response = client.post(
        "/api/solve/",
        json={"letters": "rmtoepngtnxc", "min_word_length": 3, "max_solutions": 3},
    )
    assert response.status_code == 200
    solutions = response.json()
    assert 1 <= len(solutions) <= 3

    dictionary = Dictionary()
    for sol in solutions:
        raw_cells = sol["grid"]["cells"]
        parsed_cells = {
            (int(k.split(",")[0]), int(k.split(",")[1])): v
            for k, v in raw_cells.items()
        }
        board = Board(cells=parsed_cells)
        res = validate_board(board, "rmtoepngtnxc", dictionary)
        assert res.is_valid, res.errors


def test_solve_letters_api_unsolvable_and_validation(client: TestClient) -> None:
    unsolvable = client.post(
        "/api/solve/", json={"letters": "bcdfghjklmnp", "min_word_length": 3}
    )
    assert unsolvable.status_code == 200
    assert unsolvable.json() == []

    for bad_payload in (
        {"letters": "abc", "min_word_length": 3},
        {"letters": "abc123defghi", "min_word_length": 3},
        {"letters": "rmtoepngtnxc", "min_word_length": 1},
    ):
        resp = client.post("/api/solve/", json=bad_payload)
        assert resp.status_code == 422


def test_solve_letters_htmx_mocked(client: TestClient, monkeypatch) -> None:
    from qless_solver.grid_solver import Grid, GridPosition, GridSolution, PlacedWord

    mock_solution = GridSolution(
        grid=Grid(
            words=[
                PlacedWord(
                    word="htmx", position=GridPosition(x=0, y=0, direction="across")
                )
            ],
            cells={(0, 0): "h", (1, 0): "t", (2, 0): "m", (3, 0): "x"},
        ),
        used_letters=Counter("htmx"),
    )

    def mock_solve_qless_grid_for_htmx(letters: str, min_word_length: int, **_kwargs):
        if letters == "rmtoepngtnxc":
            return [mock_solution]
        return []

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solve_qless_grid_for_htmx)

    response = client.post(
        "/solve-htmx/", data={"letters": "rmtoepngtnxc", "min_word_length": "4"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert (
        "Found 1 solution(s) for letters:\n            <strong>rmtoepngtnxc</strong>"
        in response.text
        or "<strong>rmtoepngtnxc</strong>" in response.text
    )
    assert "HTMX" in response.text
    assert 'id="result-grid"' in response.text

    response_no_solution = client.post(
        "/solve-htmx/", data={"letters": "bcdfghjklmnp", "min_word_length": "4"}
    )
    assert response_no_solution.status_code == 200
    assert (
        "No solutions found for letters: <strong>bcdfghjklmnp</strong>"
        in response_no_solution.text
    )


def test_solve_letters_htmx_live_and_validation(client: TestClient) -> None:
    live = client.post(
        "/solve-htmx/",
        data={
            "letters": "RMTOEPNGTNXC",
            "min_word_length": "3",
            "max_solutions": "4",
        },
    )
    assert live.status_code == 200
    assert "Found " in live.text
    assert 'id="result-grid"' in live.text
    assert 'class="word-badge"' in live.text
    assert 'class="word-exclude"' in live.text
    assert 'id="prev-result"' in live.text
    assert 'id="next-result"' in live.text
    assert 'id="result-definition"' in live.text
    assert 'data-x="0"' in live.text
    assert 'data-y="0"' in live.text
    assert '"word_entries"' in live.text
    assert '"definition"' in live.text

    bad_len = client.post(
        "/solve-htmx/", data={"letters": "abc", "min_word_length": "3"}
    )
    assert bad_len.status_code == 200
    assert "Expected exactly 12 letters, got 3." in bad_len.text


def test_solve_api_error_handling(client: TestClient, monkeypatch) -> None:
    def mock_solver_raises_exception(letters: str, min_word_length: int, **_kwargs):
        raise ValueError("Solver internal error")

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solver_raises_exception)
    response = client.post(
        "/api/solve/", json={"letters": "rmtoepngtnxc", "min_word_length": 3}
    )
    assert response.status_code == 500
    assert "Solver internal error" in response.json()["detail"]


def test_solve_api_dictionary_not_found(client: TestClient, monkeypatch) -> None:
    def mock_solver_raises_file_not_found(
        letters: str, min_word_length: int, **_kwargs
    ):
        raise FileNotFoundError("dictionary.txt not found at expected_path")

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solver_raises_file_not_found)
    response = client.post(
        "/api/solve/", json={"letters": "rmtoepngtnxc", "min_word_length": 3}
    )
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "Dictionary file not found" in detail
    assert "dictionary.txt not found at expected_path" in detail


def test_solve_htmx_error_handling(client: TestClient, monkeypatch) -> None:
    def mock_solver_raises_exception_htmx(
        letters: str, min_word_length: int, **_kwargs
    ):
        raise ValueError("HTMX Solver internal error")

    monkeypatch.setattr("web.main.solve_qless_grid", mock_solver_raises_exception_htmx)
    response = client.post(
        "/solve-htmx/", data={"letters": "rmtoepngtnxc", "min_word_length": "3"}
    )
    assert response.status_code == 200
    assert (
        "<strong>Error:</strong> An error occurred during solving: HTMX Solver internal error"
        in response.text
    )


def test_solve_image_endpoint_stub_message(client: TestClient) -> None:
    from io import BytesIO

    fake_file = BytesIO(b"fake")
    response = client.post(
        "/solve-image/",
        files={"image": ("test.png", fake_file, "image/png")},
        data={"min_word_length": "3"},
    )
    assert response.status_code == 200
    assert "not implemented yet" in response.text


def test_solve_image_endpoint_mocked(client: TestClient, monkeypatch) -> None:
    from io import BytesIO

    from qless_solver.grid_solver import Grid, GridPosition, GridSolution, PlacedWord

    mock_solution = GridSolution(
        grid=Grid(
            words=[
                PlacedWord(
                    word="comet", position=GridPosition(x=0, y=0, direction="across")
                )
            ],
            cells={(0, 0): "c", (1, 0): "o", (2, 0): "m", (3, 0): "e", (4, 0): "t"},
        ),
        used_letters=Counter("comet"),
    )

    def mock_detect_letters(_: bytes) -> str:
        return "rmtoepngtnxc"

    def mock_solve_qless_grid_func(letters: str, min_word_length: int, **_kwargs):
        if letters == "rmtoepngtnxc":
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


def test_define_word_api_success(client: TestClient) -> None:
    resp = client.get("/api/define/gorm")
    assert resp.status_code == 200
    assert resp.json() == {
        "word": "GORM",
        "definition": "foolish person [n] / understand [v]",
    }

    variant = client.get("/api/define/BUNN")
    assert variant.status_code == 200
    assert variant.json()["definition"].startswith("variant of BUN")


def test_define_word_api_not_found_and_invalid(client: TestClient) -> None:
    assert client.get("/api/define/notarealwordxyz").status_code == 404
    assert client.get("/api/define/123").status_code == 422


def test_serialize_solutions_word_entries_cover_board_tiles() -> None:
    if app is None:
        pytest.skip("FastAPI app not available for testing.")
    from qless_solver.grid_solver import solve_qless_grid

    from web.main import _serialize_solutions, get_dictionary

    dictionary = get_dictionary()
    solutions = solve_qless_grid(
        letters="rmtoepngtnxc", dictionary=dictionary, max_solutions=3
    )
    assert solutions
    for sol in _serialize_solutions(solutions, dictionary):
        rows = sol["rows"]
        assert isinstance(rows, list)
        entries = sol["word_entries"]
        assert isinstance(entries, list)
        assert [e["word"] for e in entries] == sol["words"]
        for entry in entries:
            assert entry["definition"]
            spelled = "".join(rows[y][x] for x, y in entry["cells"])
            assert spelled.upper() == entry["word"]


def test_solve_api_excluded_words(client: TestClient) -> None:
    resp = client.post(
        "/api/solve/",
        json={
            "letters": "rmtoepngtnxc",
            "min_word_length": 3,
            "max_solutions": 3,
            "excluded_words": ["context"],
        },
    )
    assert resp.status_code == 200
    solutions = resp.json()
    assert len(solutions) >= 1
    for sol in solutions:
        words = [pw["word"].lower() for pw in sol["grid"]["words"]]
        assert "context" not in words


def test_solve_htmx_excluded_words(client: TestClient) -> None:
    resp = client.post(
        "/solve-htmx/",
        data={
            "letters": "rmtoepngtnxc",
            "min_word_length": "3",
            "max_solutions": "3",
            "excluded_words": "context, gorm",
        },
    )
    assert resp.status_code == 200
    assert "Found " in resp.text
    assert '"word": "CONTEXT"' not in resp.text
    assert '"word": "GORM"' not in resp.text

    empty_resp = client.post(
        "/solve-htmx/",
        data={
            "letters": "abcdefghijkl",
            "min_word_length": "12",
            "max_solutions": "3",
            "excluded_words": "abcdefghijkl",
        },
    )
    assert empty_resp.status_code == 200
    assert "No solutions found" in empty_resp.text
    assert "excluding:" in empty_resp.text
    assert "ABCDEFGHIJKL" in empty_resp.text
