"""Contains all unit tests for management of chess board state"""

import pytest

from chess_logic.board import STARTING_FEN
from chess_logic.core_chess import Move
from tests import RANDOM_FENS

RANDOM_MOVES = (
    Move((1, 4), (0, 5)),
    Move((5, 1), (3, 1)),
    Move((5, 6), (2, 3)),
    Move((1, 7), (2, 7)),
)
MOVED_FENS = (
    "1r3k2/2R3pp/3bp3/5p2/4n3/BP2P3/3N1PPP/6K1 w - - 4 25",
    "r4rk1/pp2qppp/4n3/1Q6/8/8/PP3PPP/R1B1R1K1 b - - 0 18",
    "r5k1/1p3p1p/p1pq1n2/3p1P1n/6pP/4P3/PPB3P1/2R1QRK1 w - - 4 28",
    "r1bq1rk1/pppnbpp1/4pn1p/3p2B1/2PP4/2N1PN2/PP3PPP/2RQKB1R w K - 0 8",
)


def test_default_fen(chess) -> None:
    """Tests that Chess state created with no FEN has starting FEN by default"""
    assert chess.fen == STARTING_FEN


@pytest.mark.parametrize("chess, test_fen", zip(*[RANDOM_FENS] * 2), indirect=["chess"])
def test_fen_to_chess_state_conversion(chess, test_fen) -> None:
    """
    Tests conversion of FENs to bitboards and other board state-specific parameters
    via allowing 'Chess' class to extract the chess state from fens and then
    re-extracting the FENs based on this chess states bitboard, checking they match
    """
    assert chess.fen == test_fen


@pytest.mark.parametrize(
    "chess, move, new_fen",
    zip(RANDOM_FENS, RANDOM_MOVES, MOVED_FENS),
    indirect=["chess"],
)
def test_moving_pieces(chess, move, new_fen) -> None:
    """Tests basic piece movement where piece moves to empty square"""
    chess.move_piece(move)
    assert chess.fen == new_fen
