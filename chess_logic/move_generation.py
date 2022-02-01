"""Handles move generation for all pieces"""

from functools import reduce
from operator import itemgetter, or_
from typing import Any, Callable, Iterator, NamedTuple, Optional

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
    SQUARE_BITBOARD_INDEX,
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

RANK0 = 2**8 - 1
RANKS = [RANK0] + [RANK0 << i for i in range(8, 64, 8)]
FILE0 = sum(2**i for i in range(0, 64, 8))
FILES = [FILE0] + [FILE0 << i for i in range(1, 8)]

SLIDERS = "RB"
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
SLIDER_SHIFTS = dict(zip(SLIDERS + "K", (ROOK_SHIFTS, BISHOP_SHIFTS, KING_SHIFTS)))


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


def slider_moves_in_direction(
    square: Coord,
    slider: str,
    shift: int,
    mask_edges: bool = False,
    blockers: Bitboard = 0,
) -> Bitboard:
    """Returns bitboard of moves available to slider in given direction from square"""
    moves = 0
    move_mask = SQUARE_BITBOARD[square]
    for _ in range(1 if mask_edges else 0, SLIDER_SHIFTS[slider][shift](square)):
        move_mask = signed_shift(move_mask, shift)
        moves |= move_mask
        if move_mask & blockers:
            break
    return moves


def total_slider_moves(
    square: Coord, slider: str, mask_edges: bool = False, blockers: Bitboard = 0
) -> Bitboard:
    """Returns bitboard of all moves available to slider from square"""
    return reduce(
        or_,
        map(
            lambda shift: slider_moves_in_direction(
                square, slider, shift, mask_edges, blockers
            ),
            SLIDER_SHIFTS[slider],
        ),
    )


def lsb(bitboard: Bitboard) -> Bitboard:
    """Returns bitboard representing lowest set bit in given bitboard"""
    return bitboard & -bitboard


def msb(bitboard: Bitboard) -> Bitboard:
    """Returns bitboard representing highest set bit in given bitboard"""
    return 1 << bitboard.bit_length() - 1


def bitboard_piece_masks(bitboard: Bitboard) -> Iterator[Bitboard]:
    """Yields all piece masks (bitboard representing one piece) in given bitboard"""
    while bitboard:
        yield (piece_mask := lsb(bitboard))
        bitboard &= ~piece_mask


class PseudoMove(NamedTuple):
    """Stores all data associated with pseudo-legal move as NamedTuple for checks"""

    old_board: Bitboard
    new_board: Bitboard
    context_flag: Optional[str] = None
    context_data: Any = None


SLIDER_RAYS = {
    slider: {
        SQUARE_BITBOARD[square]: total_slider_moves(square, slider, mask_edges=True)
        for square in ROWS_AND_COLUMNS
    }
    for slider in SLIDERS
}

KING_ATTACK_PATH = {
    SQUARE_BITBOARD[square]: {
        shift: slider_moves_in_direction(square, "K", shift) for shift in KING_SHIFTS
    }
    for square in ROWS_AND_COLUMNS
}


def king_attacker_and_path_in_direction(shift, king_bitboard, attackers):
    """Returns first attacker in given direction and path of attacker if any"""
    attacker_path = KING_ATTACK_PATH[king_bitboard][shift]
    if relevant_attackers := attacker_path & attackers:
        if shift > 0:
            first_attacker = lsb(relevant_attackers)
            attacker_path &= (first_attacker << 1) - 1
        else:
            first_attacker = msb(relevant_attackers)
            attacker_path &= ~(first_attacker - 1)
    else:
        first_attacker = 0
    return first_attacker, attacker_path


SLIDER_MOVES = {
    slider: {
        (square_board := SQUARE_BITBOARD[square]): {
            blocker_config: [
                PseudoMove(square_board, new_board)
                for new_board in bitboard_piece_masks(
                    total_slider_moves(square, slider, blockers=blocker_config)
                )
            ]
            for blocker_config in blocker_configs(SLIDER_RAYS[slider][square_board])
        }
        for square in ROWS_AND_COLUMNS
    }
    for slider in SLIDERS
}

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

NON_SLIDERS = "KN"
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
PAWN_CAPTURE_MASKS = {7: ~FILES[0], 9: ~FILES[7]}
REMAINING_PIECES = [piece for piece in STANDARD_PIECES if piece not in "KN"]


def non_slider_moves(
    masks: dict[int, Bitboard],
    context_flag: Optional[str] = None,
    context_data_func: Callable[[Bitboard], Any] = lambda piece_mask: None,
) -> dict[Bitboard, list[Bitboard]]:
    """Returns dictionary mapping of squares to list of new squares reachable"""
    return {
        piece_mask: [
            PseudoMove(
                piece_mask,
                signed_shift(piece_mask, shift),
                context_flag,
                context_data_func(piece_mask),
            )
            for shift, mask in masks.items()
            if piece_mask & mask
        ]
        for piece_mask in BITBOARD_INDEX
    }


NON_SLIDER_PIECE_MOVES = {
    non_slider: non_slider_moves(masks, non_slider)
    for non_slider, masks in zip(
        list(NON_SLIDERS) + ["P SINGLE PUSH", "P CAPTURE"],
        (KING_MASKS, KNIGHT_MASKS, {8: sum(RANKS[1:7])}, PAWN_CAPTURE_MASKS),
    )
}
NON_SLIDER_PIECE_MOVES["P DOUBLE PUSH"] = non_slider_moves(
    {16: RANKS[1]}, "DOUBLE PUSH", lambda piece_mask: rotate_bitboard(piece_mask << 8)
)


def total_non_slider_moves(non_slider: str, piece_bitboard: Bitboard):
    """Yields all pseudo-legal moves for either king or knight"""
    for piece_mask in bitboard_piece_masks(piece_bitboard):
        yield from NON_SLIDER_PIECE_MOVES[non_slider][piece_mask]


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

    def __int__(self):
        """Returns integer representation of move"""
        return (
            63 * SQUARE_BITBOARD_INDEX[self.old_square]
            + SQUARE_BITBOARD_INDEX[self.new_square]
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

    def legal_moves(self) -> tuple[Move]:
        """Returns a list of all legal moves in current board state"""
        return tuple(
            Move(*map(self.move_bitboard_to_square, move[:2]), *move[2:])
            for move in self.generate_legal_moves()
        )

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
        self.move_boards["NO KING GAME"] = self.move_boards["GAME"] & ~king_bitboard
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
        # Finds attacks, pins, and blocks for all eight directions from king
        self.is_check = False
        blockable = pinned = 0
        for shift in KING_SHIFTS:
            first_attacker, first_attacker_path = king_attacker_and_path_in_direction(
                shift, king_bitboard, self.move_boards["GAME"]
            )
            if first_attacker:
                if self.is_attacker_in_direction(
                    first_attacker, first_attacker_path, shift
                ):
                    if self.is_check:
                        blockable = 0
                    else:
                        self.is_check = True
                        blockable |= first_attacker_path
                elif first_attacker & self.move_boards["SAME"]:
                    (
                        second_attacker,
                        second_attacker_path,
                    ) = king_attacker_and_path_in_direction(
                        shift,
                        king_bitboard,
                        self.move_boards["GAME"] & ~first_attacker_path,
                    )
                    if self.is_attacker_in_direction(
                        second_attacker,
                        second_attacker_path,
                        shift,
                        first_attacker=False,
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

    def is_attacker_in_direction(
        self,
        attacker: Bitboard,
        attacker_path: Bitboard,
        shift: int,
        first_attacker: bool = True,
    ) -> tuple[Bitboard, Bitboard]:
        """Determines whether given attacker is attacking king"""
        return attacker & self.move_boards["OPPOSITE"] and (
            any(
                attacker & self.move_boards[possible_attacker]
                for possible_attacker in POSSIBLE_ATTACKERS[shift]
            )
            or first_attacker
            and attacker_path.bit_count() == 1
            and attacker
            & (
                self.move_boards["k"]
                | self.move_boards["p"] * (shift in PAWN_CAPTURE_MASKS)
            )
        )

    def generate_knight_attacks(self) -> None:
        """Pre-computes all attacks possible by opposing knights in current position"""
        self.knight_attacks = {}
        for move in total_non_slider_moves("N", self.move_boards["n"]):
            self.knight_attacks[move.new_board] = (
                move.old_board if move.new_board not in self.knight_attacks else 0
            )
        self.total_knight_attacks = reduce(or_, self.knight_attacks, 0)

    def square_attacked(self, square: Bitboard) -> bool:
        """Checks if given square attacked by any opposing piece"""
        return square & self.total_knight_attacks or any(
            self.is_attacker_in_direction(
                *king_attacker_and_path_in_direction(
                    shift, square, self.move_boards["NO KING GAME"]
                ),
                shift,
            )
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
        for non_slider in NON_SLIDERS:
            yield from total_non_slider_moves(non_slider, self.move_boards[non_slider])

        # Generate remaining moves
        for move_func, piece in self.move_functions_and_pieces:
            yield from move_func(self.move_boards[piece])

    def slider_moves(self, slider, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for given slider"""
        for piece_mask in bitboard_piece_masks(piece_bitboard):
            yield from SLIDER_MOVES[slider][piece_mask][
                self.move_boards["GAME"] & SLIDER_RAYS[slider][piece_mask]
            ]

    def queen_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for queen piece"""
        yield from self.rook_moves(piece_bitboard)
        yield from self.bishop_moves(piece_bitboard)

    def rook_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for rook piece"""
        yield from self.slider_moves("R", piece_bitboard)

    def bishop_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for bishop piece"""
        yield from self.slider_moves("B", piece_bitboard)

    def pawn_moves(self, piece_bitboard: Bitboard) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for pawn piece"""
        single_mask = self.move_boards["~GAME"] >> 8
        if promotable := piece_bitboard & RANKS[6]:
            yield from self.promotion_moves(promotable, single_mask)
            piece_bitboard &= ~promotable

        single_push = piece_bitboard & single_mask
        yield from total_non_slider_moves("P SINGLE PUSH", single_push)
        yield from total_non_slider_moves(
            "P DOUBLE PUSH", (single_push & RANKS[1]) & self.move_boards["~GAME"] >> 16
        )

        capturable = self.move_boards["OPPOSITE"] | self.en_passant_bitboard
        for move in total_non_slider_moves(
            "P CAPTURE", piece_bitboard & ((capturable >> 7) | (capturable >> 9))
        ):
            if (shifted_piece := move.new_board) & self.move_boards["OPPOSITE"]:
                yield move
            elif shifted_piece & self.en_passant_bitboard:
                yield move._replace(
                    context_flag="EN PASSANT",
                    context_data=(
                        capture_bitboard := shifted_piece >> 8,
                        self.move_bitboard_to_square(capture_bitboard),
                    ),
                )

    def promotion_moves(
        self, promotable: Bitboard, single_mask: Bitboard
    ) -> Iterator[PseudoMove]:
        """Yields all pseudo-legal moves for pawn piece"""
        for move in total_non_slider_moves("P SINGLE PUSH", promotable & single_mask):
            yield from self.promotion_options(move)

        for move in total_non_slider_moves("P CAPTURE", promotable):
            if move.new_board & self.move_boards["OPPOSITE"]:
                yield from self.promotion_options(move)

    def promotion_options(self, move: PseudoMove) -> Iterator[PseudoMove]:
        """Ensures moves yielded with correct options and flags if promoting pawn"""
        move = move._replace(context_flag="PROMOTION")
        for piece in PROMOTION_PIECES[self.next_side]:
            yield move._replace(context_data=piece)
