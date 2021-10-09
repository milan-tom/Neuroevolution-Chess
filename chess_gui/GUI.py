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

    def __init__(self, draw_board=True, fen=STARTING_FEN, bg="black"):
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

        # Stores background colour (as both RGB and mapped) and fills screen with colour
        self.bg = pygame.Color(bg)
        self.mapped_bg = self.design.map_rgb(self.bg)
        self.design.fill(self.bg)

        # Draws the board automatically unless specified not to
        if draw_board:
            self.draw_board()

    @property
    def pxarray(self):
        """Stores dummy window pixel array representation to access pixel colours"""
        return pygame.PixelArray(self.design)

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

    def dimension_to_pixel(self, dimension):
        return dimension * self.square_size

    def get_square_rect(self, row, column) -> pygame.Rect:
        """Returns pygame 'Rect' object for specified row and column"""
        return pygame.Rect(
            *map(self.dimension_to_pixel, (column, row, 1, 1)),
        )

    def get_dimension_range(self, dimension):
        return range(
            self.dimension_to_pixel(dimension), self.dimension_to_pixel(dimension + 1)
        )

    def get_square_range(self, row, column):
        return (
            (x, y)
            for x in self.get_dimension_range(column)
            for y in self.get_dimension_range(row)
        )

    def draw_board_squares(self):
        """Draws the board on the screen"""
        # Loops through each row and column, drawing each square within the board
        for row, column in self.chess.get_rows_and_columns():
            pygame.draw.rect(
                self.design,
                self.board_colours[(row + column) % 2],
                self.get_square_rect(row, column),
            )
        self.update()

    def draw_pieces(self):
        """Draws the pieces at the correct positions on the screen"""
        # Loops through each row and column, drawing squares and pieces
        for row, column in self.chess.get_rows_and_columns():
            # Draws piece at square if it exists
            if piece := self.chess.get_piece_at_square(row, column):
                self.draw_piece(piece, row, column)
        self.update()

    def draw_board(self):
        """Displays the current state of the board"""
        self.draw_board_squares()
        self.draw_pieces()

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
