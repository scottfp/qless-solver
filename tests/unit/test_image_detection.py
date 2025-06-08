from pathlib import Path

from qless_solver.image_detection import detect_grid, detect_letters

DATA_DIR = Path(__file__).resolve().parent.parent / "images"


def _read_image(name: str) -> bytes:
    with open(DATA_DIR / name, "rb") as f:
        return f.read()


def test_detect_letters_roll_images() -> None:
    cases = {
        "test_roll_1.jpg": "kobfldhimiph",
        "test_roll_2.jpg": "blyatarpwnmr",
        "test_roll_3.jpg": "adwilkhldmes",
        "test_roll_4.jpg": "rmtoepngtnxc",
    }
    for filename, expected in cases.items():
        img_bytes = _read_image(filename)
        assert detect_letters(img_bytes) == expected


def test_detect_grid_images() -> None:
    cases = {
        "test_grid_1.jpg": [".f...", "kohl.", ".b.i.", "...p.", ".him.", "...d."],
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
        "test_grid_4.jpg": [".p...", ".r.n.", "comet", ".n.x.", ".g.t."],
    }
    for filename, expected in cases.items():
        img_bytes = _read_image(filename)
        assert detect_grid(img_bytes) == expected
