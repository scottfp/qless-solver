"""Image-based letter detection utilities."""

from __future__ import annotations

import cv2
import easyocr
import numpy as np

_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    """Create or return a cached EasyOCR reader."""
    global _reader
    if _reader is None:
        # Initialize with English alphabet only, GPU disabled for portability
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def detect_letters(image_bytes: bytes) -> str:
    """Detect dice letters using EasyOCR.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the uploaded image.

    Returns
    -------
    str
        A lowercase string of up to 12 detected letters.
    """

    if not image_bytes:
        return ""

    # Decode bytes into an OpenCV image
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return ""

    reader = _get_reader()

    results = reader.readtext(img, detail=0, paragraph=False)

    letters = "".join(ch for res in results for ch in res if ch.isalpha())
    return letters.lower()[:12]
