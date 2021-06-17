import pygame
from core_chess.chess_logic import Chess


class ChessGUI:
    def __init__(self):
        self.chess = Chess()
        self.piece_images = {
            piece: pygame.image.load(
                f"Images/{self.chess.players[~piece.isupper()]}{piece}.gif"
            )
            for piece in self.chess.pieces
        }
        self.surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.board_colours = ((255, 255, 255), (120, 81, 45))
        self.square_size = self.surface.get_height() // 8
        self.draw_board()

    def relative_position_shift(self, image_dimension):
        return (self.square_size - image_dimension) // 2

    def relative_position(self, image, row, column):
        return (
            column * self.square_size
            + self.relative_position_shift(image.get_height()),
            row * self.square_size + self.relative_position_shift(image.get_width()),
        )

    def draw_piece(self, piece, row, column):
        piece_image = self.piece_images[piece]
        self.surface.blit(
            piece_image,
            self.relative_position(piece_image, row, column),
        )

    def draw_board(self):
        rectangle = [0, 0, self.square_size, self.square_size]
        for row in range(8):
            rectangle[1] = row * self.square_size
            for column in range(8):
                rectangle[0] = column * self.square_size
                pygame.draw.rect(
                    self.surface, self.board_colours[(row + column) % 2], rectangle
                )

                piece_at_square = self.chess.get_piece_at_square(7 - row, column)
                if piece_at_square is not None:
                    self.draw_piece(piece_at_square, row, column)

        pygame.display.update()

    def mainloop(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False


chess_gui = ChessGUI()
chess_gui.mainloop()
