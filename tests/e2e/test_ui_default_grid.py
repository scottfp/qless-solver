import os
import sys
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

# Ensure the web app can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from web.main import app
except Exception:
    app = None

GRID_CASES = {
    "test_grid_1.jpg": [
        ".f...",
        "kohl.",
        ".b.i.",
        "...p.",
        "..him",
        "...d.",
    ],
    "test_grid_2.jpg": [
        ".....w",
        ".....r",
        ".l...a",
        "pantry",
        ".m....",
        ".b....",
    ],
    "test_grid_3.jpg": [
        "....s.",
        "....h.",
        "....a.",
        ".l..k.",
        "mildew",
        ".d....",
    ],
    "test_grid_4.jpg": [
        ".p...",
        ".r.n.",
        "comet",
        ".n.x.",
        ".g.t.",
    ],
}


class _SolutionGridParser(HTMLParser):
    """Extract row strings from `<div id="solution-grid">`."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[str] = []
        self._grid_depth = 0
        self._in_row = False
        self._in_cell = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return
        attr_map = dict(attrs)
        classes = (attr_map.get("class") or "").split()

        if self._grid_depth == 0:
            if attr_map.get("id") == "solution-grid":
                self._grid_depth = 1
            return

        self._grid_depth += 1
        if "grid-row" in classes:
            self._in_row = True
            self._current_row = []
        elif self._in_row and "grid-cell" in classes:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "div" or self._grid_depth == 0:
            return
        if self._in_cell:
            text = "".join(self._current_cell).strip()
            self._current_row.append(text if text else ".")
            self._in_cell = False
        elif self._in_row and self._grid_depth == 2:
            self.rows.append("".join(self._current_row))
            self._in_row = False
        self._grid_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)


@pytest.fixture(scope="module")
def client():
    if app is None:
        pytest.skip("FastAPI app not available for testing.")
    with TestClient(app) as c:
        yield c


def test_index_displays_default_grid(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "solution-grid" in html
    parser = _SolutionGridParser()
    parser.feed(html)
    assert parser.rows == GRID_CASES["test_grid_1.jpg"]


def test_index_has_navigation_arrows(client: TestClient):
    response = client.get("/")
    html = response.text
    assert 'id="prev-solution"' in html
    assert 'id="next-solution"' in html
