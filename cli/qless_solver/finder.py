"""Contour finding utilities for dice detection."""

from __future__ import annotations

from typing import List

import cv2
import numpy as np


def find_dice_contours(
    binary_image: np.ndarray, *, min_area: int = 100, max_area: int = 5000
) -> List[np.ndarray]:
    """Find contours that likely correspond to dice in a binary image.

    This uses ``cv2.findContours`` with ``cv2.RETR_EXTERNAL`` to obtain only
    outer contours. Contours are then filtered by area to remove noise.

    Args:
        binary_image: Thresholded image from :func:`apply_threshold`.

    Returns:
        A list of contours passing the area filter.
    """
    contours, _ = cv2.findContours(
        binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    filtered: List[np.ndarray] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area <= area <= max_area:
            filtered.append(contour)

    return filtered
