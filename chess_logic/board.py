"""
Handles all logic concerning initialising a chess state, generating moves from that
state, and executing them on the state
"""

from collections import deque
from dataclasses import astuple, dataclass, field
from functools import partial
from itertools import product
from operator import and_, or_
from typing import Callable, Optional, Sequence

from numba import njit, types

Bitboard = int
Coord = Sequence[int]

PIECES = "KQRBNPkqrbnp"
SIDES = ["WHITE", "BLACK"]
OPPOSITE_SIDE = {side: SIDES[(i + 1) % 2] for i, side in enumerate(SIDES)}
PIECE_SIDE = {piece: SIDES[piece.islower()] for piece in PIECES}

ROWS_AND_COLUMNS = tuple(product(range(8), repeat=2))
SQUARE_BITBOARD_INDEX = {
    square: (7 - square[0]) * 8 + 7 - square[1] for square in ROWS_AND_COLUMNS
}
SQUARE_BITBOARD = {
    square: 1 << index for square, index in SQUARE_BITBOARD_INDEX.items()
}
BITBOARD_SQUARE = dict(map(reversed, SQUARE_BITBOARD.items()))

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
State = tuple[int | str]

FEN_TO_BITBOARD_SQUARE = {
    f"{file}{8 - rank_i}": SQUARE_BITBOARD[(rank_i, file_i)]
    for file_i, file in enumerate("abcdefgh")
    for rank_i in range(8)
} | {"-": 0}
BITBOARD_TO_FEN_SQUARE = dict(map(reversed, FEN_TO_BITBOARD_SQUARE.items()))

CASTLING_SYMBOLS = "KQkq"
CastlingRights = dict[str, list[str]]
CASTLING_ROOK_MOVES = dict(zip(CASTLING_SYMBOLS, (((7, 7), (7, 5)), ((7, 0), (7, 3)))))
CASTLING_ROOK_MOVES |= {
    symbol.lower(): tuple(map(lambda square: (square[0] - 7, square[1]), squares))
    for symbol, squares in CASTLING_ROOK_MOVES.items()
}
ROOK_SQUARES_VOIDING_CASTLING = {
    squares[0]: castling for castling, squares in CASTLING_ROOK_MOVES.items()
}


def void_castling_by_rook(
    castling_rights: list[str], rook_square: Coord, lost_castling_rights: list[str]
) -> Optional[str]:
    """Removes castling right voided by rook move/capture if any"""
    if (right := ROOK_SQUARES_VOIDING_CASTLING.get(rook_square)) in castling_rights:
        castling_rights.remove(right)
        lost_castling_rights.append(right)


UNSIGN_MASK = (1 << 64) - 1
MAX_BITBOARD = 1 << 64 - 1


@njit(types.uint64(types.uint64))
def unsigned_not(board: Bitboard) -> Bitboard:
    """Returns positive version of boolean NOT of bitboard, enabling use with numba"""
    return ~board & UNSIGN_MASK


@njit(types.float64(types.uint64))
def normalize_bitboard(board: Bitboard) -> float:
    """Converts 64 bit bitboard to float between 0 and 1"""
    return board / MAX_BITBOARD


@njit(types.uint64(types.uint64), locals=dict(board=types.uint64))
def rotate_bitboard(board: Bitboard) -> Bitboard:
    """Reverses single bitboard bitwise"""
    board = ((board & 0x5555555555555555) << 1) | ((board & 0xAAAAAAAAAAAAAAAA) >> 1)
    board = ((board & 0x3333333333333333) << 2) | ((board & 0xCCCCCCCCCCCCCCCC) >> 2)
    board = ((board & 0xF0F0F0F0F0F0F0F) << 4) | ((board & 0xF0F0F0F0F0F0F0F0) >> 4)
    board = ((board & 0xFF00FF00FF00FF) << 8) | ((board & 0xFF00FF00FF00FF00) >> 8)
    board = ((board & 0xFFFF0000FFFF) << 16) | ((board & 0xFFFF0000FFFF0000) >> 16)
    board = ((board & 0xFFFFFFFF) << 32) | ((board & 0xFFFFFFFF00000000) >> 32)
    return board


def swap_halves(data: list, half_length: int) -> list:
    """Swaps the two halves of a list given half length"""
    return data[half_length:] + data[half_length:]


@dataclass
class BoardMetadata:
    """Dataclass storing metadata associated with a board state"""

    next_side: str
    fen_castling: str
    fen_en_passant_square: str
    half_move_clock: str | int
    move_number: str | int
    previous_states: deque[Optional[State]] = field(
        default_factory=partial(deque, [None] * 10, maxlen=10), init=False
    )

    def __post_init__(self) -> None:
        """Alters fen values  to represent data in more suitable forms"""
        self.next_side = SIDES["wb".index(self.next_side)]
        self.side_castling_rights = {
            side: [
                symbol
                for symbol in self.fen_castling
                if symbol != "-" and PIECE_SIDE[symbol] == side
            ]
            for side in SIDES
        }
        self.en_passant_bitboard = FEN_TO_BITBOARD_SQUARE[self.fen_en_passant_square]
        if self.en_passant_bitboard and self.next_side == "BLACK":
            self.en_passant_bitboard = rotate_bitboard(self.en_passant_bitboard)
        self.half_move_clock, self.move_number = map(
            int, (self.half_move_clock, self.move_number)
        )

    @property
    def fen_metadata(self) -> str:
        """Returns fen representation of metadata"""
        self.fen_castling = (
            "".join(sorted(sum(rights, [])))
            if any(rights := self.side_castling_rights.values())
            else "-"
        )
        self.fen_en_passant_square = BITBOARD_TO_FEN_SQUARE[
            rotate_bitboard(self.en_passant_bitboard)
            if self.next_side == "BLACK"
            else self.en_passant_bitboard
        ]
        metadata = tuple(map(str, astuple(self)[:-1]))
        return " ".join((metadata[0][0].lower(),) + metadata[1:])

    @property
    def repetition_metadata(self) -> tuple:
        """Returns tuple containing metadata necessary to check repetition"""
        return self.next_side, self.side_castling_rights, self.en_passant_bitboard

    def update_metadata(
        self,
        old_square: Coord,
        new_square: Coord,
        en_passant_bitboard: Bitboard,
        moved_piece: str,
        captured_piece: Optional[str],
        previous_state: State,
    ) -> tuple[CastlingRights, State]:
        """Updates board metadata after move"""
        moved_piece = moved_piece.upper()
        # Updates castling rights
        castling_rights_lost = {side: [] for side in SIDES}
        if next_side_castling_rights := self.side_castling_rights[self.next_side]:
            next_side_castling_rights_lost = castling_rights_lost[self.next_side]
            match moved_piece:
                case "K":
                    next_side_castling_rights_lost.extend(next_side_castling_rights)
                    next_side_castling_rights.clear()
                case "R":
                    void_castling_by_rook(
                        next_side_castling_rights,
                        old_square,
                        next_side_castling_rights_lost,
                    )

        # Updates remaining metadata
        self.next_side = OPPOSITE_SIDE[self.next_side]
        self.en_passant_bitboard = en_passant_bitboard
        self.half_move_clock = (
            0
            if moved_piece == "P" or captured_piece is not None
            else self.half_move_clock + 1
        )
        self.move_number += self.next_side == "WHITE"

        # Update previous fens for twofold repetition
        state_lost = self.previous_states[0]
        self.previous_states.append(previous_state)

        # Removes castling right of new side to move if relevant rook just captured
        if captured_piece is not None and captured_piece.upper() == "R":
            void_castling_by_rook(
                self.side_castling_rights[self.next_side],
                new_square,
                castling_rights_lost[self.next_side],
            )
        return castling_rights_lost, state_lost

    def undo_metadata_update(
        self,
        old_half_move_clock: int,
        old_en_passant_bitboard: Bitboard,
        castling_rights_lost: CastlingRights,
        state_lost: State,
    ) -> State:
        """Undos update board metadata after move"""
        self.half_move_clock = old_half_move_clock
        self.move_number -= self.next_side == "WHITE"
        self.next_side = OPPOSITE_SIDE[self.next_side]
        self.en_passant_bitboard = old_en_passant_bitboard
        for side, rights_lost in castling_rights_lost.items():
            self.side_castling_rights[side].extend(rights_lost)
        previous_state = self.previous_states[-1]
        self.previous_states.appendleft(state_lost)
        return previous_state


class ChessBoard(BoardMetadata):
    """
    Stores the state of a single chess board as collection of bitboards:
        - Initialises chess state (supports Forsyth–Edwards Notation)
        - Generates legal moves from positions
    """

    def __init__(self, fen: str) -> None:
        """
        Initialises chess state from standard starting position or from optional
        Forsyth–Edwards Notation (FEN) argument
        """
        fen_positions, *metadata = fen.split()
        super().__init__(*metadata)
        self.cached_state = None
        self.fen_positions_to_bitboards(fen_positions)

    def fen_positions_to_bitboards(self, fen_positions: str) -> None:
        """
        Store piece positions obtained from positions portion of FEN as dictionary with
        key for each piece and game as a whole and values as bitboard for given piece
        """
        # Initialize 'self.boards' dictionary with empty board for each piece key
        self.boards = dict.fromkeys(list(PIECES) + ["GAME"] + SIDES, 0)

        # Calculate integer representing bitboard for each piece and whole game from FEN
        for row_i, row in enumerate(fen_positions.split("/")):
            column_i = 0
            for piece in row:
                if piece.isnumeric():
                    column_i += int(piece)
                else:
                    self.add_bitboard_square(piece, (row_i, column_i))
                    column_i += 1

    @property
    def fen(self) -> str:
        """Returns the FEN of the current board state"""
        rows = []
        for row_i in range(8):
            row = ""
            empty_spaces = 0
            for column_i in range(8):
                if piece := self.get_piece_at_square((row_i, column_i)):
                    if empty_spaces:
                        row += str(empty_spaces)
                    row += piece
                    empty_spaces = 0
                else:
                    empty_spaces += 1
            if empty_spaces:
                row += str(empty_spaces)
            rows.append(row)

        return f"{'/'.join(rows)} {self.fen_metadata}"

    @property
    def numeric_repr(self) -> list[int | float]:
        """Returns list containing numeric representations of relevant state portions"""
        castling_rights = [
            bool(right in self.side_castling_rights[PIECE_SIDE[right]])
            for right in CASTLING_SYMBOLS
        ]
        bitboards = list(self.boards.values())[:12]
        if self.next_side == "BLACK":
            bitboards = list(map(rotate_bitboard, swap_halves(bitboards, 6)))
        return (
            list(map(normalize_bitboard, bitboards + [self.en_passant_bitboard]))
            + castling_rights
        )

    @property
    def current_state(self) -> None:
        """Returns representation of current state used for checking repetition"""
        if self.cached_state is None:
            self.cached_state = tuple(self.boards.values()) + self.repetition_metadata
        return self.cached_state

    def piece_exists_at_square(self, square: Coord, piece: str) -> bool:
        """Checks whether piece exists at square for given board"""
        return bool(self.boards[piece] & SQUARE_BITBOARD[square])

    def get_piece_at_square(self, square: Coord) -> Optional[str]:
        """Returns piece at square on chess board if there is one and 'None' if not"""
        if self.piece_exists_at_square(square, "GAME"):
            for piece in PIECES:
                if self.piece_exists_at_square(square, piece):
                    return piece
        return None

    def edit_bitboard(self, piece: str, mask: int, command: Callable):
        """
        Edits all bitboards requiring editing when moving piece by applying given
        function between bitboard and mask at index
        """
        for bitboard in (piece, PIECE_SIDE[piece], "GAME"):
            self.boards[bitboard] = command(self.boards[bitboard], mask)

    def add_bitboard_square(self, piece: str, square: Coord) -> None:
        """Adds piece presence to required bitboards (changes square bit to 1)"""
        self.edit_bitboard(piece, SQUARE_BITBOARD[square], or_)

    def remove_bitboard_square(self, piece: str, square: Coord) -> None:
        """Removes piece presence from required bitboards (changes square bit to 0)"""
        self.edit_bitboard(piece, unsigned_not(SQUARE_BITBOARD[square]), and_)

    def move_piece_bitboard_square(
        self, piece: str, old_square: Coord, new_square: Coord
    ) -> None:
        """Changes square at which presence of piece shown in relevant bitboards"""
        self.remove_bitboard_square(piece, old_square)
        self.add_bitboard_square(piece, new_square)
