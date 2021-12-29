"""Contains all tests for move generation"""


from copy import deepcopy
from os import path
from typing import Iterator
import json

import pytest

from chess_logic.core_chess import Chess


def moved_chess_state(chess, move) -> Chess:
    """Returns chess state after performing move"""
    return deepcopy(chess).move_piece(move)


def num_moves(depth, chess=Chess()) -> int:
    """Returns total number of moves at given depth from given position"""
    if depth == 1:
        return len(chess.current_legal_moves)
    return sum(
        num_moves(depth - 1, moved)
        for move in chess.current_legal_moves
        if not (moved := moved_chess_state(chess, move)).game_over
    )


def divide(depth, chess=Chess()) -> Iterator[tuple[str, int]]:
    """
    Yields move and total number of moves from that move at given depth for each legal
    move in current position
    """
    for move in chess.current_legal_moves:
        yield str(move), num_moves(depth - 1, moved_chess_state(chess, move))


test_data_path = path.join(path.dirname(__file__), "move_generation_test_data.json")
with open(test_data_path, encoding="utf-8") as test_data_file:
    test_data = json.load(test_data_file)


@pytest.mark.parametrize("chess, test_case_data", test_data.items(), indirect=["chess"])
class TestMoveGeneration:
    """Stores all tests using data from above test data JSON file"""

    # pylint: disable=no-self-use

    def test_move_generation(self, chess, test_case_data) -> None:
        """Tests that correct moves are generated in various positions"""
        assert set(test_case_data.keys()) == set(map(str, chess.current_legal_moves))

    def test_number_of_moves_generated(self, chess, test_case_data) -> None:
        """Tests correct number of moves generated at depth 3 from various positions"""
        assert all(test_case_data[move] == number for move, number in divide(3, chess))
