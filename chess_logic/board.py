"""
Handles all logic concerning initialising a chess state, generating moves from that
state, and executing them on the state
"""

from dataclasses import astuple
from itertools import product
from operator import and_, or_
from typing import Callable, Iterable, Optional, Sequence

from pydantic.dataclasses import dataclass

Bitboard = int
Coord = Sequence[int]

PIECES = "KQRBNPkqrbnp"
SIDES = ["WHITE", "BLACK"]
OPPOSITE_SIDE = {side: SIDES[(i + 1) % 2] for i, side in enumerate(SIDES)}
PIECE_SIDE = {piece: SIDES[piece.islower()] for piece in PIECES}

ROWS_AND_COLUMNS = tuple(product(range(8), repeat=2))
SQUARE_BITBOARD: dict[Coord, Bitboard] = {
    square: 1 << (7 - square[0]) * 8 + 7 - square[1] for square in ROWS_AND_COLUMNS
}
BITBOARD_SQUARE = dict(map(reversed, SQUARE_BITBOARD.items()))

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

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
        metadata = tuple(map(str, astuple(self)))
        return " ".join((metadata[0][0].lower(),) + metadata[1:])

    def update_metadata(
        self,
        old_square: Coord,
        new_square: Coord,
        en_passant_bitboard: Bitboard,
        moved_piece: str,
        captured_piece: Optional[str],
    ) -> CastlingRights:
        """Updates board metadata after move"""
        # Updates castling rights
        castling_rights_lost = {side: [] for side in SIDES}
        if next_side_castling_rights := self.side_castling_rights[self.next_side]:
            next_side_castling_rights_lost = castling_rights_lost[self.next_side]
            match moved_piece.upper():
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
            if moved_piece.upper() == "P" or captured_piece is not None
            else self.half_move_clock + 1
        )
        self.move_number += self.next_side == "WHITE"

        # Removes castling right of new side to move if relevant rook just captured
        if captured_piece is not None and captured_piece.upper() == "R":
            void_castling_by_rook(
                self.side_castling_rights[self.next_side],
                new_square,
                castling_rights_lost[self.next_side],
            )
        return castling_rights_lost

    def undo_metadata_update(
        self,
        old_half_move_clock: int,
        old_en_passant_bitboard: Bitboard,
        castling_rights_lost: CastlingRights,
    ) -> None:
        """Undos update board metadata after move"""
        self.half_move_clock = old_half_move_clock
        self.move_number -= self.next_side == "WHITE"
        self.next_side = OPPOSITE_SIDE[self.next_side]
        self.en_passant_bitboard = old_en_passant_bitboard
        for side, rights_lost in castling_rights_lost.items():
            self.side_castling_rights[side].extend(rights_lost)


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
