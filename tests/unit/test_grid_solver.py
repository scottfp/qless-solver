"""Comprehensive unit tests and benchmarks for the Q-Less grid solver."""

from __future__ import annotations

import random
import time
from collections import Counter

import pytest
from qless_solver.board import Board, validate_board
from qless_solver.dice import create_standard_dice_set
from qless_solver.dictionary import Dictionary
from qless_solver.grid_solver import (
    Grid,
    GridPosition,
    GridSolution,
    PlacedWord,
    score_board,
    solve_board,
    solve_qless_grid,
)


@pytest.fixture(scope="module")
def real_dict() -> Dictionary:
    """Real NWL dictionary loaded from dictionary.txt."""
    return Dictionary()


@pytest.fixture
def simple_dict() -> Dictionary:
    """Small focused dictionary for deterministic unit tests."""
    return Dictionary(words=["cat", "at", "a", "act", "car", "rat", "dog"])


# ---------------------------------------------------------------------------
# Grid / GridSolution schema and conversions
# ---------------------------------------------------------------------------


def test_grid_and_solution_board_round_trip() -> None:
    board = Board.from_rows(
        [
            ".p...",
            ".r.n.",
            "comet",
            ".n.x.",
            ".g.t.",
        ]
    ).translate(-4, 7)

    grid = Grid.from_board(board)
    assert grid.to_board() == board.normalize()
    assert {pw.word for pw in grid.words} == {"comet", "prong", "next"}
    assert (
        PlacedWord(word="comet", position=GridPosition(x=0, y=2, direction="across"))
        in grid.words
    )

    sol = GridSolution(grid=grid, used_letters=dict(board.letter_counts()))
    assert sol.to_board() == board.normalize()
    dumped = sol.model_dump()
    assert dumped["used_letters"] == dict(Counter("rmtoepngtnxc"))


# ---------------------------------------------------------------------------
# Small-dictionary solver behavior and input validation
# ---------------------------------------------------------------------------


def test_solve_board_small_dictionary_cases(simple_dict: Dictionary) -> None:
    # Single 3-letter word
    sols = solve_board("cat", dictionary=simple_dict, max_solutions=10)
    assert sols
    assert any({w.word for w in b.extract_runs()} == {"cat"} for b in sols) or any(
        {w.word for w in b.extract_runs()} == {"act"} for b in sols
    )
    for b in sols:
        assert validate_board(b, "cat", simple_dict).is_valid

    # Two intersecting words: "cat" + "dog" sharing nothing -> impossible; "cat" + "rat" sharing 'a' -> "cart"?
    cross_dict = Dictionary(words=["cat", "rat"])
    # "cat" + "rat" intersecting on 'a' or 't' -> "cartt" (c,a,t,r,t)
    cross_sols = solve_board("catrt", dictionary=cross_dict, max_solutions=10)
    assert len(cross_sols) > 0
    for b in cross_sols:
        res = validate_board(b, "catrt", cross_dict)
        assert res.is_valid, res.errors
        assert {w.word for w in res.words} == {"cat", "rat"}

    # No solution possible
    assert solve_board("xyz", dictionary=simple_dict) == []


def test_solve_board_invalid_and_edge_inputs(simple_dict: Dictionary) -> None:
    with pytest.raises(ValueError):
        solve_board("cat", dictionary=simple_dict, min_word_length=1)

    assert solve_board("", dictionary=simple_dict) == []
    assert solve_board("   ", dictionary=simple_dict) == []
    assert solve_board("ab", dictionary=simple_dict, min_word_length=3) == []
    assert solve_board("abc123", dictionary=simple_dict) == []
    assert solve_board("cat", dictionary=simple_dict, max_solutions=0) == []


# ---------------------------------------------------------------------------
# Real rolls, 12-letter words, cycles, traps, and canonical dedup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "roll",
    [
        "kobfldhimiph",  # test_roll_1.jpg
        "blyatarpwnmr",  # test_roll_2.jpg
        "adwilkhldmes",  # test_roll_3.jpg
        "rmtoepngtnxc",  # test_roll_4.jpg
    ],
)
def test_solve_board_real_photo_rolls(real_dict: Dictionary, roll: str) -> None:
    t0 = time.perf_counter()
    solutions = solve_board(
        roll,
        dictionary=real_dict,
        max_solutions=5,
        timeout_seconds=2.0,
    )
    elapsed = time.perf_counter() - t0

    assert len(solutions) >= 1
    assert elapsed < 2.0
    for board in solutions:
        res = validate_board(board, roll, real_dict)
        assert res.is_valid, f"Roll {roll} produced invalid board: {res.errors}"


def test_solve_board_single_12_letter_word_policy(real_dict: Dictionary) -> None:
    roll = "strawberries"

    allowed = solve_board(
        roll,
        dictionary=real_dict,
        max_solutions=5,
        allow_single_word=True,
        timeout_seconds=2.0,
    )
    assert len(allowed) >= 1
    # Ranked #1 because word count == 1 is minimal
    top_words = allowed[0].extract_runs()
    assert [w.word for w in top_words] == ["strawberries"]
    for b in allowed:
        assert validate_board(b, roll, real_dict, allow_single_word=True).is_valid

    disallowed = solve_board(
        roll,
        dictionary=real_dict,
        max_solutions=5,
        allow_single_word=False,
        timeout_seconds=2.0,
    )
    assert len(disallowed) >= 1
    for b in disallowed:
        res = validate_board(b, roll, real_dict, allow_single_word=False)
        assert res.is_valid, res.errors
        assert len(res.words) >= 2


def test_solve_board_finds_closed_hollow_cycle() -> None:
    cycle_dict = Dictionary(words=["cart", "cats", "tear", "star"])
    solutions = solve_board(
        "cartaetastar",
        dictionary=cycle_dict,
        max_solutions=10,
        timeout_seconds=2.0,
    )
    assert len(solutions) == 1
    res = validate_board(solutions[0], "cartaetastar", cycle_dict)
    assert res.is_valid, res.errors
    assert {w.word for w in res.words} == {"cart", "cats", "tear", "star"}


def test_solve_board_duplicate_word_policy() -> None:
    dup_dict = Dictionary(words=["cat"])
    assert solve_board("caatt", dictionary=dup_dict, allow_duplicates=False) == []

    allowed = solve_board("caatt", dictionary=dup_dict, allow_duplicates=True)
    assert len(allowed) == 1
    res = validate_board(allowed[0], "caatt", dup_dict, allow_duplicates=True)
    assert res.is_valid, res.errors
    assert [w.word for w in res.words] == ["cat", "cat"]


def test_solve_board_rejects_two_letter_parallel_trap() -> None:
    # Only valid words are 'bar', 'ores', 'stared', plus valid 2-letter words 'bo', 'ar', 're'.
    # A naive solver that forgets perpendicular 2-letter checks would emit parallel boards.
    trap_dict = Dictionary(words=["bar", "ores", "stared", "bo", "ar", "re"])
    assert solve_board("barorestared", dictionary=trap_dict) == []


def test_solve_board_canonical_deduplication_and_transpose_toggle() -> None:
    asym_dict = Dictionary(words=["comet", "prong", "next"])
    roll = "rmtoepngtnxc"

    deduped = solve_board(
        roll,
        dictionary=asym_dict,
        max_solutions=10,
        deduplicate_transpose=True,
    )
    assert len(deduped) == 1
    assert validate_board(deduped[0], roll, asym_dict).is_valid

    both = solve_board(
        roll,
        dictionary=asym_dict,
        max_solutions=10,
        deduplicate_transpose=False,
    )
    assert len(both) == 2
    assert both[0].canonical_key(include_transpose=False) != both[1].canonical_key(
        include_transpose=False
    )
    assert both[0].canonical_key(include_transpose=True) == both[1].canonical_key(
        include_transpose=True
    )
    for b in both:
        assert validate_board(b, roll, asym_dict).is_valid


def test_solve_board_unsolvable_rolls_return_empty_promptly(
    real_dict: Dictionary, simple_dict: Dictionary
) -> None:
    t0 = time.perf_counter()
    assert solve_board("bcdfghjklmnp", dictionary=real_dict, timeout_seconds=1.0) == []
    assert solve_board("catz", dictionary=simple_dict, timeout_seconds=1.0) == []
    assert solve_board("bcdfghjklmna", dictionary=real_dict, timeout_seconds=1.0) == []
    assert time.perf_counter() - t0 < 2.0


def test_solve_board_limits_and_ranking(real_dict: Dictionary) -> None:
    roll = "rmtoepngtnxc"

    sols_one = solve_board(roll, dictionary=real_dict, max_solutions=1)
    assert len(sols_one) == 1

    sols_three = solve_board(roll, dictionary=real_dict, max_solutions=3)
    assert 1 <= len(sols_three) <= 3
    scores = [score_board(b) for b in sols_three]
    assert scores == sorted(scores)

    # All canonical keys are distinct
    keys = [b.canonical_key() for b in sols_three]
    assert len(keys) == len(set(keys))

    # Very tight node budget returns cleanly without raising
    limited = solve_board(roll, dictionary=real_dict, max_solutions=10, max_nodes=1)
    assert len(limited) <= 10
    for b in limited:
        assert validate_board(b, roll, real_dict).is_valid


def test_solve_qless_grid_wrapper_and_monkeypatch(
    monkeypatch: pytest.MonkeyPatch, simple_dict: Dictionary
) -> None:
    monkeypatch.setattr("qless_solver.grid_solver.Dictionary", lambda: simple_dict)

    solutions = solve_qless_grid(letters="cat", min_word_length=3)
    assert len(solutions) >= 1
    assert any(
        len(sol.grid.words) == 1
        and sol.grid.words[0].word == "cat"
        and sol.used_letters == {"c": 1, "a": 1, "t": 1}
        for sol in solutions
    )

    assert solve_qless_grid(letters="xyz", min_word_length=3) == []


def test_solve_board_seeded_random_dice_rolls_benchmark(
    real_dict: Dictionary,
) -> None:
    rng = random.Random(42)
    dice_set = create_standard_dice_set()
    rolls = [
        "".join(rng.choice(die.sides) for die in dice_set.dice).lower()
        for _ in range(10)
    ]

    solved_count = 0
    t0 = time.perf_counter()
    for roll in rolls:
        boards = solve_board(
            roll,
            dictionary=real_dict,
            max_solutions=3,
            timeout_seconds=1.5,
        )
        if boards:
            solved_count += 1
        for board in boards:
            res = validate_board(board, roll, real_dict)
            assert (
                res.is_valid
            ), f"Invalid solution for random roll {roll}: {res.errors}"
    elapsed = time.perf_counter() - t0

    assert solved_count >= 5
    assert elapsed < 10.0


def test_solve_board_excludes_primary_words(real_dict: Dictionary) -> None:
    baseline = solve_board("rmtoepngtnxc", dictionary=real_dict, max_solutions=3)
    assert baseline
    assert any(w.word == "context" for w in baseline[0].extract_runs(min_length=2))

    filtered = solve_board(
        "rmtoepngtnxc",
        dictionary=real_dict,
        max_solutions=5,
        excluded_words=["CONTEXT"],
    )
    assert filtered
    for board in filtered:
        res = validate_board(board, "rmtoepngtnxc", real_dict)
        assert res.is_valid, res.errors
        assert all(w.word != "context" for w in res.words)


def test_solve_board_excludes_perpendicular_cross_words() -> None:
    # Placing down words side-by-side forms perpendicular cross-word "pot" in row 1
    # even when "pot" itself is removed from primary candidates.
    cross_dict = Dictionary(words=["bar", "pot", "ant", "bpa", "aon", "rtt"])
    baseline = solve_board("barpotant", dictionary=cross_dict, max_solutions=5)
    assert len(baseline) == 1
    assert any(w.word == "pot" for w in baseline[0].extract_runs(min_length=2))

    blocked = solve_board(
        "barpotant",
        dictionary=cross_dict,
        max_solutions=5,
        excluded_words=["pot"],
    )
    assert blocked == []


def test_solve_board_excluding_all_candidates_returns_empty() -> None:
    tiny_dict = Dictionary(words=["cat"])
    assert solve_board("cat", dictionary=tiny_dict, excluded_words=["cat"]) == []
