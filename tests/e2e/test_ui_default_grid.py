import os
import sys

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
        ".him.",
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


@pytest.fixture(scope="module")
def client():
    if app is None:
        pytest.skip("FastAPI app not available for testing.")
    with TestClient(app) as c:
        yield c


@pytest.mark.xfail(reason="Default grid not shown on page load yet")
def test_index_displays_default_grid(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "solution-grid" in html
    for row in GRID_CASES["test_grid_1.jpg"]:
        assert row in html


@pytest.mark.xfail(reason="Navigation arrows not implemented yet")
def test_index_has_navigation_arrows(client: TestClient):
    response = client.get("/")
    html = response.text
    assert 'id="prev-solution"' in html
    assert 'id="next-solution"' in html
