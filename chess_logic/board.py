"""
Handles all logic concerning initialising a chess state, generating moves from that
state, and executing them on the state
"""

from dataclasses import astuple
from itertools import combinations, product
from operator import and_, or_
from typing import Callable, Iterable, Optional, Sequence

from pydantic.dataclasses import dataclass

Bitboard = int
Coord = Sequence[int]

PIECES = "KQRBNPkqrbnp"
SIDES = ["WHITE", "BLACK"]
OPPOSITE_SIDE = {side: SIDES[(i + 1) % 2] for i, side in enumerate(SIDES)}
PIECE_SIDE = {piece: SIDES[piece.islower()] for piece in PIECES}
PIECE_OF_SIDE = {(side, piece.upper()): piece for piece, side in PIECE_SIDE.items()}

ROWS_AND_COLUMNS = tuple(product(range(8), repeat=2))
SQUARE_BITBOARD: dict[Coord, Bitboard] = {
    square: 1 << (7 - square[0]) * 8 + 7 - square[1] for square in ROWS_AND_COLUMNS
}
BITBOARD_SQUARE = dict(map(reversed, SQUARE_BITBOARD.items()))

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EMPTY_FEN = "8/8/8/8/8/8/8/8 w - - 0 1"

FEN_TO_BITBOARD_SQUARE = {
    f"{file}{rank_i + 1}": SQUARE_BITBOARD[(rank_i, file_i)]
    for file_i, file in enumerate(reversed("abcdefgh"))
    for rank_i in range(8)
} | {"-": 0}
BITBOARD_TO_FEN_SQUARE = dict(map(reversed, FEN_TO_BITBOARD_SQUARE.items()))

CASTLING_SYMBOLS = "KQkq"
FEN_CASTLING_TO_RIGHTS = {
    "".join(fen_castling): {
        side: [symbol for symbol in fen_castling if PIECE_SIDE[symbol] == side]
        for side in SIDES
    }
    for symbols_length in range(1, len(CASTLING_SYMBOLS) + 1)
    for fen_castling in combinations(CASTLING_SYMBOLS, symbols_length)
}
FEN_CASTLING_TO_RIGHTS["-"] = {side: [] for side in SIDES}

CASTLING_ROOK_MOVES = dict(zip(CASTLING_SYMBOLS, (((7, 7), (7, 5)), ((7, 0), (7, 3)))))
CASTLING_ROOK_MOVES |= {
    symbol.lower(): tuple(map(lambda square: (square[0] - 7, square[1]), squares))
    for symbol, squares in CASTLING_ROOK_MOVES.items()
}
ROOK_SQUARES_VOIDING_CASTLING = {
    squares[0]: castling for castling, squares in CASTLING_ROOK_MOVES.items()
}

UNSIGN_MASK = (1 << 64) - 1


def fen_portions(fen: str) -> list[str]:
    """Splits FEN into space-separated components"""
    return fen.split()


def fens_portion(fens: Iterable[str], portion_i: int) -> Iterable[str]:
    """Returns generator retrieving specified portion of multiple FENs"""
    return map(lambda fen: fen_portions(fen)[portion_i], fens)


def get_bitboards_to_edit(piece: str) -> tuple:
    """Returns tuple of bitboards requiring editing when moving piece"""
    return piece, PIECE_SIDE[piece], "GAME"


def unsign_bitboard(board: Bitboard) -> Bitboard:
    """
    Converts bitboard to unsigned 64-bit bitboard (negative values could arise from
    two's complement when bitwise NOT used on bitboard as Python has no length limit for
    integers)
    """
    return board & UNSIGN_MASK


def rotate_bitboard(board: Bitboard) -> Bitboard:
    """Reverses single bitboard bitwise"""
    return int(bin(unsign_bitboard(board)).lstrip("0b").zfill(64)[::-1], 2)


@dataclass
class BoardMetadata:
    """Dataclass storing metadata associated with a board state"""

    # pylint: disable=attribute-defined-outside-init

    next_side: str
    fen_castling: str
    fen_en_passant_square: str
    half_move_clock: int
    move_number: int

    def __post_init_post_parse__(self) -> None:
        """Alters value of 'next_side' to conform with our labels for sides"""
        self.next_side = SIDES["wb".index(self.next_side)]
        self.side_castling_rights = FEN_CASTLING_TO_RIGHTS[self.fen_castling]
        self.en_passant_bitboard = FEN_TO_BITBOARD_SQUARE[self.fen_en_passant_square]

    @property
    def fen_metadata(self) -> str:
        """Returns fen representation of metadata"""
        self.fen_castling = list(FEN_CASTLING_TO_RIGHTS.keys())[
            list(FEN_CASTLING_TO_RIGHTS.values()).index(self.side_castling_rights)
        ]
        self.fen_en_passant_square = BITBOARD_TO_FEN_SQUARE[
            rotate_bitboard(self.en_passant_bitboard)
            if self.next_side == "WHITE"
            else self.en_passant_bitboard
        ]
        metadata = tuple(map(str, astuple(self)))
        return " ".join((metadata[0][0].lower(),) + metadata[1:])

    def update_metadata(
        self,
        moved_piece: str,
        old_square: Coord,
        en_passant_bitboard: Bitboard,
        captured_piece: Optional[str],
    ) -> None:
        """Updates board metadata after move"""
        # Updates castling rights
        if current_castling_rights := self.side_castling_rights[self.next_side]:
            match moved_piece:
                case "K":
                    current_castling_rights.clear()
                case "R":
                    if old_square in ROOK_SQUARES_VOIDING_CASTLING and (
                        voided_right := PIECE_OF_SIDE[
                            (self.next_side, ROOK_SQUARES_VOIDING_CASTLING[old_square])
                        ]
                    ):
                        current_castling_rights.remove(voided_right)

        # Updates remaining metadata
        self.next_side = OPPOSITE_SIDE[self.next_side]
        self.en_passant_bitboard = en_passant_bitboard
        self.half_move_clock = (
            0
            if moved_piece.upper() == "P" or captured_piece is not None
            else self.half_move_clock + 1
        )
        self.move_number += self.next_side == "WHITE"


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
        fen_positions, *metadata = fen_portions(fen)
        super().__init__(*metadata)
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

    def get_bitboard(self, piece: str) -> Bitboard:
        """Returns integer representing bitboard of given piece"""
        return self.boards[piece]

    def piece_exists_at_square(self, square: Coord, piece: str) -> bool:
        """Checks whether piece exists at square for given board"""
        return bool(self.get_bitboard(piece) & SQUARE_BITBOARD[square])

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
        for bitboard in get_bitboards_to_edit(piece):
            self.boards[bitboard] = command(self.get_bitboard(bitboard), mask)

    def add_bitboard_square(self, piece: str, square: Coord) -> None:
        """Adds piece presence to required bitboards (changes square bit to 1)"""
        self.edit_bitboard(piece, SQUARE_BITBOARD[square], or_)

    def remove_bitboard_square(self, piece: str, square: Coord) -> None:
        """Removes piece presence from required bitboards (changes square bit to 0)"""
        self.edit_bitboard(piece, ~SQUARE_BITBOARD[square], and_)

    def move_piece_bitboard_square(
        self, piece: str, old_square: Coord, new_square: Coord
    ) -> None:
        """Changes square at which presence of piece shown in relevant bitboards"""
        self.remove_bitboard_square(piece, old_square)
        self.add_bitboard_square(piece, new_square)
