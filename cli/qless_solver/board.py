"""2D board representation, canonicalization, and strict Q-Less validation.

Coordinate convention:
    ``(x, y)`` integer grid coordinates where ``x`` increases left-to-right
    (across) and ``y`` increases top-to-bottom (down).
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator
from qless_solver.dictionary import Dictionary

Direction = Literal["across", "down"]
CanonicalBoardKey = tuple[tuple[tuple[int, int], str], ...]


class BoardWord(BaseModel):
    """A maximal horizontal or vertical word run on a board."""

    model_config = ConfigDict(frozen=True)

    word: str
    x: int
    y: int
    direction: Direction

    def cells(self) -> tuple[tuple[int, int], ...]:
        """Return the ``(x, y)`` coordinates occupied by this word in reading order."""
        if self.direction == "across":
            return tuple((self.x + i, self.y) for i in range(len(self.word)))
        return tuple((self.x, self.y + i) for i in range(len(self.word)))


class Board(BaseModel):
    """Sparse 2D letter grid supporting normalization, transposition, and run extraction."""

    cells: dict[tuple[int, int], str] = Field(default_factory=dict)

    @field_validator("cells")
    @classmethod
    def _validate_and_normalize_cells(
        cls, value: dict[tuple[int, int], str]
    ) -> dict[tuple[int, int], str]:
        normalized: dict[tuple[int, int], str] = {}
        for coord, ch in value.items():
            if (
                not isinstance(ch, str)
                or len(ch) != 1
                or not ch.isascii()
                or not ch.isalpha()
            ):
                raise ValueError(
                    f"Invalid cell letter {ch!r} at {coord}: must be a single ASCII letter."
                )
            normalized[coord] = ch.lower()
        return normalized

    @classmethod
    def from_rows(cls, rows: Sequence[str], empty_char: str = ".") -> Board:
        """Construct a ``Board`` from row strings using ``empty_char`` or space for empty cells."""
        if len(empty_char) != 1:
            raise ValueError(
                f"empty_char must be a single character, got {empty_char!r}"
            )
        cells: dict[tuple[int, int], str] = {}
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == empty_char or ch == " ":
                    continue
                cells[(x, y)] = ch
        return cls(cells=cells)

    def bounds(self) -> Optional[tuple[int, int, int, int]]:
        """Return ``(min_x, min_y, max_x, max_y)`` or ``None`` if the board is empty."""
        if not self.cells:
            return None
        xs = [x for x, _ in self.cells]
        ys = [y for _, y in self.cells]
        return min(xs), min(ys), max(xs), max(ys)

    def dimensions(self) -> tuple[int, int]:
        """Return ``(width, height)`` of the bounding box, or ``(0, 0)`` if empty."""
        box = self.bounds()
        if box is None:
            return 0, 0
        min_x, min_y, max_x, max_y = box
        return max_x - min_x + 1, max_y - min_y + 1

    def to_rows(self, empty_char: str = ".") -> list[str]:
        """Render the board's bounding box as a list of equal-width row strings."""
        if len(empty_char) != 1:
            raise ValueError(
                f"empty_char must be a single character, got {empty_char!r}"
            )
        box = self.bounds()
        if box is None:
            return []
        min_x, min_y, max_x, max_y = box
        rows: list[str] = []
        for y in range(min_y, max_y + 1):
            row_chars = [
                self.cells.get((x, y), empty_char) for x in range(min_x, max_x + 1)
            ]
            rows.append("".join(row_chars))
        return rows

    def to_ascii(self, empty_char: str = ".") -> str:
        """Render the board's bounding box as a multiline ASCII string."""
        return "\n".join(self.to_rows(empty_char=empty_char))

    def translate(self, dx: int, dy: int) -> Board:
        """Return a new board with every coordinate shifted by ``(dx, dy)``."""
        if dx == 0 and dy == 0:
            return Board(cells=dict(self.cells))
        return Board(cells={(x + dx, y + dy): ch for (x, y), ch in self.cells.items()})

    def normalize(self) -> Board:
        """Shift all coordinates so ``min_x == 0`` and ``min_y == 0``."""
        box = self.bounds()
        if box is None:
            return Board()
        min_x, min_y, _, _ = box
        return self.translate(-min_x, -min_y)

    def transpose(self) -> Board:
        """Return the transposed board with ``(x, y)`` swapped to ``(y, x)``."""
        return Board(cells={(y, x): ch for (x, y), ch in self.cells.items()})

    def canonical_key(self, include_transpose: bool = True) -> CanonicalBoardKey:
        """Return a hashable canonical key deduplicating translations and optional transposes."""
        norm = self.normalize()
        norm_key: CanonicalBoardKey = tuple(sorted(norm.cells.items()))
        if not include_transpose:
            return norm_key
        trans_key: CanonicalBoardKey = tuple(sorted(norm.transpose().cells.items()))
        return min(norm_key, trans_key)

    def canonical(self, include_transpose: bool = True) -> Board:
        """Return the canonical ``Board`` matching ``canonical_key``."""
        return Board(
            cells=dict(self.canonical_key(include_transpose=include_transpose))
        )

    def letter_counts(self) -> Counter[str]:
        """Return a multiset counter of letters placed on the board."""
        return Counter(self.cells.values())

    def is_connected(self) -> bool:
        """Return True iff the board is non-empty and all tiles form one 4-connected group."""
        if not self.cells:
            return False
        start = next(iter(self.cells))
        visited: set[tuple[int, int]] = {start}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            x, y = queue.popleft()
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in self.cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == len(self.cells)

    def extract_runs(self, min_length: int = 2) -> list[BoardWord]:
        """Extract all maximal horizontal and vertical runs of length >= ``min_length``."""
        runs: list[BoardWord] = []

        for x, y in self.cells:
            if (x - 1, y) not in self.cells:
                chars: list[str] = []
                cx = x
                while (cx, y) in self.cells:
                    chars.append(self.cells[(cx, y)])
                    cx += 1
                if len(chars) >= min_length:
                    runs.append(
                        BoardWord(word="".join(chars), x=x, y=y, direction="across")
                    )

            if (x, y - 1) not in self.cells:
                chars = []
                cy = y
                while (x, cy) in self.cells:
                    chars.append(self.cells[(x, cy)])
                    cy += 1
                if len(chars) >= min_length:
                    runs.append(
                        BoardWord(word="".join(chars), x=x, y=y, direction="down")
                    )

        runs.sort(key=lambda r: (r.direction, r.y, r.x))
        return runs


class ValidationResult(BaseModel):
    """Outcome of validating a board against Q-Less rules."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    words: list[BoardWord] = Field(default_factory=list)


def _format_letter_multiset(counts: Counter[str]) -> str:
    parts = [
        f"{ch} (x{count})" if count > 1 else ch for ch, count in sorted(counts.items())
    ]
    return ", ".join(parts)


def validate_board(
    board: Board,
    letters: str,
    dictionary: Dictionary,
    *,
    min_word_length: int = 3,
    allow_duplicates: bool = False,
    allow_single_word: bool = True,
) -> ValidationResult:
    """Validate a Q-Less board against tile, connectivity, word, and policy constraints."""
    expected_letters = letters.strip().lower()
    if (
        not expected_letters
        or not expected_letters.isascii()
        or not expected_letters.isalpha()
    ):
        return ValidationResult(
            is_valid=False,
            errors=[
                f"Invalid target letters {letters!r}: must be a non-empty ASCII letter string."
            ],
            words=[],
        )

    if not board.cells:
        return ValidationResult(
            is_valid=False,
            errors=["Board is empty."],
            words=[],
        )

    errors: list[str] = []

    actual_counts = board.letter_counts()
    expected_counts = Counter(expected_letters)
    if actual_counts != expected_counts:
        missing = expected_counts - actual_counts
        extra = actual_counts - expected_counts
        if missing:
            errors.append(
                f"Missing letters from board: {_format_letter_multiset(missing)}."
            )
        if extra:
            errors.append(
                f"Extra or unexpected letters on board: {_format_letter_multiset(extra)}."
            )

    if not board.is_connected():
        errors.append("Board tiles are not orthogonally connected into a single group.")

    runs = board.extract_runs(min_length=2)
    if not runs:
        errors.append(f"Board contains no words of length >= {min_word_length}.")
    else:
        for run in runs:
            if len(run.word) < min_word_length:
                errors.append(
                    f"Word '{run.word}' at ({run.x}, {run.y}) {run.direction} "
                    f"is shorter than minimum length {min_word_length}."
                )
            elif not dictionary.is_valid_word(run.word, min_length=min_word_length):
                errors.append(
                    f"Invalid word '{run.word}' at ({run.x}, {run.y}) {run.direction}."
                )

    if not allow_single_word and len(runs) == 1:
        errors.append("Board must contain at least two intersecting words.")

    if not allow_duplicates:
        word_counts = Counter(run.word for run in runs)
        for word, count in sorted(word_counts.items()):
            if count > 1:
                errors.append(f"Duplicate word '{word}' appears {count} times.")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        words=runs,
    )
