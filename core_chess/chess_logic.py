STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EMPTY_FEN = "8/8/8/8/8/8/8/8 w - - 0 1"


class Chess:
    def __init__(self, fen=STARTING_FEN):
        self.pieces = "KQRBNPkqrbnp"
        self.players = "wb"
        (
            positions,
            self.next_colour,
            self.castling,
            self.en_passant_square,
            self.half_move_clock,
            self.move_number,
        ) = fen.split()
        self.board = dict.fromkeys(list(self.pieces) + ["game"], 0)
        self.fen_positions(positions)

    def fen_positions(self, positions):
        for row_i, row in enumerate(reversed(positions.split("/"))):
            piece_i = 0
            for piece in reversed(row):
                if piece.isnumeric():
                    piece_i += int(piece)
                else:
                    self.board[piece] += 1 << (row_i * 8 + piece_i)
                    self.board["game"] += 1 << (row_i * 8 + piece_i)
                    piece_i += 1

    @property
    def fen(self):
        """Returns the FEN of the current board state"""
        rows = []
        for row_i in range(8):
            row = ""
            empty_spaces = 0
            for column_i in range(8):
                for piece, board in self.board.items():
                    if board & (1 << ((7 - row_i) * 8 + (7 - column_i))):
                        if empty_spaces:
                            row += str(empty_spaces)
                        row += piece
                        empty_spaces = 0
                        break
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

    def get_game_bitboard(self):
        return self.board["game"]

    def get_bitboard(self, piece):
        return self.board[piece]

    def get_square_bitboard_index(self, row, column):
        return row * 8 + 7 - column

    def piece_exists_at_square(self, row, column, bitboard):
        return bitboard & (1 << self.get_square_bitboard_index(row, column))

    def get_piece_at_square(self, row, column):
        if self.piece_exists_at_square(row, column, self.get_game_bitboard()):
            for piece in self.pieces:
                if self.piece_exists_at_square(row, column, self.get_bitboard(piece)):
                    return piece
        return None
