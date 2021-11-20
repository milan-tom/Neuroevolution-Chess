"""Handles move generation for individual pieces"""

from itertools import chain
from typing import Iterable

from chess_logic.board import Bitboard, Coord, ChessBoard, STARTING_FEN

Bitboards = dict[str, Bitboard]
Moves = Iterable[tuple[Coord, Coord]]

RANK0 = 2 ** 8 - 1
RANKS = [RANK0] + [RANK0 << i for i in range(8, 64, 8)]

FILE0 = sum(2 ** i for i in range(0, 64, 8))
FILES = [FILE0] + [FILE0 << i for i in range(1, 8)]


def bitboard_index_to_square(index: int) -> Coord:
    """Returns coordinates of square associated with bitboard index"""
    return tuple(map(lambda x: 7 - x, divmod(index, 8)))


class Chess(ChessBoard):
    """
    Provides full handling of chess state, adding move generation and move making to
    handling of board state
    """

    def __init__(self, fen: str = STARTING_FEN) -> None:
        super().__init__(fen)
        self.current_legal_moves = self.legal_moves()

    def move(self, old_square: Coord, new_square: Coord) -> None:
        """Moves piece at given square to new square and updates available moves"""
        super().move(old_square, new_square)
        self.current_legal_moves = self.legal_moves()

    def legal_moves(self) -> Moves:
        """Yields all pseudo-legal moves for all pieces in current board state"""
        return list(
            chain(
                self.king_moves(),
                self.queen_moves(),
                self.rook_moves(),
                self.bishop_moves(),
                self.knight_moves(),
                self.pawn_moves(),
            )
        )

    def legal_moves_from_square(self, square: Coord) -> Iterable[Coord]:
        """Returns all legal moves from specific square on board"""
        return [
            new_square
            for old_square, new_square in self.current_legal_moves
            if old_square == square
        ]

    def king_moves(self):
        """Yields all pseudo-legal moves for king piece (currently not implemented)"""
        # pylint: disable=no-self-use
        return ()

    def queen_moves(self):
        """Yields all pseudo-legal moves for queen piece (currently not implemented)"""
        # pylint: disable=no-self-use
        return ()

    def rook_moves(self):
        """Yields all pseudo-legal moves for rook piece (currently not implemented)"""
        # pylint: disable=no-self-use
        return ()

    def bishop_moves(self):
        """Yields all pseudo-legal moves for bishop piece (currently not implemented)"""
        # pylint: disable=no-self-use
        return ()

    def knight_moves(self):
        """Yields all pseudo-legal moves for knight piece (currently not implemented)"""
        # pylint: disable=no-self-use
        return ()

    def pawn_moves(self):
        """Yields all pseudo-legal moves for pawn piece (currently not implemented)"""
        # pylint: disable=no-self-use
        return ()
