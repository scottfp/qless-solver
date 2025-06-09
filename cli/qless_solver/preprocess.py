"""Image pre-processing utilities for OCR."""

from __future__ import annotations

import cv2
import numpy as np


def apply_threshold(image: np.ndarray) -> np.ndarray:
    """Convert image to a binary thresholded form.

    Steps:
    1. Convert to grayscale.
    2. Apply a 5x5 Gaussian blur.
    3. Apply adaptive Gaussian thresholding.

    Args:
        image: Input image as a NumPy array in BGR format.

    Returns:
        The thresholded binary image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )
    return thresh
