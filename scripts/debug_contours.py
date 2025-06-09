"""Visualize detected dice contours for debugging."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli.qless_solver.finder import find_dice_contours
from cli.qless_solver.preprocess import apply_threshold


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug dice contour detection")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the source image",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to save the annotated image",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = cv2.imread(str(args.input))
    if image is None:
        raise FileNotFoundError(f"Unable to load image: {args.input}")

    binary = apply_threshold(image)
    contours = find_dice_contours(binary)

    cv2.drawContours(image, contours, -1, (0, 255, 0), 2)
    cv2.imwrite(str(args.output), image)


if __name__ == "__main__":
    main()
