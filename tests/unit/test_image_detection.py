from pathlib import Path

import pytest
from qless_solver.image_detection import detect_letters

ROLL_CASES = {
    "test_roll_1.jpg": "kobfldhimiph",
    "test_roll_2.jpg": "blyatarpwnmr",
    "test_roll_3.jpg": "adwilkhldmes",
    "test_roll_4.jpg": "rmtoepngtnxc",
}


@pytest.mark.parametrize("filename,expected", ROLL_CASES.items())
@pytest.mark.xfail(reason="Image letter detection not implemented yet")
def test_detect_letters_from_roll_images(filename: str, expected: str) -> None:
    image_path = Path("tests/images") / filename
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    result = detect_letters(image_bytes)
    assert result == expected
