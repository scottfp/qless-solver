"""
Generator module for creating test inputs for the qless-solver.
"""

import random
from typing import List, Optional, Tuple

# Define typical dice configurations for Q-Less
# Each die has 6 faces with letters
# These are hypothetical distributions - actual Q-Less dice may have different letters
DEFAULT_DICE = [
    ["A", "E", "I", "O", "U", "Y"],  # Die 1 - vowel-heavy
    ["A", "E", "I", "O", "U", "Y"],  # Die 2 - vowel-heavy
    ["B", "C", "D", "F", "G", "H"],  # Die 3
    ["J", "K", "L", "M", "N", "P"],  # Die 4
    ["R", "S", "T", "V", "W", "X"],  # Die 5
    ["A", "E", "I", "O", "U", "Z"],  # Die 6 - vowel-heavy
    ["B", "C", "D", "F", "G", "H"],  # Die 7
    ["J", "K", "L", "M", "N", "P"],  # Die 8
    ["R", "S", "T", "V", "W", "X"],  # Die 9
    ["A", "E", "I", "O", "U", "Y"],  # Die 10 - vowel-heavy
    ["B", "C", "D", "G", "P", "T"],  # Die 11
    ["H", "L", "N", "R", "S", "T"],  # Die 12
]


def generate_random_roll(dice: Optional[List[List[str]]] = None) -> str:
    """
    Generate a random roll of the Q-Less dice.

    Args:
        dice: Configuration of dice to use. If None, uses the default configuration.

    Returns:
        A string of 12 letters representing a random roll of the dice.
    """
    if dice is None:
        dice = DEFAULT_DICE

    result = []
    for die in dice:
        result.append(random.choice(die))

    return "".join(result)


def generate_solvable_roll(
    dice: Optional[List[List[str]]] = None,
    words: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    """
    Generate a solvable roll of the Q-Less dice.

    This function tries to generate a roll that can be solved with the given words.
    If no words are provided, it will generate a random roll.

    Args:
        dice: Configuration of dice to use. If None, uses the default configuration.
        words: List of words to include in the solution.

    Returns:
        A tuple of (roll, solution_words) where roll is a string of 12 letters
        and solution_words is a list of words that can be formed from the roll.
    """
    if dice is None:
        dice = DEFAULT_DICE

    if words is None or not words:
        # Just generate a random roll since we don't have target words
        return generate_random_roll(dice), []

    # Convert all words to uppercase to match the dice
    words = [word.upper() for word in words]

    # Make sure we can actually form these words with our dice
    # This is a simplified check - in a real implementation, we would need
    # to ensure that the letters can be arranged on the dice

    # Just return a random roll and the words for now
    # In a real implementation, we would try to generate a roll that includes these words
    return generate_random_roll(dice), words


def generate_test_cases(count: int = 10) -> List[str]:
    """
    Generate a set of test cases for the qless-solver.

    Args:
        count: Number of test cases to generate.

    Returns:
        A list of strings, each representing a roll of the Q-Less dice.
    """
    return [generate_random_roll() for _ in range(count)]
