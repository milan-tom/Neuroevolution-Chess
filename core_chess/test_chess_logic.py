import unittest

from core_chess.chess_logic import Chess, STARTING_FEN, EMPTY_FEN


RANDOM_FENS = [
    "1r6/2R1k1pp/3bp3/5p2/4n3/BP2P3/3N1PPP/6K1 b - - 3 24",
    "r4rk1/pp2qppp/4n3/1p6/8/1Q6/PP3PPP/R1B1R1K1 w - - 0 18",
    "r5k1/1p3p1p/p1p2n2/3p1P1n/6pP/4P1q1/PPB3P1/2R1QRK1 b - - 3 27",
    "r1bq1rk1/pppnbppp/4pn2/3p2B1/2PP4/2N1PN2/PP3PPP/2RQKB1R b K - 4 7",
    "r1q1nrk1/1pp2ppp/2nb4/p2Np3/4P1b1/2P1BNP1/PP2QPBP/R2R2K1 w - - 10 16",
    "rnbqk2r/ppp1bppp/4pn2/3p4/8/3P1NP1/PPP1PPBP/RNBQ1RK1 b kq - 0 5",
    "r1bq1rk1/pp3ppp/2nb1n2/1B1p4/3P4/2N2N2/PP3PPP/R1BQ1RK1 w - - 3 10",
    "r5k1/bpR2pp1/p6p/P2P4/1P1N4/3n1NPP/4rP1K/R7 b - - 2 24",
    "r1bqk2r/1pp1bppp/2n2n2/p3p3/2PP4/3P1NP1/PP3PBP/RNBQ1RK1 b kq - 0 8",
]


class ChessRulesTest(unittest.TestCase):
    def test_fen_to_chess_state_conversion(self):
        """
        Tests conversion of FENs to bitboards and other board state-specific parameters
        via allowing 'Chess' class to extract the chess state from fens and then
        re-extracting the FENs based on this chess states bitboard, checking they match
        """
        # Tests default starting position, empty position and random positions
        for test_fen in [STARTING_FEN, EMPTY_FEN] + RANDOM_FENS:
            with self.subTest(test_fen=test_fen):
                test_chess = Chess() if test_fen == STARTING_FEN else Chess(test_fen)
                self.assertEqual(test_chess.fen, test_fen)


if __name__ == "__main__":
    unittest.main()
