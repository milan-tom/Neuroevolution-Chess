"""Handles move generation for individual pieces"""

from typing import Iterable

from chess_logic.board import Bitboard, Coord, OPPOSITE_SIDES, PIECES, STARTING_FEN
from chess_logic.board import ChessBoard, get_piece_side

STANDARD_PIECES = PIECES[:6]

Bitboards = dict[str, Bitboard]
Moves = Iterable[tuple[Coord, Coord]]

RANK0 = 2 ** 8 - 1
RANKS = [RANK0] + [RANK0 << i for i in range(8, 64, 8)]
FILE0 = sum(2 ** i for i in range(0, 64, 8))
FILES = [FILE0] + [FILE0 << i for i in range(1, 8)]

UNSIGN_MASK = 2 ** 64 - 1
PAWN_MASK_SHIFTS = 8, 16, 9, 7


def rotate_bitboard(board: Bitboard) -> Bitboard:
    """Reverses single bitboard bitwise"""
    return int(bin(board)[2:].zfill(64)[::-1], 2)


class Chess(ChessBoard):
    """
    Provides full handling of chess state, adding move generation and move making to
    handling of board state
    """

    def __init__(self, fen: str = STARTING_FEN) -> None:
        super().__init__(fen)
        move_functions = (
            self.king_moves,
            self.queen_moves,
            self.rook_moves,
            self.bishop_moves,
            self.knight_moves,
            self.pawn_moves,
        )
        self.move_functions_and_pieces = list(zip(move_functions, STANDARD_PIECES))
        self.current_legal_moves = self.legal_moves()

    def move(self, old_square: Coord, new_square: Coord) -> None:
        """Moves piece at given square to new square"""
        if captured_piece := self.get_piece_at_square(new_square):
            self.remove_bitboard_square(captured_piece, new_square)
        self.move_piece_bitboard_square(
            self.get_piece_at_square(old_square),
            old_square,
            new_square,
        )
        self.update_metadata()
        self.current_legal_moves = self.legal_moves()

    def bitboard_index_to_square(self, index: int) -> Coord:
        """Returns coordinates of square given bitboard index (rotated for black)"""
        if self.rotate:
            index = 63 - index
        return tuple(map(lambda x: 7 - x, divmod(index, 8)))

    def legal_moves(self) -> Moves:
        """Yields all pseudo-legal moves for all pieces in current board state"""
        self.rotate = self.next_side == "BLACK"
        self.move_boards = self.oriented_bitboards(
            {
                piece.upper(): bitboard
                for piece, bitboard in self.boards.items()
                if len(piece) != 1 or get_piece_side(piece) == self.next_side
            }
        )
        self.move_boards["~GAME"] = ~self.move_boards["GAME"]
        self.move_boards["OPPOSITE"] = self.move_boards[OPPOSITE_SIDES[self.next_side]]

        return [
            move
            for func, piece in self.move_functions_and_pieces
            for move in func(self.move_boards[piece])
        ]

    def legal_moves_from_square(self, square: Coord) -> Iterable[Coord]:
        """Returns all legal moves from specific square on board"""
        return [
            new_square
            for old_square, new_square in self.current_legal_moves
            if old_square == square
        ]

    def oriented_bitboards(self, bitboards: Bitboards) -> Bitboards:
        """
        Rotates bitboards if side to move is black (enables move generation universally
        from white's perspective)
        """
        if self.rotate:
            return {
                piece: rotate_bitboard(bitboard)
                for piece, bitboard in bitboards.items()
            }
        return bitboards

    def king_moves(self, piece_bitboard: Bitboard) -> Moves:
        """Yields all pseudo-legal moves for king piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return ()

    def queen_moves(self, piece_bitboard: Bitboard) -> Moves:
        """Yields all pseudo-legal moves for queen piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return ()

    def rook_moves(self, piece_bitboard: Bitboard) -> Moves:
        """Yields all pseudo-legal moves for rook piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return ()

    def bishop_moves(self, piece_bitboard: Bitboard) -> Moves:
        """Yields all pseudo-legal moves for bishop piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return ()

    def knight_moves(self, piece_bitboard: Bitboard) -> Moves:
        """Yields all pseudo-legal moves for knight piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return ()

    def pawn_moves(self, piece_bitboard: Bitboard) -> Moves:
        """Yields all pseudo-legal moves for pawn piece"""
        single_push = piece_bitboard << 8 & self.move_boards["~GAME"]
        double_push = (single_push & RANKS[2]) << 8 & self.move_boards["~GAME"]
        capture = (
            (piece_bitboard & ~FILES[7]) << 9 | (piece_bitboard & ~FILES[0]) << 7
        ) & self.move_boards["OPPOSITE"]
        for i in range(piece_bitboard.bit_length()):
            piece_mask = 1 << i
            if piece_mask & piece_bitboard:
                old_square = self.bitboard_index_to_square(i)
                for shift, move_bitboard in zip(
                    PAWN_MASK_SHIFTS,
                    (single_push, double_push, capture, capture),
                ):
                    if piece_mask << shift & move_bitboard:
                        yield old_square, self.bitboard_index_to_square(i + shift)
