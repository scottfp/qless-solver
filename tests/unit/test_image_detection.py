from pathlib import Path

import cv2
import numpy as np
import pytest
from qless_solver.image_detection import detect_letters

from cli.qless_solver.preprocess import apply_threshold

ROLL_CASES = {
    "test_roll_1.jpg": "kobfldhimiph",
    "test_roll_2.jpg": "blyatarpwnmr",
    "test_roll_3.jpg": "adwilkhldmes",
    "test_roll_4.jpg": "rmtoepngtnxc",
}


def test_can_load_golden_images() -> None:
    """Verify that a golden image can be loaded with OpenCV."""
    image_path = Path("tests/images") / "test_grid_1.jpg"
    image = cv2.imread(str(image_path))
    assert image is not None


@pytest.mark.parametrize("filename,expected", ROLL_CASES.items())
@pytest.mark.xfail(reason="Image letter detection not implemented yet")
def test_detect_letters_from_roll_images(filename: str, expected: str) -> None:
    image_path = Path("tests/images") / filename
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    result = detect_letters(image_bytes)
    assert result == expected


def test_preprocessing_is_deterministic() -> None:
    """apply_threshold should produce consistent results."""
    input_image_path = Path("tests/images") / "test_roll_4.jpg"
    golden_image_path = Path("tests/golden_images") / "golden_roll_4.png"

    input_image = cv2.imread(str(input_image_path))
    assert input_image is not None
    golden_image = cv2.imread(str(golden_image_path), cv2.IMREAD_GRAYSCALE)
    assert golden_image is not None

    processed = apply_threshold(input_image)

    assert np.array_equal(processed, golden_image)
