"""
Handles all logic concerning initialising a chess state, generating moves from that
state, and executing them on the state
"""

from dataclasses import astuple, dataclass
from itertools import product
from operator import and_, or_
from typing import Callable, Iterable, Optional, Sequence

PIECES = "KQRBNPkqrbnp"
SIDES = ["WHITE", "BLACK"]
OPPOSITE_SIDES = {side: SIDES[(i + 1) % 2] for i, side in enumerate(SIDES)}
ROWS_AND_COLUMNS = tuple(product(range(8), repeat=2))

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EMPTY_FEN = "8/8/8/8/8/8/8/8 w - - 0 1"

Bitboard = int
Coord = Sequence[int]


def fen_portions(fen: str) -> list[str]:
    """Splits FEN into space-separated components"""
    return fen.split()


def fens_portion(fens: Iterable[str], portion_i: int) -> Iterable[str]:
    """Returns generator retrieving specified portion of multiple FENs"""
    return map(lambda fen: fen_portions(fen)[portion_i], fens)


def get_piece_side(piece: str) -> str:
    """Returns side which piece belongs to based on case of piece symbol"""
    return SIDES[piece.islower()]


def get_bitboards_to_edit(piece: str) -> tuple:
    """Returns tuple of bitboards requiring editing when moving piece"""
    return piece, get_piece_side(piece), "GAME"


def get_bitboard_index(square: Coord) -> int:
    """
    Returns index in bitboard corresponding to square coordinate in chess board
    :param square: Sequence of length 2 with row and column (0-based index
    increasing from top to bottom and left to right)
    """
    row, column = square
    return (7 - row) * 8 + 7 - column


@dataclass
class BoardMetadata:
    """Dataclass storing metadata associated with a board state"""

    next_side: str
    castling: str
    en_passant_square: str
    half_move_clock: str
    move_number: str

    def __post_init__(self) -> None:
        """Alters value of 'next_side' to conform with our labels for sides"""
        self.next_side = SIDES["wb".index(self.next_side)]

    @property
    def fen_metadata(self) -> str:
        """Returns fen representation of metadata"""
        metadata = astuple(self)
        return " ".join((metadata[0][0].lower(),) + metadata[1:])

    def update_metadata(self):
        """Updates board metadata after move"""
        self.next_side = OPPOSITE_SIDES[self.next_side]


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
        return bool(self.get_bitboard(piece) & (1 << get_bitboard_index(square)))

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
        """Adds presence of piece to required bitboards (changes bit at square to 1)"""
        self.edit_bitboard(piece, 1 << get_bitboard_index(square), or_)

    def remove_bitboard_square(self, piece: str, square: Coord) -> None:
        """Adds presence of piece to required bitboards (changes bit at square to 0)"""
        self.edit_bitboard(piece, ~(1 << get_bitboard_index(square)), and_)

    def move_piece_bitboard_square(
        self, piece: str, old_square: Coord, new_square: Coord
    ) -> None:
        """Changes square at which presence of piece shown in relevant bitboards"""
        self.remove_bitboard_square(piece, old_square)
        self.add_bitboard_square(piece, new_square)
