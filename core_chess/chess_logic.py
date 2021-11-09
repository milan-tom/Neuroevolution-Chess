"""
Handles all logic concerning initialising a chess state, generating moves from that
state, and executing them on the state
"""

from itertools import product
from operator import and_, or_
from typing import Callable, Iterable, Optional, Sequence

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EMPTY_FEN = "8/8/8/8/8/8/8/8 w - - 0 1"

Coord = Sequence[int]


class Chess:
    """
    Stores the state of a single chess board as collection of bitboards:
        - Initialises chess state (supports Forsyth–Edwards Notation)
        - Generates legal moves from positions
    """

    def __init__(self, fen: str = STARTING_FEN) -> None:
        """
        Initialises chess state from standard starting position or from optional
        Forsyth–Edwards Notation (FEN) argument
        """
        self.pieces = "KQRBNPkqrbnp"
        self.players = ["WHITE", "BLACK"]
        (
            fen_positions,
            fen_next_colour,
            self.castling,
            self.en_passant_square,
            self.half_move_clock,
            self.move_number,
        ) = fen.split()
        self.next_colour = self.players["wb".index(fen_next_colour)]
        self.fen_positions_to_bitboards(fen_positions)

    def fen_portions(self, fen: str) -> list[str]:
        """Splits FEN into space-separated components"""
        return fen.split()

    def fens_portion(self, fens: Iterable[str], portion_i: int) -> Iterable[str]:
        """Returns generator retrieving specified portion of multiple FENs"""
        return map(lambda fen: self.fen_portions(fen)[portion_i], fens)

    def fen_positions_to_bitboards(self, fen_positions: str) -> None:
        """
        Store piece positions obtained from positions portion of FEN as dictionary with
        key for each piece and game as a whole and values as bitboard for given piece
        """
        # Initialize 'self.boards' dictionary with empty board for each piece key
        self.boards = dict.fromkeys(list(self.pieces) + ["GAME"] + self.players, 0)

        # Calculate integer representing bitboard for each piece and whole game from FEN
        for row_i, row in enumerate(fen_positions.split("/")):
            column_i = 0
            for piece in row:
                if piece.isnumeric():
                    column_i += int(piece)
                else:
                    bitboard_index = self.get_bitboard_index((row_i, column_i))
                    self.add_bitboard_index(piece, bitboard_index)
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

        return " ".join(
            (
                "/".join(rows),
                self.next_colour[0].lower(),
                self.castling,
                self.en_passant_square,
                self.half_move_clock,
                self.move_number,
            )
        )

    def get_piece_side(self, piece: str) -> str:
        """Returns side which piece belongs to based on case of piece symbol"""
        return self.players[piece.islower()]

    def get_bitboard(self, piece: str) -> int:
        """Returns integer representing bitboard of given piece"""
        return self.boards[piece]

    def get_bitboard_index(self, square: Coord) -> int:
        """
        Returns index in bitboard corresponding to square coordinate in chess board
        :param square: Sequence of length 2 with row and column (0-based index
        increasing from top to bottom and left to right)
        """
        row, column = square
        return (7 - row) * 8 + 7 - column

    def piece_exists_at_square(self, square: Coord, piece: str) -> bool:
        """Checks whether piece exists at square for given board"""
        return bool(self.get_bitboard(piece) & (1 << self.get_bitboard_index(square)))

    def get_piece_at_square(self, square: Coord) -> Optional[str]:
        """Returns piece at square on chess board if there is one and 'None' if not"""
        if self.piece_exists_at_square(square, "GAME"):
            for piece in self.pieces:
                if self.piece_exists_at_square(square, piece):
                    return piece

    def get_rows_and_columns(self) -> Iterable[Coord]:
        """Returns generator yielding all possible square coordinates"""
        return product(range(8), repeat=2)

    def get_bitboards_to_edit(self, piece: str) -> tuple:
        """Returns tuple of bitboards requiring editing when moving piece"""
        return piece, self.get_piece_side(piece), "GAME"

    def edit_bitboard(self, piece: str, mask: int, command: Callable):
        """
        Edits all bitboards requiring editing when moving piece by applying given
        function between bitboard and mask at index
        """
        for bitboard in self.get_bitboards_to_edit(piece):
            self.boards[bitboard] = command(self.get_bitboard(bitboard), mask)

    def add_bitboard_index(self, piece: str, index: int) -> None:
        """Adds presence of piece to required bitboards (changes bit at index to 1)"""
        self.edit_bitboard(piece, 1 << index, or_)

    def remove_bitboard_index(self, piece: str, index: int) -> None:
        """Adds presence of piece to required bitboards (changes bit at index to 0)"""
        self.edit_bitboard(piece, ~(1 << index), and_)

    def replace_piece_bitboard_index(
        self, piece: str, old_index: int, new_index: int
    ) -> None:
        """Removes old piece and adds new piece to corresponding bitboards"""
        self.remove_bitboard_index(piece, old_index)
        self.add_bitboard_index(piece, new_index)

    def legal_moves_from_square(self, piece: str, square: Coord) -> Iterable[Coord]:
        """
        Returns all legal moves in the current board state from specific square on board
        (currently just temporary placeholders)
        """
        row, column = square
        return (
            (row + row_change, column + column_change)
            for row_change in range(-bool(row), (row < 7) + 1)
            for column_change in range(-bool(column), (column < 7) + 1)
            if row_change or column_change
        )

    def move(self, old_square: Coord, new_square: Coord) -> None:
        """Moves piece at given square to new square"""
        self.replace_piece_bitboard_index(
            self.get_piece_at_square(old_square),
            self.get_bitboard_index(old_square),
            self.get_bitboard_index(new_square),
        )
