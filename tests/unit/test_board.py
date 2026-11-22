"""Extensive unit and edge-case tests for Board, canonicalization, and validate_board."""

from __future__ import annotations

from collections import Counter

import pytest
from pydantic import ValidationError
from qless_solver.board import Board, BoardWord, validate_board
from qless_solver.dictionary import Dictionary


@pytest.fixture(scope="module")
def real_dict() -> Dictionary:
    """Real NWL dictionary loaded from dictionary.txt."""
    return Dictionary()


@pytest.fixture
def small_dict() -> Dictionary:
    """Focused dictionary for isolated geometric and policy edge-case tests."""
    return Dictionary(
        words=[
            "cat",
            "cats",
            "dog",
            "dogs",
            "at",
            "to",
            "of",
            "are",
            "ten",
            "car",
            "tea",
            "rat",
            "art",
            "tar",
            "net",
            "star",
            "cart",
            "tear",
            "eat",
            "ran",
            "ant",
            "tan",
            "bar",
            "ore",
            "ores",
            "stared",
            "bo",
            "ar",
            "re",
            "wray",
            "pantry",
            "lamb",
        ]
    )


def _rotate_90_cw(board: Board) -> Board:
    """Rotate normalized board 90 degrees clockwise: (x, y) -> (-y, x)."""
    return Board(cells={(-y, x): ch for (x, y), ch in board.cells.items()}).normalize()


def _rotate_180(board: Board) -> Board:
    """Rotate normalized board 180 degrees: (x, y) -> (-x, -y)."""
    return Board(cells={(-x, -y): ch for (x, y), ch in board.cells.items()}).normalize()


def _flip_horizontal(board: Board) -> Board:
    """Mirror board left-to-right: (x, y) -> (-x, y)."""
    return Board(cells={(-x, y): ch for (x, y), ch in board.cells.items()}).normalize()


def _flip_vertical(board: Board) -> Board:
    """Mirror board top-to-bottom: (x, y) -> (x, -y)."""
    return Board(cells={(x, -y): ch for (x, y), ch in board.cells.items()}).normalize()


# ---------------------------------------------------------------------------
# Board construction, rendering, and validation of cell values
# ---------------------------------------------------------------------------


def test_board_empty_properties() -> None:
    empty = Board()
    assert empty.cells == {}
    assert empty.bounds() is None
    assert empty.dimensions() == (0, 0)
    assert empty.to_rows() == []
    assert empty.to_ascii() == ""
    assert empty.normalize() == empty
    assert empty.translate(3, -4) == empty
    assert empty.transpose() == empty
    assert empty.canonical_key() == ()
    assert empty.canonical() == empty
    assert empty.is_connected() is False
    assert empty.extract_runs() == []


def test_board_from_rows_and_rendering_round_trip() -> None:
    rows = [
        ".P...",
        ".R.N.",
        "COMET",
        ".N.X.",
        ".G.T.",
    ]
    board = Board.from_rows(rows)
    assert board.bounds() == (0, 0, 4, 4)
    assert board.dimensions() == (5, 5)
    assert board.to_rows() == [
        ".p...",
        ".r.n.",
        "comet",
        ".n.x.",
        ".g.t.",
    ]
    assert board.to_ascii() == "\n".join(board.to_rows())
    assert board.to_ascii(empty_char=" ") == (
        " p   \n" " r n \n" "comet\n" " n x \n" " g t "
    )


def test_board_from_rows_ragged_spaces_and_custom_empty_char() -> None:
    board = Board.from_rows(["  c a ", "cat", "_at"], empty_char="_")
    # Row 0: (2,0)=c, (4,0)=a (spaces skipped)
    # Row 1: (0,1)=c, (1,1)=a, (2,1)=t
    # Row 2: (1,2)=a, (2,2)=t ('_' skipped)
    assert board.cells[(2, 0)] == "c"
    assert board.cells[(4, 0)] == "a"
    assert board.cells[(0, 1)] == "c"
    assert (0, 2) not in board.cells
    assert board.dimensions() == (5, 3)


def test_board_negative_and_sparse_coordinates() -> None:
    board = Board(cells={(-100, -50): "C", (-99, -50): "a", (-98, -50): "T"})
    assert board.bounds() == (-100, -50, -98, -50)
    assert board.dimensions() == (3, 1)
    assert board.to_rows() == ["cat"]
    norm = board.normalize()
    assert norm.cells == {(0, 0): "c", (1, 0): "a", (2, 0): "t"}


@pytest.mark.parametrize("bad_char", ["", "ab", "1", "?", ".", " ", "é"])
def test_board_rejects_invalid_cell_values(bad_char: str) -> None:
    with pytest.raises(ValidationError):
        Board(cells={(0, 0): bad_char})


@pytest.mark.parametrize("bad_char", ["1", "?", "é"])
def test_board_from_rows_rejects_invalid_characters(bad_char: str) -> None:
    with pytest.raises(ValidationError):
        Board.from_rows([f"ca{bad_char}"])


def test_board_rejects_non_single_empty_char() -> None:
    with pytest.raises(ValueError):
        Board.from_rows(["cat"], empty_char="..")
    with pytest.raises(ValueError):
        Board.from_rows(["cat"]).to_rows(empty_char="")


# ---------------------------------------------------------------------------
# Normalization, transpose, and canonical deduplication
# ---------------------------------------------------------------------------


def test_canonical_key_translation_invariance() -> None:
    base = Board.from_rows([".p...", ".r.n.", "comet", ".n.x.", ".g.t."])
    assert base.translate(0, 0) == base
    shifted_pos = base.translate(12, 7)
    shifted_neg = base.translate(-5, -9)

    assert (
        base.canonical_key()
        == shifted_pos.canonical_key()
        == shifted_neg.canonical_key()
    )
    assert base.canonical_key(include_transpose=False) == shifted_neg.canonical_key(
        include_transpose=False
    )
    assert shifted_neg.normalize() == base


def test_canonical_key_transpose_invariance_and_flag() -> None:
    board_a = Board.from_rows(
        [
            ".p...",
            ".r.n.",
            "comet",
            ".n.x.",
            ".g.t.",
        ]
    )
    board_b = Board.from_rows(
        [
            "..c..",
            "prong",
            "..m..",
            ".next",
            "..t..",
        ]
    )

    assert board_a.transpose() == board_b
    assert board_b.transpose() == board_a
    assert board_a.canonical_key(include_transpose=True) == board_b.canonical_key(
        include_transpose=True
    )
    assert board_a.canonical_key(include_transpose=False) != board_b.canonical_key(
        include_transpose=False
    )

    # Translation + transpose combined should still collapse to the same canonical key
    shifted_transposed = board_b.translate(-10, 42)
    assert shifted_transposed.canonical_key() == board_a.canonical_key()

    # Canonicalization is idempotent
    canon = board_a.canonical()
    assert canon.canonical() == canon


def test_canonical_key_distinguishes_rotations_and_reflections() -> None:
    board = Board.from_rows(
        [
            ".p...",
            ".r.n.",
            "comet",
            ".n.x.",
            ".g.t.",
        ]
    )
    rot90 = _rotate_90_cw(board)
    rot180 = _rotate_180(board)
    hflip = _flip_horizontal(board)
    vflip = _flip_vertical(board)

    # Without transpose equivalence, all 5 orientations are distinct
    no_transpose_keys = {
        board.canonical_key(include_transpose=False),
        rot90.canonical_key(include_transpose=False),
        rot180.canonical_key(include_transpose=False),
        hflip.canonical_key(include_transpose=False),
        vflip.canonical_key(include_transpose=False),
    }
    assert len(no_transpose_keys) == 5

    # With transpose equivalence, rot90_cw and vflip are transpose twins,
    # while none of the invalid reflections/rotations collide with the original board.
    assert rot90.canonical_key() == vflip.canonical_key()
    assert board.canonical_key() not in {
        rot90.canonical_key(),
        rot180.canonical_key(),
        hflip.canonical_key(),
        vflip.canonical_key(),
    }
    assert (
        len(
            {
                board.canonical_key(),
                rot90.canonical_key(),
                rot180.canonical_key(),
                hflip.canonical_key(),
            }
        )
        == 4
    )


def test_canonical_key_self_transpose_symmetric_board() -> None:
    symmetric = Board.from_rows(
        [
            "cat",
            "are",
            "ten",
        ]
    )
    assert symmetric.transpose() == symmetric
    assert symmetric.canonical_key(include_transpose=True) == symmetric.canonical_key(
        include_transpose=False
    )


# ---------------------------------------------------------------------------
# Run extraction & 4-connectivity
# ---------------------------------------------------------------------------


def test_extract_runs_separates_gaps_and_ignores_singletons() -> None:
    board = Board.from_rows(
        [
            "cat.dog",
            "a......",
            "r......",
        ]
    )
    runs = board.extract_runs(min_length=2)
    assert runs == [
        BoardWord(word="cat", x=0, y=0, direction="across"),
        BoardWord(word="dog", x=4, y=0, direction="across"),
        BoardWord(word="car", x=0, y=0, direction="down"),
    ]
    assert runs[0].cells() == ((0, 0), (1, 0), (2, 0))
    assert runs[2].cells() == ((0, 0), (0, 1), (0, 2))


def test_extract_runs_dense_block_and_single_cell() -> None:
    single = Board.from_rows(["a"])
    assert single.extract_runs(min_length=2) == []

    dense = Board.from_rows(
        [
            "cat",
            "are",
            "ten",
        ]
    )
    runs = dense.extract_runs(min_length=2)
    assert [(r.direction, r.word) for r in runs] == [
        ("across", "cat"),
        ("across", "are"),
        ("across", "ten"),
        ("down", "cat"),
        ("down", "are"),
        ("down", "ten"),
    ]


def test_is_connected_cases() -> None:
    # Single tile and connected shapes
    assert Board.from_rows(["a"]).is_connected() is True
    assert Board.from_rows(["cat"]).is_connected() is True
    assert (
        Board.from_rows(
            [
                "cart",
                "a..e",
                "t..a",
                "star",
            ]
        ).is_connected()
        is True
    )

    # Disconnected by 1 empty column
    assert Board.from_rows(["cat.dog"]).is_connected() is False
    # Disconnected by 1 empty row
    assert Board.from_rows(["cat", "...", "dog"]).is_connected() is False
    # Diagonal-only contact must NOT count as connected
    assert (
        Board.from_rows(
            [
                "cat...",
                "...dog",
            ]
        ).is_connected()
        is False
    )
    # Single diagonal stray tile
    assert (
        Board.from_rows(
            [
                "cat.",
                "...s",
            ]
        ).is_connected()
        is False
    )


# ---------------------------------------------------------------------------
# Valid Q-Less boards against real dictionary.txt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rows,letters,expected_words",
    [
        (
            [
                ".f...",
                "kohl.",
                ".b.i.",
                "...p.",
                "..him",
                "...d.",
            ],
            "kobfldhimiph",
            {"kohl", "him", "fob", "lipid"},
        ),
        (
            [
                "....s.",
                "....h.",
                "....a.",
                ".l..k.",
                "mildew",
                ".d....",
            ],
            "adwilkhldmes",
            {"mildew", "lid", "shake"},
        ),
        (
            [
                ".p...",
                ".r.n.",
                "comet",
                ".n.x.",
                ".g.t.",
            ],
            "rmtoepngtnxc",
            {"comet", "prong", "next"},
        ),
    ],
)
def test_validate_real_photo_grids(
    real_dict: Dictionary,
    rows: list[str],
    letters: str,
    expected_words: set[str],
) -> None:
    board = Board.from_rows(rows)
    result = validate_board(board, letters, real_dict)
    assert result.is_valid is True, result.errors
    assert result.errors == []
    assert {w.word for w in result.words} == expected_words
    # Intersections mean total word letter sum strictly exceeds tile count (12)
    assert sum(len(w.word) for w in result.words) > 12


def test_validate_real_grid_2_missing_wray_vs_custom_dict(
    real_dict: Dictionary, small_dict: Dictionary
) -> None:
    rows = [
        ".....w",
        ".....r",
        ".l...a",
        "pantry",
        ".m....",
        ".b....",
    ]
    board = Board.from_rows(rows)
    letters = "blyatarpwnmr"

    real_res = validate_board(board, letters, real_dict)
    assert real_res.is_valid is False
    assert any("wray" in err for err in real_res.errors)

    custom_res = validate_board(board, letters, small_dict)
    assert custom_res.is_valid is True, custom_res.errors
    assert {w.word for w in custom_res.words} == {"pantry", "lamb", "wray"}


def test_validate_single_12_letter_word_policy(real_dict: Dictionary) -> None:
    horiz = Board.from_rows(["strawberries"])
    vert = Board.from_rows(list("strawberries"))
    letters = "strawberries"

    for board in (horiz, vert):
        res_allowed = validate_board(board, letters, real_dict, allow_single_word=True)
        assert res_allowed.is_valid is True, res_allowed.errors
        assert [w.word for w in res_allowed.words] == ["strawberries"]

        res_disallowed = validate_board(
            board, letters, real_dict, allow_single_word=False
        )
        assert res_disallowed.is_valid is False
        assert any("two intersecting words" in err for err in res_disallowed.errors)


def test_validate_closed_hollow_cycle_board(real_dict: Dictionary) -> None:
    # 12 tiles forming a closed 4x4 loop with 4 intersections
    cycle = Board.from_rows(
        [
            "cart",
            "a..e",
            "t..a",
            "star",
        ]
    )
    letters = "cartaetastar"
    assert len(cycle.cells) == 12
    assert Counter(letters) == cycle.letter_counts()

    result = validate_board(cycle, letters, real_dict)
    assert result.is_valid is True, result.errors
    assert {w.word for w in result.words} == {"cart", "star", "cats", "tear"}


def test_validate_dense_3x3_parallel_square_with_tail(real_dict: Dictionary) -> None:
    # 12 tiles forming 3 parallel horizontal words and 3 vertical words (6 distinct words)
    dense = Board.from_rows(
        [
            "cow",
            "are",
            "bed",
            "..d",
            "..e",
            "..d",
        ]
    )
    letters = "cowarebedded"
    assert len(dense.cells) == 12
    result = validate_board(dense, letters, real_dict)
    assert result.is_valid is True, result.errors
    assert {w.word for w in result.words} == {
        "cow",
        "are",
        "bed",
        "cab",
        "ore",
        "wedded",
    }


def test_validate_translated_transposed_and_uppercase_letters(
    real_dict: Dictionary,
) -> None:
    base = Board.from_rows([".p...", ".r.n.", "comet", ".n.x.", ".g.t."])
    translated_transposed = base.transpose().translate(-12, 8)
    result = validate_board(translated_transposed, "  RMTOEPNGTNXC  ", real_dict)
    assert result.is_valid is True, result.errors


# ---------------------------------------------------------------------------
# Edge-case traps: 2-letter runs, merges, orientation, tiles, connectivity, dupes
# ---------------------------------------------------------------------------


def test_invalid_parallel_words_forming_valid_english_2_letter_runs(
    real_dict: Dictionary,
) -> None:
    # 'bar' directly above 'ores' forms vertical 'bo', 'ar', 're' (all valid Scrabble 2-letter words!)
    board = Board.from_rows(
        [
            ".bar.",
            ".ores",
            "....t",
            "....a",
            "....r",
            "....e",
            "....d",
        ]
    )
    letters = "barorestared"
    assert len(board.cells) == 12

    result = validate_board(board, letters, real_dict)
    assert result.is_valid is False
    for two_letter in ("bo", "ar", "re"):
        assert any(
            f"'{two_letter}'" in err and "shorter than minimum length 3" in err
            for err in result.errors
        )


def test_invalid_parallel_words_forming_nonsense_2_letter_runs(
    real_dict: Dictionary,
) -> None:
    board = Board.from_rows(
        [
            "cat..",
            "dogs.",
            "...t.",
            "...a.",
            "...r.",
            "...e.",
            "...d.",
        ]
    )
    letters = "catdogstared"
    assert len(board.cells) == 12

    result = validate_board(board, letters, real_dict)
    assert result.is_valid is False
    for two_letter in ("cd", "ao", "tg"):
        assert any(f"'{two_letter}'" in err for err in result.errors)


def test_invalid_explicit_2_letter_word_and_grazing_parallel(
    real_dict: Dictionary,
    small_dict: Dictionary,
) -> None:
    # 'mildew' + 'shakes' shifted right by 1 row touching only at col 5 ('ws' 2-letter run)
    grazing = Board.from_rows(
        [
            "mildew.....",
            ".....shakes",
        ]
    )
    assert len(grazing.cells) == 12
    res_grazing = validate_board(grazing, "mildewshakes", real_dict)
    assert res_grazing.is_valid is False
    assert any("'ws'" in err for err in res_grazing.errors)

    # Explicit valid 2-letter word 'to' attached to valid intersecting words
    hook = Board.from_rows(
        [
            "cat",
            ".r.",
            ".to",
        ]
    )
    res_hook = validate_board(hook, "catrto", small_dict)
    assert res_hook.is_valid is False
    assert any(
        "'to'" in err and "shorter than minimum length 3" in err
        for err in res_hook.errors
    )


def test_invalid_merged_words_and_1_letter_extension(
    real_dict: Dictionary,
    small_dict: Dictionary,
) -> None:
    # Two valid words ('cat' + 'dog') placed end-to-end with no gap -> 'catdog'
    merged = Board.from_rows(
        [
            "...c..",
            "...h..",
            "...a..",
            "...r..",
            "...t..",
            "...e..",
            "catdog",
        ]
    )
    assert len(merged.cells) == 12
    res_merged = validate_board(merged, "chartedcatog", real_dict)
    assert res_merged.is_valid is False
    assert any("Invalid word 'catdog'" in err for err in res_merged.errors)

    # Valid word accidentally extended by a perpendicular word's letter ('cat' + 'd' -> 'catd')
    ext = Board.from_rows(
        [
            "catd..",
            "...o..",
            "...g..",
        ]
    )
    res_ext = validate_board(ext, "catdog", small_dict)
    assert res_ext.is_valid is False
    assert any("Invalid word 'catd'" in err for err in res_ext.errors)


def test_invalid_reversed_rotations_reflections_and_bent_words(
    real_dict: Dictionary,
) -> None:
    # Reversed right-to-left ('temoc') and bottom-to-top ('gnorp')
    valid = Board.from_rows([".p...", ".r.n.", "comet", ".n.x.", ".g.t."])
    letters = "rmtoepngtnxc"

    for transformed in (
        _rotate_90_cw(valid),
        _rotate_180(valid),
        _flip_horizontal(valid),
        _flip_vertical(valid),
    ):
        res = validate_board(transformed, letters, real_dict)
        assert res.is_valid is False
        assert any("Invalid word" in err for err in res.errors)

    # Bent L-shaped 3 tiles: looks like 'cat' bent around a corner, actually two 2-letter runs 'ca' & 'at'
    bent = Board.from_rows(
        [
            "ca",
            ".t",
        ]
    )
    res_bent = validate_board(bent, "cat", real_dict)
    assert res_bent.is_valid is False
    assert any("'ca'" in err for err in res_bent.errors)
    assert any("'at'" in err for err in res_bent.errors)


def test_invalid_tile_conservation_cases(real_dict: Dictionary) -> None:
    board = Board.from_rows([".p...", ".r.n.", "comet", ".n.x.", ".g.t."])

    # Missing die on board (board has 12 tiles, letters has 13)
    res_missing = validate_board(board, "rmtoepngtnxcz", real_dict)
    assert res_missing.is_valid is False
    assert any("Missing letters" in err and "z" in err for err in res_missing.errors)

    # Extra die on board (board has 12 tiles, letters has 11)
    res_extra = validate_board(board, "rmtoepngtnx", real_dict)
    assert res_extra.is_valid is False
    assert any(
        "Extra or unexpected letters" in err and "c" in err for err in res_extra.errors
    )

    # Right total count (12), wrong multiplicity (two 'c's instead of two 't's)
    res_mult = validate_board(board, "rmcoepngcnxt", real_dict)
    assert res_mult.is_valid is False
    assert any("Missing letters" in err and "c" in err for err in res_mult.errors)
    assert any(
        "Extra or unexpected letters" in err and "t" in err for err in res_mult.errors
    )

    # Empty board & invalid letters
    assert validate_board(Board(), "rmtoepngtnxc", real_dict).is_valid is False
    assert validate_board(board, "", real_dict).is_valid is False
    assert validate_board(board, "abc123", real_dict).is_valid is False

    # Single-cell board with single letter (conservation passes, connectivity passes, no >=3 word)
    single = Board.from_rows(["a"])
    res_single = validate_board(single, "a", real_dict)
    assert res_single.is_valid is False
    assert any("no words of length >= 3" in err for err in res_single.errors)


def test_invalid_connectivity_traps(real_dict: Dictionary) -> None:
    # Two valid 6-letter words using all 12 letters separated by an empty row
    gap_row = Board.from_rows(
        [
            "pantry",
            "......",
            "mildew",
        ]
    )
    res_gap = validate_board(gap_row, "pantrymildew", real_dict)
    assert res_gap.is_valid is False
    assert any("not orthogonally connected" in err for err in res_gap.errors)

    # Two valid 6-letter words touching diagonally at a corner
    diagonal = Board.from_rows(
        [
            "pantry......",
            "......mildew",
        ]
    )
    res_diag = validate_board(diagonal, "pantrymildew", real_dict)
    assert res_diag.is_valid is False
    assert any("not orthogonally connected" in err for err in res_diag.errors)


def test_invalid_duplicate_words_policy(
    real_dict: Dictionary, small_dict: Dictionary
) -> None:
    # Case 1: 'cat' across + 'cat' down sharing 'c'
    corner_dup = Board.from_rows(
        [
            "cat",
            "a..",
            "t..",
        ]
    )
    res_disallowed = validate_board(
        corner_dup, "caatt", small_dict, allow_duplicates=False
    )
    assert res_disallowed.is_valid is False
    assert any("Duplicate word 'cat'" in err for err in res_disallowed.errors)

    res_allowed = validate_board(corner_dup, "caatt", small_dict, allow_duplicates=True)
    assert res_allowed.is_valid is True, res_allowed.errors

    # Case 2: Two separate 'cat's connected via a bridge word ('area')
    bridged_dup = Board.from_rows(
        [
            "cat",
            ".r.",
            ".e.",
            "cat",
        ]
    )
    res_bridge_bad = validate_board(
        bridged_dup, "catrecat", real_dict, allow_duplicates=False
    )
    assert res_bridge_bad.is_valid is False
    assert any(
        "Duplicate word 'cat' appears 2 times" in err for err in res_bridge_bad.errors
    )
    res_bridge_ok = validate_board(
        bridged_dup, "catrecat", real_dict, allow_duplicates=True
    )
    assert res_bridge_ok.is_valid is True, res_bridge_ok.errors

    # Case 3: Symmetric 3x3 word square where across words == down words
    sym_square = Board.from_rows(
        [
            "cat",
            "are",
            "ten",
        ]
    )
    res_sym_bad = validate_board(
        sym_square, "catareten", real_dict, allow_duplicates=False
    )
    assert res_sym_bad.is_valid is False
    for word in ("are", "cat", "ten"):
        assert any(
            f"Duplicate word '{word}' appears 2 times" in err
            for err in res_sym_bad.errors
        )
    res_sym_ok = validate_board(
        sym_square, "catareten", real_dict, allow_duplicates=True
    )
    assert res_sym_ok.is_valid is True, res_sym_ok.errors


def test_validate_reports_multiple_simultaneous_errors(real_dict: Dictionary) -> None:
    # Disconnected + missing letters + 2-letter run + invalid word
    broken = Board.from_rows(
        [
            "qz...",
            ".....",
            "xyz..",
        ]
    )
    res = validate_board(broken, "abcdefghijkl", real_dict)
    assert res.is_valid is False
    assert any("Missing letters" in err for err in res.errors)
    assert any("Extra or unexpected letters" in err for err in res.errors)
    assert any("not orthogonally connected" in err for err in res.errors)
    assert any("shorter than minimum length 3" in err for err in res.errors)
    assert any("Invalid word 'xyz'" in err for err in res.errors)
