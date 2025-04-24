# Qless Solver - Grid-Based Word Placement Design Document

## 1. Introduction

This document outlines the design for enhancing the Qless solver to handle grid-based word placement constraints. The solver needs to find arrangements of words that connect in valid ways, similar to a Scrabble board.

## 2. Current Implementation

After examining the existing codebase, I found:

- **Dictionary Module**: Already implemented with the NWL2023.txt integration
- **Solver Module**: Has a simple implementation that finds combinations of words using all available letters, but lacks grid-based placement logic
- **Solution Class**: Represents a solution as a list of words and letter usage counts

The current solver uses backtracking to find combinations of words that use all available letters, but doesn't verify if these words can be legally arranged in a grid where they intersect properly.

## 3. Proposed Extensions

### 3.1 Grid Representation

```python
class GridPosition(BaseModel):
    x: int
    y: int
    direction: str = "across"  # "across" or "down"

class PlacedWord(BaseModel):
    word: str
    position: GridPosition

class Grid(BaseModel):
    cells: Dict[Tuple[int, int], str] = Field(default_factory=dict)
    words: List[PlacedWord] = Field(default_factory=list)

    def place_word(self, word: str, position: GridPosition) -> bool:
        """Place a word on the grid, returning True if successful"""
        # Validate placement
        # Update cells
        # Add to words list

    def validate_placement(self, word: str, position: GridPosition) -> bool:
        """Check if word placement is valid"""
        # Check if word fits in grid
        # Check if word connects to existing words
        # Check if all intersections form valid words
        # Check for no invalid 1-2 letter words

    def get_anchor_points(self) -> List[GridPosition]:
        """Find positions where new words can be anchored"""
        # For each letter on the grid, find potential word placements
```

### 3.2 Enhanced Solver Algorithm

```python
def solve_qless_grid(
    letters: str,
    min_word_length: int = 3,
) -> List[GridSolution]:
    """Solve Qless with grid placement constraints"""
    # Generate candidate words
    possible_words = get_valid_words(letters, min_length=min_word_length)

    # Sort words by potential (length, rare letters, etc.)
    sorted_words = sort_words_by_potential(possible_words)

    # Find grid-valid solutions
    solutions = find_grid_solutions(sorted_words, Counter(letters), min_word_length)

    return solutions
```

### 3.3 Grid-Based Backtracking

```python
def find_grid_solutions(
    possible_words: List[str],
    available_letters: Counter,
    min_word_length: int
) -> List[GridSolution]:
    """Find solutions with valid grid arrangements"""
    solutions = []

    def backtrack(
        grid: Grid,
        remaining_letters: Counter,
        used_words: Set[str],
    ) -> None:
        # If few enough letters remain, consider this a solution
        if sum(remaining_letters.values()) < 3:  # Can't form valid words with < 3 letters
            solutions.append(GridSolution(grid=grid.copy(), used_letters=original_letters - remaining_letters))
            return

        # Get possible anchor points
        anchor_points = grid.get_anchor_points()

        # For each anchor point, try placing valid words
        for point in anchor_points:
            for word in possible_words:
                if word in used_words:
                    continue

                # Check if word can be formed with remaining letters
                word_counter = Counter(word)
                if not all(word_counter[letter] <= remaining_letters[letter] for letter in word_counter):
                    continue

                # Check if placement is valid
                if grid.validate_placement(word, point):
                    # Place the word
                    grid.place_word(word, point)
                    used_words.add(word)

                    # Update remaining letters
                    for letter, count in word_counter.items():
                        remaining_letters[letter] -= count

                    # Recursively continue
                    backtrack(grid, remaining_letters, used_words)

                    # Backtrack
                    grid.remove_word(word, point)
                    used_words.remove(word)
                    for letter, count in word_counter.items():
                        remaining_letters[letter] += count

    # Start with an empty grid and the first word
    for word in sorted_words[:10]:  # Limit to reasonable starting words
        grid = Grid()
        initial_position = GridPosition(x=0, y=0, direction="across")
        grid.place_word(word, initial_position)

        word_counter = Counter(word)
        remaining = available_letters.copy()
        for letter, count in word_counter.items():
            remaining[letter] -= count

        backtrack(grid, remaining, {word})

    return solutions
```

### 3.4 Solution Scoring and Ranking

```python
def score_solution(solution: GridSolution) -> float:
    """Score a solution based on various factors"""
    # Count unused letters (fewer is better)
    unused_letter_count = sum(solution.remaining_letters.values())

    # Count words (fewer is better)
    word_count = len(solution.grid.words)

    # Calculate grid compactness
    compactness = calculate_grid_compactness(solution.grid)

    # Combined score - lower is better
    return unused_letter_count + (word_count * 2) - compactness
```

## 4. Implementation Plan

1. **Grid Class Development**
   - Create Grid and related classes
   - Implement word placement logic
   - Develop validation methods
   - Add methods to find anchor points

2. **Solver Enhancement**
   - Extend the current solver with grid-based backtracking
   - Implement heuristics for word selection and ordering
   - Add early pruning strategies

3. **Integration and Testing**
   - Update solver interface to support grid-based solutions
   - Create visualization methods for grid-based solutions
   - Develop tests for grid validation

4. **Optimization**
   - Profile and optimize the core algorithm
   - Implement letter usage statistics to prioritize certain placements
   - Add caching for performance improvements

## 5. Existing vs. New Components

### Already Implemented:
- Dictionary loading and word validation
- Basic backtracking framework for finding word combinations
- Solution modeling (though needs extension)

### To Be Implemented:
- Grid representation and manipulation
- Grid-based word placement validation
- Enhanced backtracking with spatial constraints
- Solution scoring and ranking
- Visualization of the grid-based solutions

## 6. Challenges and Considerations

1. **Performance**: Grid-based validation adds significant computational complexity
   - Mitigation: Aggressive pruning, heuristic-based search ordering

2. **Memory Usage**: Storing many potential grid configurations can be memory-intensive
   - Mitigation: Limit solution space exploration, eliminate unpromising branches early

3. **Algorithm Completeness**: Finding all possible solutions may be impractical
   - Mitigation: Focus on finding a reasonable set of high-quality solutions
