class Bitboard:
    def __init__(self, fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"):
        self.fen_to_bitboard(fen)

    def fen_to_bitboard(self, fen):
        self.board = {piece: int() for piece in "KQRBNPkqrbnp"}
        for row_i, row in enumerate(reversed(fen.split("/"))):
            piece_i = 0
            for piece in reversed(row):
                if piece.isnumeric():
                    piece_i += int(piece)
                else:
                    self.board[piece] += 2 ** (row_i * 8 + piece_i)
                    piece_i += 1
