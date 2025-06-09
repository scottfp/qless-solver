#!/usr/bin/env python3
"""Utility to generate a thresholded image for manual verification."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

# Ensure the project root is on the path when running directly from the repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli.qless_solver.preprocess import apply_threshold


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate thresholded image")
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
        help="Path to save the processed image",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = cv2.imread(str(args.input))
    if image is None:
        raise FileNotFoundError(f"Unable to load image: {args.input}")

    result = apply_threshold(image)
    cv2.imwrite(str(args.output), result)


if __name__ == "__main__":
    main()
