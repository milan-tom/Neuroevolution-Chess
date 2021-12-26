"""Contains all unit tests for move generation from chess board state"""

import pytest

from chess_logic.core_chess import Chess
from tests import TEST_FENS


@pytest.mark.parametrize("test_fen", TEST_FENS)
def test_board_orientation(test_fen) -> None:
    """Tests bitboard orientation for white and black in selected test positions"""
    test_chess = Chess(test_fen)
    oriented_boards = test_chess.oriented_bitboards(test_chess.boards)
    if test_chess.next_side == "WHITE":
        # Checks no changes made when orienting bitboards for white
        assert oriented_boards == test_chess.boards
    else:
        # Checks changes made when orienting bitboards for black and
        # orienting the bitboards twice gives the original bitboards
        assert oriented_boards != test_chess.boards
        assert test_chess.oriented_bitboards(oriented_boards) == test_chess.boards
