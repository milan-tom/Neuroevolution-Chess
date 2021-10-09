import os
from threading import Thread

import pygame

from core_chess.chess_logic import Chess, STARTING_FEN

# Adds dummy video driver for machines without displays (e.g. testing from Linux server)
if os.name == "posix" and "DISPLAY" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
# Instructs OS to open window slightly offset so all of it fits on the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0, 20"


class ChessGUI:
    """Displays a GUI for a given chess state"""

    def __init__(self, fen=STARTING_FEN):
        self.chess = Chess(fen)
        """Initialises pygame components and draws board"""
        pygame.display.set_caption("Chess GUI")
        self.display = pygame.display.set_mode((0, 0), pygame.RESIZABLE)

        # Imports all piece images (source:
        # https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
        image_path = os.path.join(os.path.dirname(__file__), "images", "{}{}.png")
        self.piece_images = {
            piece: pygame.image.load(
                image_path.format(self.chess.players[~piece.isupper()], piece.upper())
            )
            for piece in self.chess.pieces
        }

        # Stores colour codes for light and dark squares, respectively
        self.board_colours = ((255, 255, 255), (120, 81, 45))

        # Creates dummy window for implementing design, enabling scaling to any screen
        self.design = pygame.Surface((1536, 864))
        self.square_size = 108  # Size of square in pixels to fill dummy window's height

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
        self.design.blit(
            piece_image,
            self.relative_position(piece_image, row, column),
        )

    def update(self):
        """Scales dummy design window to actual screen size and renders changes"""
        frame = pygame.transform.scale(self.design, self.display.get_size())
        self.display.blit(frame, frame.get_rect())
        pygame.display.flip()

    def draw_board(self):
        """Displays the current state of the board"""
        # Initialises list of rectangle (i.e. board square) coordinates
        rectangle = [0, 0, self.square_size, self.square_size]
        # Loops through each row and column, drawing squares and pieces
        for row in range(8):
            # Updates coordinates and square colours as appropriate
            rectangle[1] = row * self.square_size
            for column in range(8):
                rectangle[0] = column * self.square_size
                # Draws chess board square and piece at square if it exists
                pygame.draw.rect(
                    self.design, self.board_colours[(row + column) % 2], rectangle
                )
                piece_at_square = self.chess.get_piece_at_square(7 - row, column)
                if piece_at_square is not None:
                    self.draw_piece(piece_at_square, row, column)

        self.update()

    def __enter__(self):
        """
        Enables use of GUI in 'with' statement, keeping while loop that keeps GUI open
        running in separate thread to allow other code to execute
        """
        Thread(target=self.mainloop).start()
        return self

    def mainloop(self):
        """Keeps GUI running, handling events and rendering changes"""
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Enables use of GUI in 'with' statement, closing when with statement ends"""
        self.running = False


if __name__ == "__main__":
    chess_gui = ChessGUI()
    chess_gui.mainloop()
