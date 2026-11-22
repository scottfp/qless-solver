"""Intersection-aware 2D grid solver for the Q-Less solitaire dice game."""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from qless_solver.board import Board, CanonicalBoardKey, Direction
from qless_solver.dictionary import Dictionary


class GridPosition(BaseModel):
    """Starting coordinate and direction of a placed word on a grid."""

    model_config = ConfigDict(frozen=True)

    x: int
    y: int
    direction: Direction = "across"


class PlacedWord(BaseModel):
    """A word placed on the grid along with its starting position."""

    model_config = ConfigDict(frozen=True)

    word: str
    position: GridPosition


class Grid(BaseModel):
    """2D crossword grid representation compatible with the web UI and JSON API."""

    cells: dict[tuple[int, int], str] = Field(default_factory=dict)
    words: list[PlacedWord] = Field(default_factory=list)

    @classmethod
    def from_board(cls, board: Board) -> Grid:
        """Create a normalized ``Grid`` with extracted words from a ``Board``."""
        norm = board.normalize()
        words = [
            PlacedWord(
                word=bw.word,
                position=GridPosition(x=bw.x, y=bw.y, direction=bw.direction),
            )
            for bw in norm.extract_runs(min_length=2)
        ]
        return cls(cells=dict(norm.cells), words=words)

    def to_board(self) -> Board:
        """Convert this ``Grid`` back to a ``Board``."""
        return Board(cells=dict(self.cells))


class GridSolution(BaseModel):
    """A solved Q-Less grid along with its letter multiplicity summary."""

    grid: Grid
    used_letters: dict[str, int]

    def to_board(self) -> Board:
        """Return the underlying ``Board`` for this solution."""
        return self.grid.to_board()


def score_board(board: Board) -> tuple[int, int, int, CanonicalBoardKey]:
    """Rank boards cleanly: fewer words, smaller area, squarer shape, deterministic key."""
    words = board.extract_runs(min_length=2)
    width, height = board.dimensions()
    return (
        len(words),
        width * height,
        abs(width - height),
        board.canonical_key(),
    )


def _raw_canonical_key(cells: dict[tuple[int, int], str]) -> CanonicalBoardKey:
    """Compute canonical key directly from raw cell coordinates without Pydantic overhead."""
    if not cells:
        return ()
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    norm_key: CanonicalBoardKey = tuple(
        sorted(((x - min_x, y - min_y), ch) for (x, y), ch in cells.items())
    )
    trans_key: CanonicalBoardKey = tuple(
        sorted(((y - min_y, x - min_x), ch) for (x, y), ch in cells.items())
    )
    return min(norm_key, trans_key)


def _extract_raw_words(cells: dict[tuple[int, int], str]) -> list[str]:
    """Extract all maximal horizontal and vertical runs of length >= 2."""
    words: list[str] = []
    for x, y in cells:
        if (x - 1, y) not in cells:
            cx = x
            chars: list[str] = []
            while (cx, y) in cells:
                chars.append(cells[(cx, y)])
                cx += 1
            if len(chars) >= 2:
                words.append("".join(chars))
        if (x, y - 1) not in cells:
            cy = y
            chars = []
            while (x, cy) in cells:
                chars.append(cells[(x, cy)])
                cy += 1
            if len(chars) >= 2:
                words.append("".join(chars))
    return words


def _try_place(
    word: str,
    sx: int,
    sy: int,
    direction: Direction,
    cells: dict[tuple[int, int], str],
    rem: Counter[str],
    dictionary: Dictionary,
    min_word_length: int,
) -> Optional[list[tuple[tuple[int, int], str]]]:
    """Validate and return new tiles for placing ``word`` at ``(sx, sy)``, or None."""
    dx, dy = (1, 0) if direction == "across" else (0, 1)
    px, py = (0, 1) if direction == "across" else (1, 0)
    word_len = len(word)

    # Disallow merging into adjacent collinear tiles on either end
    if (sx - dx, sy - dy) in cells or (
        sx + word_len * dx,
        sy + word_len * dy,
    ) in cells:
        return None

    new_cells: list[tuple[tuple[int, int], str]] = []
    needed: dict[str, int] = {}

    for i, ch in enumerate(word):
        pos = (sx + i * dx, sy + i * dy)
        existing = cells.get(pos)
        if existing is not None:
            if existing != ch:
                return None
        else:
            cnt = needed.get(ch, 0) + 1
            if cnt > rem[ch]:
                return None
            needed[ch] = cnt
            new_cells.append((pos, ch))

    if not new_cells:
        return None

    # Validate every perpendicular cross-run created or touched by a newly placed tile
    for (nx, ny), ch in new_cells:
        if (nx - px, ny - py) in cells or (nx + px, ny + py) in cells:
            bx, by = nx - px, ny - py
            while (bx, by) in cells:
                bx -= px
                by -= py
            bx += px
            by += py

            cross_chars: list[str] = []
            cx, cy = bx, by
            while True:
                if (cx, cy) == (nx, ny):
                    cross_chars.append(ch)
                elif (cx, cy) in cells:
                    cross_chars.append(cells[(cx, cy)])
                else:
                    break
                cx += px
                cy += py

            if len(cross_chars) < min_word_length:
                return None
            cross_word = "".join(cross_chars)
            if not dictionary.is_valid_word(cross_word, min_length=min_word_length):
                return None

    return new_cells


def solve_board(
    letters: str,
    *,
    dictionary: Optional[Dictionary] = None,
    min_word_length: int = 3,
    max_solutions: Optional[int] = 10,
    allow_duplicates: bool = False,
    allow_single_word: bool = True,
    deduplicate_transpose: bool = True,
    timeout_seconds: Optional[float] = 5.0,
    max_nodes: Optional[int] = 200_000,
) -> list[Board]:
    """Find valid Q-Less ``Board`` arrangements for ``letters``."""
    if min_word_length < 2:
        raise ValueError("min_word_length must be at least 2")
    if max_solutions is not None and max_solutions <= 0:
        return []

    cleaned = letters.strip().lower()
    if (
        not cleaned
        or not cleaned.isascii()
        or not cleaned.isalpha()
        or len(cleaned) < min_word_length
    ):
        return []

    active_dict = dictionary if dictionary is not None else Dictionary()
    candidates = sorted(
        active_dict.get_valid_words(cleaned, min_length=min_word_length)
    )
    if not candidates:
        return []

    initial_counts = Counter(cleaned)
    total_tiles = len(cleaned)

    df: Counter[str] = Counter()
    for word in candidates:
        for ch in set(word):
            df[ch] += 1

    # Every tile letter must appear in at least one valid candidate word
    for ch in initial_counts:
        if df[ch] == 0:
            return []

    def _word_priority(word: str) -> tuple[int, float, str]:
        rarity = sum(1.0 / df[ch] for ch in set(word))
        return (-len(word), -rarity, word)

    candidates.sort(key=_word_priority)

    by_letter: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for word in candidates:
        for idx, ch in enumerate(word):
            by_letter[ch].append((word, idx))

    # Every valid solution (up to transpose) has an across word containing the rarest letter
    rarest_ch = min(initial_counts, key=lambda ch: (df[ch], ch))
    seed_words = [
        word
        for word in candidates
        if rarest_ch in word and (allow_single_word or len(word) < total_tiles)
    ]
    if not seed_words:
        return []

    cells: dict[tuple[int, int], str] = {}
    rem = initial_counts.copy()
    canonical_solutions: list[Board] = []
    seen_solutions: set[CanonicalBoardKey] = set()
    visited_states: set[CanonicalBoardKey] = set()
    expanded_count = 0
    nodes = 0
    deadline = (
        time.perf_counter() + timeout_seconds if timeout_seconds is not None else None
    )

    def _limit_reached() -> bool:
        if max_solutions is not None:
            current = (
                len(canonical_solutions) if deduplicate_transpose else expanded_count
            )
            if current >= max_solutions:
                return True
        if deadline is not None and time.perf_counter() > deadline:
            return True
        if max_nodes is not None and nodes >= max_nodes:
            return True
        return False

    def dfs(rem_total: int) -> None:
        nonlocal expanded_count, nodes
        if _limit_reached():
            return
        nodes += 1

        ck = _raw_canonical_key(cells)
        if ck in visited_states:
            return
        visited_states.add(ck)

        if rem_total == 0:
            words_now = _extract_raw_words(cells)
            if not allow_single_word and len(words_now) <= 1:
                return
            if not allow_duplicates and len(words_now) != len(set(words_now)):
                return
            if ck not in seen_solutions:
                seen_solutions.add(ck)
                board = Board(cells=dict(ck))
                canonical_solutions.append(board)
                if deduplicate_transpose:
                    expanded_count += 1
                else:
                    expanded_count += 1 if board.transpose() == board else 2
            return

        rem_letters = [ch for ch, cnt in rem.items() if cnt > 0]
        target_ch = min(rem_letters, key=lambda ch: (df[ch], ch))

        anchors = list(cells.items())
        tried_placements: set[tuple[str, int, int, Direction]] = set()

        for pass_target_only in (True, False):
            for (ax, ay), ach in anchors:
                has_h = (ax - 1, ay) in cells or (ax + 1, ay) in cells
                has_v = (ax, ay - 1) in cells or (ax, ay + 1) in cells
                dirs: list[Direction] = []
                if not has_h:
                    dirs.append("across")
                if not has_v:
                    dirs.append("down")
                if not dirs:
                    continue

                for word, idx in by_letter[ach]:
                    has_target = target_ch in word
                    if pass_target_only != has_target:
                        continue
                    for direction in dirs:
                        sx = ax - idx if direction == "across" else ax
                        sy = ay if direction == "across" else ay - idx
                        pkey = (word, sx, sy, direction)
                        if pkey in tried_placements:
                            continue
                        tried_placements.add(pkey)

                        placed = _try_place(
                            word,
                            sx,
                            sy,
                            direction,
                            cells,
                            rem,
                            active_dict,
                            min_word_length,
                        )
                        if placed is None:
                            continue

                        for pos, ch in placed:
                            cells[pos] = ch
                            rem[ch] -= 1

                        if allow_duplicates:
                            dfs(rem_total - len(placed))
                        else:
                            words_now = _extract_raw_words(cells)
                            if len(words_now) == len(set(words_now)):
                                dfs(rem_total - len(placed))

                        for pos, ch in placed:
                            del cells[pos]
                            rem[ch] += 1

                        if _limit_reached():
                            return

    for seed in seed_words:
        if _limit_reached():
            break
        for i, ch in enumerate(seed):
            cells[(i, 0)] = ch
            rem[ch] -= 1
        dfs(total_tiles - len(seed))
        cells.clear()
        for ch in seed:
            rem[ch] += 1

    canonical_solutions.sort(key=score_board)

    if deduplicate_transpose:
        return (
            canonical_solutions[:max_solutions]
            if max_solutions is not None
            else canonical_solutions
        )

    expanded: list[Board] = []
    for board in canonical_solutions:
        expanded.append(board)
        transposed = board.transpose()
        if transposed != board:
            expanded.append(transposed)
        if max_solutions is not None and len(expanded) >= max_solutions:
            break

    return expanded[:max_solutions] if max_solutions is not None else expanded


def solve_qless_grid(
    letters: str,
    min_word_length: int = 3,
    *,
    dictionary: Optional[Dictionary] = None,
    max_solutions: Optional[int] = 10,
    allow_duplicates: bool = False,
    allow_single_word: bool = True,
    deduplicate_transpose: bool = True,
    timeout_seconds: Optional[float] = 5.0,
    max_nodes: Optional[int] = 200_000,
) -> list[GridSolution]:
    """Solve Q-Less and wrap resulting boards into ``GridSolution`` objects."""
    boards = solve_board(
        letters,
        dictionary=dictionary,
        min_word_length=min_word_length,
        max_solutions=max_solutions,
        allow_duplicates=allow_duplicates,
        allow_single_word=allow_single_word,
        deduplicate_transpose=deduplicate_transpose,
        timeout_seconds=timeout_seconds,
        max_nodes=max_nodes,
    )
    return [
        GridSolution(
            grid=Grid.from_board(board),
            used_letters=dict(board.letter_counts()),
        )
        for board in boards
    ]
