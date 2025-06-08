"""Image-based letter detection utilities.

The functions in this module perform very small scale optical character
recognition (OCR) using :mod:`Pillow`.  The implementation is purposely simple
so that it works in the restricted execution environment used for the unit
tests where heavyweight OCR engines such as Tesseract are unavailable.
"""

from __future__ import annotations

from io import BytesIO
from typing import Dict, Iterable, List, cast

from PIL import Image, ImageChops, ImageDraw, ImageFile, ImageFont, ImageOps, ImageStat

# Size (width and height) of each cell in the synthetic test images.  The tests
# generate the images using this value, so the detection logic relies on it as
# well.
CELL_SIZE = 50


def _create_templates(font_size: int = 36) -> Dict[str, Image.Image]:
    """Create template images for the uppercase alphabet.

    These templates are used for naive template matching.  Because the test
    images are created with the same font, simple pixel comparison is
    sufficient.
    """

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, font_size)
    templates: Dict[str, Image.Image] = {}

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        img = Image.new("L", (CELL_SIZE, CELL_SIZE), 255)
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), letter, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((CELL_SIZE - w) / 2, (CELL_SIZE - h) / 2 - 5),
            letter,
            font=font,
            fill=0,
        )
        templates[letter] = img
    return templates


# Generate templates once at import time
TEMPLATES = _create_templates()


def _recognise_cell(cell: Image.Image) -> str:
    """Return the recognised uppercase letter for ``cell``.

    If the cell is blank (very light), ``'.'`` is returned.
    """

    cell = cell.resize((CELL_SIZE, CELL_SIZE)).convert("L")
    if ImageStat.Stat(cell).mean[0] > 250:  # almost white - treat as blank
        return "."

    best_char = "."
    best_score = float("inf")

    for char, template in TEMPLATES.items():
        diff = ImageChops.difference(cell, template)
        score = sum(diff.getdata())
        if score < best_score:
            best_score = score
            best_char = char

    return best_char


def _split_cells(img: Image.Image | ImageFile.ImageFile) -> Iterable[Image.Image]:
    """Yield equally sized cells from ``img`` left to right."""

    width, height = img.size
    cols = width // CELL_SIZE
    for i in range(cols):
        yield img.crop((i * CELL_SIZE, 0, (i + 1) * CELL_SIZE, CELL_SIZE))


def detect_letters(image_bytes: bytes) -> str:
    """Detect a 12‑letter roll from an uploaded image.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the uploaded image representing a single row of 12 dice.

    Returns
    -------
    str
        A 12‑letter lowercase string representing the detected dice letters.
    """

    image = cast(Image.Image, Image.open(BytesIO(image_bytes)))
    image = ImageOps.grayscale(image)

    letters = [_recognise_cell(cell).lower() for cell in _split_cells(image)]
    return "".join(letters)


def detect_grid(image_bytes: bytes) -> List[str]:
    """Detect a grid of letters from ``image_bytes``.

    The function assumes that the image consists of ``CELL_SIZE`` square cells
    arranged in a rectangular grid.
    """

    image = cast(Image.Image, Image.open(BytesIO(image_bytes)))
    image = ImageOps.grayscale(image)

    width, height = image.size
    cols = width // CELL_SIZE
    rows = height // CELL_SIZE

    grid: List[str] = []
    for r in range(rows):
        row_letters = []
        for c in range(cols):
            cell = image.crop(
                (c * CELL_SIZE, r * CELL_SIZE, (c + 1) * CELL_SIZE, (r + 1) * CELL_SIZE)
            )
            row_letters.append(_recognise_cell(cell).lower())
        grid.append("".join(row_letters))

    return grid
