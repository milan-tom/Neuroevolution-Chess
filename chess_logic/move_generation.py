"""Handles move generation for all pieces"""

from enum import auto, Enum
from functools import reduce
from operator import itemgetter, or_
from typing import Any, Iterator, NamedTuple, Optional

from chess_logic.board import (
    Bitboard,
    BITBOARD_SQUARE,
    BITBOARD_TO_FEN_SQUARE,
    CASTLING_ROOK_MOVES,
    CASTLING_SYMBOLS,
    Coord,
    ChessBoard,
    OPPOSITE_SIDE,
    PIECE_SIDE,
    PIECES,
    rotate_bitboard,
    ROWS_AND_COLUMNS,
    SIDES,
    SQUARE_BITBOARD,
)

Bitboards = dict[str, Bitboard]
Context = tuple[str, Any]

PIECE_OF_SIDE = {
    side: {piece.upper(): piece for piece in PIECES if PIECE_SIDE[piece] == side}
    for side in SIDES
}
STANDARD_PIECES = PIECES[:6]
PROMOTION_PIECES = {
    side: "".join(map(PIECE_OF_SIDE[side].get, STANDARD_PIECES[1:-1])) for side in SIDES
}

RANK0 = 2 ** 8 - 1
RANKS = [RANK0] + [RANK0 << i for i in range(8, 64, 8)]
FILE0 = sum(2 ** i for i in range(0, 64, 8))
FILES = [FILE0] + [FILE0 << i for i in range(1, 8)]


class Slider(Enum):
    """Stores slider flags as enums"""

    ROOK = auto()
    BISHOP = auto()
    KING = auto()


ROOK_SHIFTS = {shift: itemgetter(i) for i, shift in enumerate((8, 1))}
ROOK_SHIFTS |= {
    -shift: lambda square, i=i: 7 - square[i] for i, shift in enumerate(ROOK_SHIFTS)
}
BISHOP_SHIFTS = {
    shift: lambda square, i=i: min(
        7 - x if i & j else x for j, x in enumerate(square, 1)
    )
    for i, shift in enumerate((9, -7, 7, -9))
}
KING_SHIFTS = ROOK_SHIFTS | BISHOP_SHIFTS
SLIDER_SHIFTS = dict(zip(Slider, (ROOK_SHIFTS, BISHOP_SHIFTS, KING_SHIFTS)))


def signed_shift(board: Bitboard, shift: int) -> Bitboard:
    """Performs binary shift considering sign (left/right shift for +ve/-ve shift)"""
    if shift < 0:
        return board >> -shift
    return board << shift


def blocker_configs(blocker_mask: Bitboard) -> Iterator[Bitboard]:
    """Yields all possible blocker configurations for the given blocker mask"""
    for blocker_config_i in range(1 << blocker_mask.bit_count()):
        # Removes blockers in certain positions according to blocker configuration index
        blocker_config = blocker_mask
        for i in range(blocker_mask.bit_length()):
            blocker = 1 << i
            if blocker & blocker_mask:
                if 1 & blocker_config_i:
                    blocker_config &= ~blocker
                blocker_config_i >>= 1

        yield blocker_config


def move_board(
    square: Coord, slider: Slider, mask_edges: bool = False, blockers: Bitboard = 0
) -> Bitboard:
    """Returns move board given current square, blockers present, and possible shifts"""
    piece_mask = SQUARE_BITBOARD[square]
    moves = 0
    for shift, max_move_func in SLIDER_SHIFTS[slider].items():
        max_move = max_move_func(square)
        # Prevents slider from reaching board border if required
        if mask_edges:
            max_move -= 1

        # Adds all moves in current direction to overall move bitboard until blocked
        move_mask = piece_mask
        for _ in range(max_move):
            move_mask = signed_shift(move_mask, shift)
            moves |= move_mask
            if move_mask & blockers:
                break
    return moves


SLIDER_RAYS = {
    slider: {
        SQUARE_BITBOARD[square]: move_board(
            square, slider, mask_edges=slider != Slider.KING
        )
        for square in ROWS_AND_COLUMNS
    }
    for slider in Slider
}

SLIDER_MOVES = {
    slider: {
        (bitboard := SQUARE_BITBOARD[square]): {
            blocker_config: move_board(square, slider, blockers=blocker_config)
            for blocker_config in blocker_configs(SLIDER_RAYS[slider][bitboard])
        }
        for square in ROWS_AND_COLUMNS
    }
    for slider in Slider
    if slider is not slider.KING
}

KING_MASKS = {
    +8 + 1: ~(RANKS[7] | FILES[7]),
    +8 + 0: ~RANKS[7],
    +8 - 1: ~(RANKS[7] | FILES[0]),
    +0 + 1: ~FILES[7],
    +0 - 1: ~FILES[0],
    -8 + 1: ~(RANKS[0] | FILES[7]),
    -8 + 0: ~RANKS[0],
    -8 - 1: ~(RANKS[0] | FILES[0]),
}
KNIGHT_FORWARD_MASKS = {
    1 * 8 + 2: ~(RANKS[7] | sum(FILES[6:])),
    1 * 8 - 2: ~(RANKS[7] | sum(FILES[:2])),
    2 * 8 + 1: ~(sum(RANKS[6:]) | FILES[7]),
    2 * 8 - 1: ~(sum(RANKS[6:]) | FILES[0]),
}
KNIGHT_MASKS = KNIGHT_FORWARD_MASKS | {
    -shift: rotate_bitboard(mask) for shift, mask in KNIGHT_FORWARD_MASKS.items()
}
PAWN_CAPTURE_SHIFTS_AND_MASKS = {7: ~FILES[0], 9: ~FILES[7]}
NON_SLIDER_PIECES_AND_MASKS = list(zip("KN", (KING_MASKS, KNIGHT_MASKS)))
REMAINING_PIECES = [piece for piece in STANDARD_PIECES if piece not in "KN"]


def non_slider_moves(
    piece_bitboard: Bitboard,
    masks: dict[int, Bitboard],
    context_flag: Optional[Any] = None,
):
    """Yields all pseudo-legal moves for either king or knight"""
    for i in range(piece_bitboard.bit_length()):
        piece_mask = 1 << i
        if piece_mask & piece_bitboard:
            for shift, mask in masks.items():
                yield PseudoMove(
                    piece_mask, signed_shift(piece_mask & mask, shift), context_flag
                )


POSSIBLE_ATTACKERS = {shift: ["b", "q"] for shift in BISHOP_SHIFTS}
POSSIBLE_ATTACKERS |= {shift: ["r", "q"] for shift in ROOK_SHIFTS}

BITBOARD_INDEX = {1 << i: i for i in range(64)}
POSSIBLE_PIN_SHIFTS = sorted(KING_SHIFTS.keys(), reverse=True)[:4]
REVERSED_BITBOARD = {1 << i: 1 << 63 - i for i in range(64)}


def shift_direction(old: Bitboard, new: Bitboard) -> int:
    """Returns core bitboard shift by which new square moved to from old"""
    difference = BITBOARD_INDEX[new] - BITBOARD_INDEX[old]
    for shift in POSSIBLE_PIN_SHIFTS:
        if difference % shift == 0:
            return shift
    raise ValueError("New square is not directly reachable from old square")


CASTLING_SQUARES_TO_CHECK = {
    symbol: [SQUARE_BITBOARD[(7, column)] for column in column_range]
    for symbol, column_range in zip(
        CASTLING_SYMBOLS, (range(5, 7), range(3, 1, -1), range(2, 0, -1), range(4, 6))
    )
}
CASTLING_CLEAR_BITBOARD = {
    symbol: reduce(or_, squares + [signed_shift(squares[-1], extra_shift)])
    for (symbol, squares), extra_shift in zip(
        CASTLING_SQUARES_TO_CHECK.items(), (0, 1, 0, -1)
    )
}


class PseudoMove(NamedTuple):
    """Stores all data associated with pseudo-legal move as NamedTuple for checks"""

    old_board: Bitboard
    new_board: Bitboard
    context_flag: Optional[str] = None
    context_data: Any = None


class Move(NamedTuple):
    """Stores all data associated with move as NamedTuple"""

    old_square: Coord
    new_square: Coord
    context_flag: Optional[str] = None
    context_data: Any = None

    def __str__(self):
        """Returns basic string representation of move (old square and new square)"""
        # pylint: disable=unsubscriptable-object
        move = "".join(
            map(
                lambda square: BITBOARD_TO_FEN_SQUARE[SQUARE_BITBOARD[square]], self[:2]
            )
        )
        return (
            move
            if self.context_flag != "PROMOTION"
            else move + self.context_data.lower()
        )


class MoveGenerator(ChessBoard):
    """Handles all move generation for current chess state"""

    def __init__(self, fen: str) -> None:
        super().__init__(fen)
        move_functions = (
            self.queen_moves,
            self.rook_moves,
            self.bishop_moves,
            self.pawn_moves,
        )
        self.move_functions_and_pieces = list(zip(move_functions, REMAINING_PIECES))
        self.is_check = self.promotion = self.rotate = False
        self.move_boards = {}
        self.knight_attacks = {}
        self.total_knight_attacks = 0

    def move_bitboard_to_square(self, move_bitboard: Bitboard) -> Coord:
        """Returns coordinates of square given bitboard index (rotated for black)"""
        return BITBOARD_SQUARE[
            REVERSED_BITBOARD[move_bitboard] if self.rotate else move_bitboard
        ]

    def legal_moves(self) -> list[Move]:
        """Returns a list of all legal moves in current board state"""
        return [
            Move(*map(self.move_bitboard_to_square, move[:2]), *move[2:])
            for move in self.generate_legal_moves()
        ]

    def generate_legal_moves(self) -> Iterator[PseudoMove]:
        """Yields all legal moves for all pieces in current board state"""
        self.rotate = self.next_side == "BLACK"

        # Orients bitboards for move generation (upper case piece represents next side)
        self.move_boards = self.oriented_bitboards(
            {
                (
                    piece.upper()
                    if len(piece) != 1 or PIECE_SIDE[piece] == self.next_side
                    else piece.lower()
                ): bitboard
                for piece, bitboard in self.boards.items()
            }
        )
        self.move_boards["~GAME"] = ~self.move_boards["GAME"]
        self.move_boards["SAME"] = self.move_boards[self.next_side]
        self.move_boards["~SAME"] = ~self.move_boards["SAME"]
        self.move_boards["OPPOSITE"] = self.move_boards[OPPOSITE_SIDE[self.next_side]]

        king_bitboard = self.move_boards["K"]
        pinned, blockable = self.get_pinned_and_blockable(king_bitboard)

        if not self.is_check:
            yield from self.generate_castling_moves()

        # Iterates through generated pseudo-legal moves, yielding those that are legal
        for move in self.generate_pseudo_legal_moves():
            if move.new_board & self.move_boards["~SAME"]:
                if move.context_flag == "K":
                    if not self.square_attacked(move.new_board):
                        yield move
                else:
                    if self.is_check:
                        if move.old_board & ~pinned and (
                            move.new_board & blockable
                            or move.context_flag == "EN PASSANT"
                            and move.context_data[0] & blockable
                        ):
                            yield move
                    elif move.old_board & pinned:
                        if move.context_flag != "N" and shift_direction(
                            king_bitboard, move.old_board
                        ) == shift_direction(move.old_board, move.new_board):
                            yield move
                    else:
                        yield move

    def get_pinned_and_blockable(
        self, king_bitboard: Bitboard
    ) -> tuple[Bitboard, Bitboard]:
        """Returns bitboards representing current pinned and check-blocking squares"""
        # Precomputes bitboards representing king and primary/secondary attackers
        king_square = BITBOARD_SQUARE[king_bitboard]
        king_attackers = (
            self.move_boards["GAME"] & SLIDER_RAYS[Slider.KING][king_bitboard]
        )
        primary_attacker_paths = move_board(
            king_square, Slider.KING, blockers=king_attackers
        )
        secondary_attacker_paths = (
            0
            if not primary_attacker_paths
            else move_board(
                king_square,
                Slider.KING,
                blockers=king_attackers & ~primary_attacker_paths,
            )
        )

        # Removes king from game bitboard, preventing interference with attacks
        self.move_boards["GAME"] &= ~king_bitboard

        # Finds attacks, pins, and blocks for all eight directions from king
        self.is_check = False
        blockable = pinned = 0
        for shift in KING_SHIFTS:

            first_attacker, first_attacker_path = self.checked_attacker_in_direction(
                king_bitboard, shift, primary_attacker_paths
            )
            if first_attacker_path:
                if self.is_check:
                    blockable = 0
                else:
                    self.is_check = True
                    blockable |= first_attacker_path
            elif (
                first_attacker & self.move_boards["SAME"] & ~king_bitboard
                and self.checked_attacker_in_direction(
                    first_attacker,
                    shift,
                    secondary_attacker_paths,
                    pawn_possible=False,
                )[1]
            ):
                pinned |= first_attacker

        # Checks knight attacks on king
        self.generate_knight_attacks()
        if king_bitboard & self.total_knight_attacks:
            if self.is_check or not (
                knight_blockable := self.knight_attacks[king_bitboard]
            ):
                blockable = 0
            else:
                self.is_check = True
                blockable |= knight_blockable

        return pinned, blockable

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

    def checked_attacker_in_direction(
        self,
        square: Bitboard,
        shift: int,
        attacker_paths: Bitboard,
        pawn_possible: bool = True,
    ) -> tuple[Bitboard, Bitboard]:
        """
        Returns first potential attacker square in given direction and attacker path if
        square contains piece actually attacking king
        """
        first_attacker_path = 0
        first_attacker = square
        while (next_attacker := signed_shift(first_attacker, shift)) & attacker_paths:
            first_attacker = next_attacker
            first_attacker_path |= first_attacker

        if first_attacker & self.move_boards["OPPOSITE"]:
            if (
                any(
                    first_attacker & self.move_boards[attacker]
                    for attacker in POSSIBLE_ATTACKERS[shift]
                )
                or pawn_possible
                and shift in PAWN_CAPTURE_SHIFTS_AND_MASKS
                and first_attacker & self.move_boards["p"]
                and first_attacker_path.bit_count() == 1
            ):
                return first_attacker, first_attacker_path
        return first_attacker, 0

    def generate_knight_attacks(self) -> None:
        """Pre-computes all attacks possible by opposing knights in current position"""
        self.knight_attacks = {}
        for move in non_slider_moves(self.move_boards["n"], KNIGHT_MASKS):
            self.knight_attacks[move.new_board] = (
                move.old_board if move.new_board not in self.knight_attacks else 0
            )
        self.total_knight_attacks = reduce(or_, self.knight_attacks, 0)

    def square_attacked(self, square: Bitboard) -> bool:
        """Checks if given square attacked by any opposing piece"""
        square_coords = BITBOARD_SQUARE[square]
        square_attackers = self.move_boards["GAME"] & SLIDER_RAYS[Slider.KING][square]
        first_attacker_paths = move_board(
            square_coords, Slider.KING, blockers=square_attackers
        )
        return square & self.total_knight_attacks or any(
            self.checked_attacker_in_direction(square, shift, first_attacker_paths)[1]
            for shift in KING_SHIFTS
        )

    def generate_castling_moves(self) -> Iterator[PseudoMove]:
        """Yields all possible castling moves for current side"""
        for castling_right in self.side_castling_rights[self.next_side]:
            squares_to_check = CASTLING_SQUARES_TO_CHECK[castling_right]
            if not (
                CASTLING_CLEAR_BITBOARD[castling_right] & self.move_boards["GAME"]
                or any(map(self.square_attacked, squares_to_check))
            ):
                yield PseudoMove(
                    self.move_boards["K"],
                    squares_to_check[-1],
                    "CASTLING",
                    CASTLING_ROOK_MOVES[castling_right],
                )

    def generate_pseudo_legal_moves(self) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for all pieces in current board state"""
        # Non-slider moves
        for piece, masks in NON_SLIDER_PIECES_AND_MASKS:
            yield from non_slider_moves(self.move_boards[piece], masks, piece)

        # Generate remaining moves
        for move_func, piece in self.move_functions_and_pieces:
            yield from move_func(self.move_boards[piece])

    def slider_moves(self, slider, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for given slider"""
        for i in range(piece_bitboard.bit_length()):
            piece_mask = 1 << i
            if piece_mask & piece_bitboard:
                blockers = self.move_boards["GAME"] & SLIDER_RAYS[slider][piece_mask]
                moves_board = SLIDER_MOVES[slider][piece_mask][blockers]
                for j in range(moves_board.bit_length()):
                    if (moved_board := 1 << j) & moves_board:
                        yield PseudoMove(piece_mask, moved_board)

    def queen_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for queen piece"""
        yield from self.rook_moves(piece_bitboard)
        yield from self.bishop_moves(piece_bitboard)

    def rook_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for rook piece"""
        yield from self.slider_moves(Slider.ROOK, piece_bitboard)

    def bishop_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for bishop piece"""
        yield from self.slider_moves(Slider.BISHOP, piece_bitboard)

    def pawn_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for pawn piece"""
        # Generates possible push move bitboards for all pawns at once
        single_push = piece_bitboard << 8 & self.move_boards["~GAME"]
        double_push = (single_push & RANKS[2]) << 8 & self.move_boards["~GAME"]

        for i in range(piece_bitboard.bit_length()):
            piece_mask = 1 << i
            # Generates moves if pawn exists at bitboard index
            if piece_mask & piece_bitboard:
                self.promotion = bool(piece_mask & RANKS[6])

                # Generates all forward push moves
                if (moved_board := piece_mask << 8) & single_push:
                    yield from self.promotion_checked_moves(piece_mask, moved_board)
                    if (moved_board := piece_mask << 16) & double_push:
                        yield PseudoMove(
                            piece_mask,
                            moved_board,
                            "DOUBLE PUSH",
                            rotate_bitboard(piece_mask << 8),
                        )

                # Generates all pawn captures
                for shift, move_mask in PAWN_CAPTURE_SHIFTS_AND_MASKS.items():
                    if piece_mask & move_mask:
                        shifted_piece = piece_mask << shift
                        if shifted_piece & self.move_boards["OPPOSITE"]:
                            yield from self.promotion_checked_moves(
                                piece_mask, shifted_piece
                            )
                        elif shifted_piece & self.en_passant_bitboard:
                            yield PseudoMove(
                                piece_mask,
                                shifted_piece,
                                "EN PASSANT",
                                (
                                    capture_bitboard := signed_shift(
                                        piece_mask, shift - 8
                                    ),
                                    self.move_bitboard_to_square(capture_bitboard),
                                ),
                            )

    def promotion_checked_moves(
        self, old_board: int, new_board: int
    ) -> Iterator[PseudoMove]:
        """Ensures moves yielded with correct options and flags if promoting pawn"""
        if self.promotion:
            for piece in PROMOTION_PIECES[self.next_side]:
                yield PseudoMove(old_board, new_board, "PROMOTION", piece)
        else:
            yield PseudoMove(old_board, new_board)
