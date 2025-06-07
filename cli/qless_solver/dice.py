"""
Dice module for the Q-Less game.

This module contains the representation of the Q-Less dice and functions
to manipulate them.
"""

import random
from typing import Dict, List, Optional, Tuple

try:  # Support both Pydantic v1 and v2
    from pydantic import BaseModel, Field, field_validator
    PYDANTIC_V2 = True
except ImportError:  # pragma: no cover - fallback for older Pydantic
    from pydantic import BaseModel, Field, validator as field_validator
    PYDANTIC_V2 = False

# The actual letter distribution on the Q-Less dice, sourced from BoardGameGeek
# Each list represents one die with its six sides
QLESS_DICE = [
    ["M", "M", "L", "L", "B", "Y"],  # Die 1
    ["V", "F", "G", "K", "P", "P"],  # Die 2
    ["H", "H", "N", "N", "R", "R"],  # Die 3
    ["D", "F", "R", "L", "L", "W"],  # Die 4
    ["R", "R", "D", "L", "G", "G"],  # Die 5
    ["X", "K", "B", "S", "Z", "N"],  # Die 6
    ["W", "H", "H", "T", "T", "P"],  # Die 7
    ["C", "C", "B", "T", "J", "D"],  # Die 8
    ["C", "C", "M", "T", "T", "S"],  # Die 9
    ["O", "I", "I", "N", "N", "Y"],  # Die 10
    ["A", "E", "I", "O", "U", "U"],  # Die 11
    ["A", "A", "E", "E", "O", "O"],  # Die 12
]


class Die(BaseModel):
    """Representation of a single die in the Q-Less game."""

    sides: List[str] = Field(description="The 6 sides of the die with their letters")
    current_face: Optional[str] = Field(
        None, description="The currently showing face after a roll"
    )

    @field_validator("sides")
    @classmethod
    def validate_sides(cls, v: List[str]) -> List[str]:
        """Validate that a die has exactly 6 sides."""
        if len(v) != 6:
            raise ValueError("A die must have exactly 6 sides")
        return v

    def roll(self, use_face_index: Optional[int] = None) -> str:
        """
        Roll the die to get a random side.

        Args:
            use_face_index: Optional index to use instead of random roll (for testing)

        Returns:
            The letter on the rolled face
        """
        if use_face_index is not None and 0 <= use_face_index < 6:
            self.current_face = self.sides[use_face_index]
        else:
            self.current_face = random.choice(self.sides)

        return self.current_face


class DiceSet(BaseModel):
    """Representation of a set of dice for the Q-Less game."""

    dice: List[Die] = Field(description="The collection of dice in the set")
    roll_result: List[str] = Field(
        default_factory=list, description="The result of the last roll"
    )

    if PYDANTIC_V2:
        model_config = {"arbitrary_types_allowed": True}
    else:  # pragma: no cover - pydantic v1 style config
        class Config:
            arbitrary_types_allowed = True

    @classmethod
    def from_config(cls, dice_config: Optional[List[List[str]]] = None) -> "DiceSet":
        """
        Create a DiceSet from a configuration.

        Args:
            dice_config: Optional configuration for the dice. If not provided,
                         the standard Q-Less dice configuration is used.

        Returns:
            A new DiceSet instance
        """
        if dice_config is None:
            dice_config = QLESS_DICE

        dice = [Die(sides=sides, current_face=None) for sides in dice_config]
        return cls(dice=dice)

    def roll(self, use_face_indices: Optional[List[int]] = None) -> List[str]:
        """
        Roll all dice in the set.

        Args:
            use_face_indices: Optional list of indices to use instead of random rolls (for testing)

        Returns:
            List of letters from the rolled dice
        """
        self.roll_result = []

        for i, die in enumerate(self.dice):
            face_index = None
            if use_face_indices is not None and i < len(use_face_indices):
                face_index = use_face_indices[i]

            letter = die.roll(face_index)
            self.roll_result.append(letter)

        return self.roll_result

    def get_roll_string(self) -> str:
        """
        Get the current roll as a string.

        Returns:
            A string with all letters from the current roll
        """
        return "".join(self.roll_result)

    def get_letter_frequency(self) -> Dict[str, int]:
        """
        Count the frequency of each letter in the current roll.

        Returns:
            A dictionary mapping letters to their frequency in the roll
        """
        frequency: Dict[str, int] = {}
        for letter in self.roll_result:
            frequency[letter] = frequency.get(letter, 0) + 1
        return frequency


def create_standard_dice_set() -> DiceSet:
    """
    Create a standard Q-Less dice set.

    Returns:
        A DiceSet with the standard Q-Less dice configuration
    """
    return DiceSet.from_config(QLESS_DICE)


def roll_dice(dice_set: Optional[DiceSet] = None) -> Tuple[List[str], str]:
    """
    Roll a set of dice and return the result.

    Args:
        dice_set: Optional DiceSet to use. If not provided, a new standard set will be created.

    Returns:
        A tuple containing:
        - The list of individual letters from the roll
        - The combined string of all letters
    """
    if dice_set is None:
        dice_set = create_standard_dice_set()

    letters = dice_set.roll()
    return letters, dice_set.get_roll_string()
