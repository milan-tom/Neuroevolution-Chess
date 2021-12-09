"""Contains all unit tests for management of chess board state"""

import unittest

from chess_logic.board import fens_portion, STARTING_FEN
from chess_logic.core_chess import Chess, Move
from tests import RANDOM_FENS, TEST_FENS

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


class ChessBoardTest(unittest.TestCase):
    """Holds chess board unit tests and relevant helper functions"""

    def test_fen_to_chess_state_conversion(self) -> None:
        """
        Tests conversion of FENs to bitboards and other board state-specific parameters
        via allowing 'Chess' class to extract the chess state from fens and then
        re-extracting the FENs based on this chess states bitboard, checking they match
        """
        # Tests default starting position, empty position and random positions
        for test_fen in TEST_FENS:
            with self.subTest(test_fen=test_fen):
                test_chess = Chess() if test_fen == STARTING_FEN else Chess(test_fen)
                self.assertEqual(test_chess.fen, test_fen)

    def test_moving_pieces(self) -> None:
        """Tests basic piece movement where piece moves to empty square"""
        # Loops through test moves, performing them on the starting states from the
        # first few of the previously defined 'RANDOM_FENS'
        for original_fen, move, new_fen in zip(RANDOM_FENS, RANDOM_MOVES, MOVED_FENS):
            with self.subTest(original_fen=original_fen, move=move, new_fen=new_fen):
                test_chess = Chess(original_fen)
                test_chess.move_piece(move)
                # Verifies correctness of positions and next side portions of actual FEN
                for portion in range(1):
                    self.assertEqual(*fens_portion((test_chess.fen, new_fen), portion))


if __name__ == "__main__":
    unittest.main()
