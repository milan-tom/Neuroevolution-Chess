from itertools import product

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EMPTY_FEN = "8/8/8/8/8/8/8/8 w - - 0 1"


class Chess:
    def __init__(self, fen=STARTING_FEN):
        self.pieces = "KQRBNPkqrbnp"
        self.players = "WB"
        (
            positions,
            self.next_colour,
            self.castling,
            self.en_passant_square,
            self.half_move_clock,
            self.move_number,
        ) = self.fen_portions(fen)
        self.board = dict.fromkeys(list(self.pieces) + ["game"], 0)
        self.fen_positions(positions)

    def fen_portions(self, fen):
        return fen.split()

    def fens_portion(self, fens, portion_i):
        return map(lambda fen: self.fen_portions(fen)[portion_i], fens)

    def fen_positions(self, positions):
        for row_i, row in enumerate(positions.split("/")):
            piece_i = 0
            for piece in row:
                if piece.isnumeric():
                    piece_i += int(piece)
                else:
                    self.board[piece] += 1 << self.get_bitboard_index((row_i, piece_i))
                    self.board["game"] += 1 << self.get_bitboard_index((row_i, piece_i))
                    piece_i += 1

    @property
    def fen(self):
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
                self.next_colour,
                self.castling,
                self.en_passant_square,
                self.half_move_clock,
                self.move_number,
            )
        )

    def get_bitboard(self, piece):
        return self.board[piece]

    def get_bitboard_index(self, square_coords):
        row, column = square_coords
        return (7 - row) * 8 + 7 - column

    def piece_exists_at_square(self, square_coords, bitboard):
        return bitboard & (1 << self.get_bitboard_index(square_coords))

    def get_piece_at_square(self, square_coords):
        if self.piece_exists_at_square(square_coords, self.get_bitboard("game")):
            for piece in self.pieces:
                if self.piece_exists_at_square(square_coords, self.get_bitboard(piece)):
                    return piece
        return None

    def get_rows_and_columns(self):
        return product(range(8), repeat=2)

    def remove_bitboard_index(self, piece, index):
        self.board[piece] &= ~(1 << index)

    def add_bitboard_index(self, piece, index):
        self.board[piece] |= 1 << index

    def replace_piece_bitboard_index(self, piece, old_index, new_index):
        self.remove_bitboard_index(piece, old_index)
        self.add_bitboard_index(piece, new_index)

    def get_moves(self, piece, square_coords):
        row, column = square_coords
        return (
            (row + row_change, column + column_change)
            for row_change, column_change in product(range(-1, 2), repeat=2)
            if row_change or column_change
        )

    def move(self, old_square_coord, new_square_coord):
        old_bitboard_index = self.get_bitboard_index(old_square_coord)
        new_bitboard_index = self.get_bitboard_index(new_square_coord)
        for piece in ("game", self.get_piece_at_square(old_square_coord)):
            self.replace_piece_bitboard_index(
                piece, old_bitboard_index, new_bitboard_index
            )
