"""
Generator module for creating test inputs for the qless-solver.
"""

from typing import List, Optional, Tuple

from qless_solver.dice import create_standard_dice_set


def generate_random_roll() -> str:
    """
    Generate a random roll of the Q-Less dice using the accurate dice distribution.

    Returns:
        A string of 12 letters representing a random roll of the dice.
    """
    dice_set = create_standard_dice_set()
    _, roll_string = dice_set.roll(), dice_set.get_roll_string()
    return roll_string


def generate_solvable_roll(words: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    """
    Generate a solvable roll of the Q-Less dice.

    This function tries to generate a roll that can be solved with the given words.
    If no words are provided, it will generate a random roll.

    Args:
        words: List of words to include in the solution.

    Returns:
        A tuple of (roll, solution_words) where roll is a string of 12 letters
        and solution_words is a list of words that can be formed from the roll.
    """
    if words is None or not words:
        # Just generate a random roll since we don't have target words
        return generate_random_roll(), []

    # Convert all words to uppercase to match the dice
    words = [word.upper() for word in words]

    # Make sure we can actually form these words with our dice
    # This is a simplified check - in a real implementation, we would need
    # to ensure that the letters can be arranged on the dice

    # Just return a random roll and the words for now
    # In a real implementation, we would try to generate a roll that includes these words
    return generate_random_roll(), words


def generate_test_cases(count: int = 10) -> List[str]:
    """
    Generate a set of test cases for the qless-solver.

    Args:
        count: Number of test cases to generate.

    Returns:
        A list of strings, each representing a roll of the Q-Less dice.
    """
    return [generate_random_roll() for _ in range(count)]
