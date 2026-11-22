#!/usr/bin/env python3
"""Build ``common_words.txt`` from SCOWL (2020.12.07) intersected with ``dictionary.txt``."""

from __future__ import annotations

import argparse
import re
import tarfile
from pathlib import Path
from typing import Iterable

SCOWL_TIERS = (10, 20, 35, 40, 50, 55, 60, 70, 80, 95)
SCOWL_FILE_RE = re.compile(r"(?:^|/)final/(english|american)-words\.(\d+)$")


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for building the common dictionary word list."""
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Extract lowercase common words from a SCOWL archive, intersect with "
            "dictionary.txt, and write common_words.txt."
        )
    )
    parser.add_argument(
        "--scowl-archive",
        required=True,
        type=Path,
        help="Path to the scowl-2020.12.07.tar.gz archive",
    )
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=repo_root / "dictionary.txt",
        help="Path to the full dictionary.txt file (default: repo root)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "common_words.txt",
        help="Output path for the generated common word list",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=35,
        choices=SCOWL_TIERS,
        help="Maximum SCOWL size tier to include (default: 35)",
    )
    return parser.parse_args(args)


def _is_strict_lowercase_ascii_word(word: str) -> bool:
    return len(word) >= 2 and word.isascii() and word.isalpha() and word == word.lower()


def load_scowl_words(archive_path: Path, max_size: int = 35) -> set[str]:
    """Load lowercase English and American words up to ``max_size`` from SCOWL."""
    words: set[str] = set()
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            match = SCOWL_FILE_RE.search(member.name)
            if not match:
                continue
            tier = int(match.group(2))
            if tier > max_size:
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            with handle:
                for raw_line in handle:
                    line = raw_line.decode("latin-1").strip()
                    if _is_strict_lowercase_ascii_word(line):
                        words.add(line)
    return words


def load_nwl_words(dictionary_path: Path) -> set[str]:
    """Load lowercase ASCII alphabetic words from ``dictionary.txt``."""
    words: set[str] = set()
    with open(dictionary_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            token = stripped.split(" ", 1)[0].lower()
            cleaned = "".join(ch for ch in token if ch.isascii() and ch.isalpha())
            if cleaned:
                words.add(cleaned)
    return words


def write_word_list(output_path: Path, words: Iterable[str]) -> list[str]:
    """Write sorted unique words one per line with a trailing newline."""
    sorted_words = sorted(set(words))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for word in sorted_words:
            handle.write(f"{word}\n")
    return sorted_words


def main() -> int:
    """Generate the curated common word list and print sanity diagnostics."""
    args = parse_args()
    scowl_words = load_scowl_words(args.scowl_archive, max_size=args.max_size)
    nwl_words = load_nwl_words(args.dictionary)
    common_words = write_word_list(args.output, scowl_words & nwl_words)

    print(
        f"Loaded {len(scowl_words)} SCOWL (<= {args.max_size}) words, "
        f"{len(nwl_words)} NWL words."
    )
    print(f"Wrote {len(common_words)} intersected words to {args.output}")

    common_set = set(common_words)
    expected_present = (
        "apple",
        "comet",
        "prong",
        "next",
        "context",
        "cats",
        "running",
        "strawberries",
        "norm",
        "peg",
    )
    expected_absent = (
        "aa",
        "gorm",
        "dwalm",
        "cwm",
        "qi",
        "za",
        "xu",
        "abye",
        "mong",
        "zyzzyva",
    )
    present_ok = {w: (w in common_set) for w in expected_present}
    absent_ok = {w: (w not in common_set) for w in expected_absent}
    print("Expected present:", present_ok)
    print("Expected absent:", absent_ok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
