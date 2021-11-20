"""Contains all unit tests for chess logic"""

import unittest

from chess_logic.board import fens_portion, EMPTY_FEN, STARTING_FEN
from chess_logic.core_chess import Chess

RANDOM_FENS = (
    "1r6/2R1k1pp/3bp3/5p2/4n3/BP2P3/3N1PPP/6K1 b - - 3 24",
    "r4rk1/pp2qppp/4n3/1p6/8/1Q6/PP3PPP/R1B1R1K1 w - - 0 18",
    "r5k1/1p3p1p/p1p2n2/3p1P1n/6pP/4P1q1/PPB3P1/2R1QRK1 b - - 3 27",
    "r1bq1rk1/pppnbppp/4pn2/3p2B1/2PP4/2N1PN2/PP3PPP/2RQKB1R b K - 4 7",
    "r1q1nrk1/1pp2ppp/2nb4/p2Np3/4P1b1/2P1BNP1/PP2QPBP/R2R2K1 w - - 10 16",
    "rnbqk2r/ppp1bppp/4pn2/3p4/8/3P1NP1/PPP1PPBP/RNBQ1RK1 b kq - 0 5",
    "r1bq1rk1/pp3ppp/2nb1n2/1B1p4/3P4/2N2N2/PP3PPP/R1BQ1RK1 w - - 3 10",
    "r5k1/bpR2pp1/p6p/P2P4/1P1N4/3n1NPP/4rP1K/R7 b - - 2 24",
    "r1bqk2r/1pp1bppp/2n2n2/p3p3/2PP4/3P1NP1/PP3PBP/RNBQ1RK1 b kq - 0 8",
)
RANDOM_MOVES = ((1, 4), (0, 5)), ((5, 1), (3, 1)), ((5, 6), (2, 3)), ((1, 7), (2, 7))
MOVED_FENS = (
    "1r3k2/2R3pp/3bp3/5p2/4n3/BP2P3/3N1PPP/6K1 w - - 4 25",
    "r4rk1/pp2qppp/4n3/1Q6/8/8/PP3PPP/R1B1R1K1 b - - 0 18",
    "r5k1/1p3p1p/p1pq1n2/3p1P1n/6pP/4P3/PPB3P1/2R1QRK1 w - - 4 28",
    "r1bq1rk1/pppnbpp1/4pn1p/3p2B1/2PP4/2N1PN2/PP3PPP/2RQKB1R w K - 0 8",
)
TEST_FENS = (STARTING_FEN, EMPTY_FEN) + RANDOM_FENS


class ChessRulesTest(unittest.TestCase):
    """TestCase subclass for chess logic unit tests and relevant helper functions"""

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
                test_chess.move(*move)
                # Verifies that positions portions of actual and expected FENs match
                self.assertEqual(*fens_portion((test_chess.fen, new_fen), 0))


if __name__ == "__main__":
    unittest.main()
