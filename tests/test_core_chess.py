"""Contains all unit tests for move generation from chess board state"""

import unittest

from chess_logic.core_chess import Chess
from tests import TEST_FENS


class ChessMovesTest(unittest.TestCase):
    """Holds chess move generation unit tests and relevant helper functions"""

    def test_board_orientation(self):
        """Tests bitboard orientation for white and black in selected test positions"""
        for test_fen in TEST_FENS:
            test_chess = Chess(test_fen)
            oriented_boards = test_chess.oriented_bitboards(test_chess.boards)
            with self.subTest(test_fen=test_fen, next_side=test_chess.next_side):
                if test_chess.next_side == "WHITE":
                    # Checks no changes made when orienting bitboards for white
                    self.assertEqual(oriented_boards, test_chess.boards)
                else:
                    # Checks changes made when orienting bitboards for black and
                    # orienting the bitboards twice gives the original bitboards
                    self.assertNotEqual(oriented_boards, test_chess.boards)
                    self.assertEqual(
                        test_chess.oriented_bitboards(oriented_boards),
                        test_chess.boards,
                    )


if __name__ == "__main__":
    unittest.main()
