"""Contains all tests for move generation"""

import json
from os import path
from typing import Iterator

import pytest

from chess_logic.core_chess import Chess


def num_moves(depth, chess, move):
    """Returns total number of moves after performing move, subsequently undoing move"""
    performed_move = chess.move_piece(move)
    total = not chess.game_over and perft(depth - 1, chess)
    chess.undo_move(performed_move)
    return total


def perft(depth, chess=Chess()) -> int:
    """Returns total number of moves at given depth from given position"""
    if depth == 1:
        return len(chess.current_legal_moves)
    return sum(num_moves(depth, chess, move) for move in chess.current_legal_moves)


def divide(depth, chess=Chess()) -> Iterator[tuple[str, int]]:
    """Divides perft into each available legal move in current position"""
    for move in chess.current_legal_moves:
        yield str(move), num_moves(depth, chess, move)


test_data_path = path.join(path.dirname(__file__), "move_generation_test_data.json")
with open(test_data_path, encoding="utf-8") as test_data_file:
    test_data = json.load(test_data_file)


@pytest.mark.parametrize("fen, chess", zip(*[test_data] * 2), indirect=["chess"])
def test_undo_move(fen: str, chess: Chess):
    """Tests that making and undoing legal moves returns chess state to same position"""
    for move in chess.current_legal_moves:
        chess.undo_move(chess.move_piece(move))
        assert chess.fen == fen


@pytest.mark.parametrize("chess, test_case_data", test_data.items(), indirect=["chess"])
class TestMoveGeneration:
    """Stores all tests using data from test data JSON file with above parameters"""

    # pylint: disable=no-self-use

    def test_move_generation(
        self, chess: Chess, test_case_data: dict[str, int]
    ) -> None:
        """Tests that correct moves are generated in various positions"""
        assert set(test_case_data) == set(map(str, chess.current_legal_moves))

    def test_number_of_moves_generated(
        self, chess: Chess, test_case_data: dict[str, int]
    ) -> None:
        """Tests correct number of moves generated at depth 3 from various positions"""
        assert all(test_case_data[move] == number for move, number in divide(3, chess))
