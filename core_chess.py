class Chess:
    def __init__(self, fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"):
        (
            positions,
            self.next_colour,
            self.castling,
            self.en_passant_square,
            self.half_move_clock,
            self.move_number,
        ) = fen.split()

        self.board = {piece: int() for piece in "KQRBNPkqrbnp"}
        for row_i, row in enumerate(reversed(positions.split("/"))):
            piece_i = 0
            for piece in reversed(row):
                if piece.isnumeric():
                    piece_i += int(piece)
                else:
                    self.board[piece] += 1 << (row_i * 8 + piece_i)
                    piece_i += 1
