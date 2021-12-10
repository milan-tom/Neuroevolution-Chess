"""Handles move generation for individual pieces"""

from typing import Any, Iterator, NamedTuple, Optional

from chess_logic.board import (
    Bitboard,
    ChessBoard,
    Coord,
    OPPOSITE_SIDE,
    PIECE_SIDE,
    PIECES,
    rotate_bitboard,
    STARTING_FEN,
)

Bitboards = dict[str, Bitboard]
Context = tuple[str, Any]

STANDARD_PIECES = PIECES[:6]
PROMOTION_PIECES = STANDARD_PIECES[1:-1]
PIECE_OF_SIDE = {(side, piece.upper()): piece for piece, side in PIECE_SIDE.items()}

RANK0 = 2 ** 8 - 1
RANKS = [RANK0] + [RANK0 << i for i in range(8, 64, 8)]
FILE0 = sum(2 ** i for i in range(0, 64, 8))
FILES = [FILE0] + [FILE0 << i for i in range(1, 8)]

KNIGHT_FORWARD_MASKS = {
    1 * 8 + 2: ~(RANKS[7] | sum(FILES[6:])),
    1 * 8 - 2: ~(RANKS[7] | sum(FILES[:2])),
    2 * 8 + 1: ~(sum(RANKS[6:]) | FILES[0]),
    2 * 8 - 1: ~(sum(RANKS[6:]) | FILES[7]),
}
KNIGHT_MASKS = KNIGHT_FORWARD_MASKS | {
    -shift: rotate_bitboard(mask) for shift, mask in KNIGHT_FORWARD_MASKS.items()
}
PAWN_CAPTURE_SHIFTS_AND_MASKS = {7: ~FILES[0], 9: ~FILES[7]}


def signed_shift(board: Bitboard, shift: int) -> Bitboard:
    """Performs binary shift considering sign (left/right shift for +ve/-ve shift)"""
    if shift < 0:
        return board >> -shift
    return board << shift


class Move(NamedTuple):
    """Stores all data associated with move as NamedTuple"""

    old_square: Coord
    new_square: Coord
    context_flag: Optional[str] = None
    context_data: Any = None


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
        self.promotion = False
        self.current_legal_moves = self.legal_moves()

    def move_piece(self, move: Move) -> None:
        """Moves piece at given square to new square"""
        if captured_piece := self.get_piece_at_square(move.new_square):
            self.remove_bitboard_square(captured_piece, move.new_square)
        self.move_piece_bitboard_square(
            self.get_piece_at_square(move.old_square),
            move.old_square,
            move.new_square,
        )

        en_passant_bitboard = 0
        match move.context_flag:
            case "PROMOTION":
                self.remove_bitboard_square(
                    PIECE_OF_SIDE[(self.next_side, "P")], move.new_square
                )
                self.add_bitboard_square(move.context_data, move.new_square)
            case "EN PASSANT":
                self.remove_bitboard_square(
                    PIECE_OF_SIDE[(OPPOSITE_SIDE[self.next_side], "P")],
                    move.context_data,
                )
            case "DOUBLE PUSH":
                en_passant_bitboard = move.context_data

        self.update_metadata(en_passant_bitboard)
        self.current_legal_moves = self.legal_moves()

    def bitboard_index_to_square(self, index: int) -> Coord:
        """Returns coordinates of square given bitboard index (rotated for black)"""
        if self.rotate:
            index = 63 - index
        return tuple(map(lambda x: 7 - x, divmod(index, 8)))

    def legal_moves(self) -> list[Move]:
        """Yields all pseudo-legal moves for all pieces in current board state"""
        self.rotate = self.next_side == "BLACK"
        self.move_boards = self.oriented_bitboards(
            {
                piece.upper(): bitboard
                for piece, bitboard in self.boards.items()
                if len(piece) != 1 or PIECE_SIDE[piece] == self.next_side
            }
        )
        self.move_boards["~GAME"] = ~self.move_boards["GAME"]
        self.move_boards["~SAME"] = ~self.move_boards[self.next_side]
        self.move_boards["OPPOSITE"] = self.move_boards[OPPOSITE_SIDE[self.next_side]]

        # Collates list of all moves in current position
        return [
            move
            for func, piece in self.move_functions_and_pieces
            for move in func(self.move_boards[piece])
        ]

    def legal_moves_from_square(self, square: Coord) -> list[Move]:
        """Returns all legal moves from specific square on board"""
        return [move for move in self.current_legal_moves if move.old_square == square]

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

    def king_moves(self, piece_bitboard: Bitboard) -> Iterator[Move]:
        """Yields all pseudo-legal moves for king piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return iter(())

    def queen_moves(self, piece_bitboard: Bitboard) -> Iterator[Move]:
        """Yields all pseudo-legal moves for queen piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return iter(())

    def rook_moves(self, piece_bitboard: Bitboard) -> Iterator[Move]:
        """Yields all pseudo-legal moves for rook piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return iter(())

    def bishop_moves(self, piece_bitboard: Bitboard) -> Iterator[Move]:
        """Yields all pseudo-legal moves for bishop piece (currently not implemented)"""
        # pylint: disable=no-self-use, unused-argument
        return iter(())

    def knight_moves(self, piece_bitboard: Bitboard) -> Iterator[Move]:
        """Yields all pseudo-legal moves for knight piece"""
        for i in range(piece_bitboard.bit_length()):
            piece_mask = 1 << i
            if piece_mask & piece_bitboard:
                old_square = self.bitboard_index_to_square(i)
                for shift, mask in KNIGHT_MASKS.items():
                    if (
                        signed_shift(piece_mask & mask, shift)
                        & self.move_boards["~SAME"]
                    ):
                        yield Move(old_square, self.bitboard_index_to_square(i + shift))

    def pawn_moves(self, piece_bitboard: Bitboard) -> Iterator[Move]:
        """Yields all pseudo-legal moves for pawn piece"""
        # Generates possible push move bitboards for all pawns at once
        single_push = piece_bitboard << 8 & self.move_boards["~GAME"]
        double_push = (single_push & RANKS[2]) << 8 & self.move_boards["~GAME"]

        for i in range(piece_bitboard.bit_length()):
            piece_mask = 1 << i
            # Generates moves if pawn exists at bitboard index
            if piece_mask & piece_bitboard:
                old_square = self.bitboard_index_to_square(i)
                self.promotion = bool(piece_mask & RANKS[6])

                # Generates all forward push moves
                if piece_mask << 8 & single_push:
                    yield from self.promotion_checked_moves(
                        old_square, self.bitboard_index_to_square(i + 8)
                    )
                    if piece_mask << 16 & double_push:
                        yield Move(
                            old_square,
                            self.bitboard_index_to_square(i + 16),
                            "DOUBLE PUSH",
                            rotate_bitboard(piece_mask << 8),
                        )

                # Generates all pawn captures
                for shift, move_mask in PAWN_CAPTURE_SHIFTS_AND_MASKS.items():
                    if piece_mask & move_mask:
                        shifted_piece = piece_mask << shift
                        new_square = self.bitboard_index_to_square(i + shift)
                        if shifted_piece & self.move_boards["OPPOSITE"]:
                            yield from self.promotion_checked_moves(
                                old_square, new_square
                            )
                        elif shifted_piece & self.en_passant_bitboard:
                            yield Move(
                                old_square,
                                new_square,
                                "EN PASSANT",
                                self.bitboard_index_to_square(i + shift - 8),
                            )

    def promotion_checked_moves(
        self, old_square: Coord, new_square: Coord
    ) -> Iterator[Move]:
        """Ensures moves yielded with correct options and flags if promoting pawn"""
        if self.promotion:
            for piece in PROMOTION_PIECES:
                yield Move(old_square, new_square, "PROMOTION", piece)
        else:
            yield Move(old_square, new_square)
