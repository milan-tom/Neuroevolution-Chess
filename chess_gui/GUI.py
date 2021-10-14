import os
from itertools import product
from time import process_time

import pygame
import pygame_widgets

from core_chess.chess_logic import Chess, STARTING_FEN

# Adds dummy video driver for machines without displays (e.g. testing from Linux server)
if os.name == "posix" and "DISPLAY" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
# Instructs OS to open window slightly offset so all of it fits on the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0, 20"


class ChessGUI:
    """Displays a GUI for a given chess state"""

    def __init__(self, draw_board=True, fen=STARTING_FEN, bg="black"):
        """Initialises pygame components and draws board"""
        pygame.init()
        pygame.display.set_caption("Chess GUI")
        self.display = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        self.buttons = []
        self.running = True

        # Initialises chess object to manage chess rules for GUI
        self.chess = Chess(fen)

        # Imports all piece images (source:
        # https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
        image_path = os.path.join(os.path.dirname(__file__), "images", "{}{}.png")
        self.piece_images = {}
        for piece in self.chess.pieces:
            piece_image = pygame.image.load(
                image_path.format(self.chess.players[piece.islower()], piece.upper())
            )
            self.piece_images[piece] = piece_image.subsurface(
                piece_image.get_bounding_rect()
            )

        # Stores colour codes for light and dark squares, respectively
        self.board_colours = ((255, 255, 255), (120, 81, 45))

        # Creates dummy window for implementing design, enabling scaling to any screen
        self.design = pygame.Surface((1536, 864))
        self.square_size = 108  # Size of square in pixels to fill dummy window's height

        # Stores background colour (as both RGB and mapped) and fills screen with colour
        self.bg = pygame.Color(bg)
        self.mapped_bg = self.design.map_rgb(self.bg)
        self.clear()

        # Draws the board automatically unless specified not to
        if draw_board:
            self.draw_board()

    @property
    def pxarray(self):
        """Stores dummy window pixel array representation to access pixel colours"""
        return pygame.PixelArray(self.design)

    def clear(self):
        self.design.fill(self.bg)

    def update(self):
        """Scales dummy design window to actual screen size and renders changes"""
        frame = pygame.transform.smoothscale(self.design, self.display.get_size())
        self.display.blit(frame, frame.get_rect())
        pygame.display.flip()

    def dimension_to_pixel(self, dimension):
        return dimension * self.square_size

    def square_to_pixel(self, square_coords):
        return list(map(self.dimension_to_pixel, square_coords[::-1]))

    def get_square_rect(self, square_coords) -> pygame.Rect:
        """Returns pygame 'Rect' object for specified row and column"""
        return pygame.Rect(
            *(self.square_to_pixel(square_coords) + [self.square_size] * 2)
        )

    def get_dimension_range(self, dimension):
        return range(*self.square_to_pixel((dimension + 1, dimension)))

    def get_square_range(self, square_coords):
        return product(*map(self.get_dimension_range, square_coords[::-1]))

    def get_square_colour(self, square_coords):
        return self.board_colours[sum(square_coords) % 2]

    def draw_button_at_coordinates(
        self,
        square_coords,
        colour,
        on_release,
        on_release_params=(),
    ):
        button = pygame_widgets.Button(
            self.design,
            *self.square_to_pixel(square_coords),
            height=self.square_size,
            width=self.square_size,
            inactiveColour=colour,
            onRelease=on_release,
            onReleaseParams=on_release_params,
        )
        button.draw()
        self.buttons.append(button)

    def draw_board_squares(self):
        """Draws the board on the screen"""
        # Loops through each row and column, drawing each square within the board
        for square_coords in self.chess.get_rows_and_columns():
            pygame.draw.rect(
                self.design,
                self.get_square_colour(square_coords),
                self.get_square_rect(square_coords),
            )
        self.update()

    def draw_piece(self, piece, square_coords):
        """Draws specified piece at centre of square at specified row and column"""
        piece_image = self.piece_images[piece]
        self.design.blit(
            piece_image,
            piece_image.get_rect(center=self.get_square_rect(square_coords).center),
        )

    def draw_pieces(self):
        """Draws the pieces at the correct positions on the screen"""
        # Initialises list holding piece buttons on current board
        self.buttons = []
        # Loops through each row and column, drawing squares and pieces
        for square_coords in self.chess.get_rows_and_columns():
            # Draws piece at square if it exists
            if piece := self.chess.get_piece_at_square(square_coords):
                self.draw_button_at_coordinates(
                    square_coords,
                    self.get_square_colour(square_coords),
                    self.show_moves,
                    (piece, square_coords),
                )
                self.draw_piece(piece, square_coords)
        self.update()

    def draw_board(self):
        """Displays the current state of the board"""
        self.clear()
        self.draw_board_squares()
        self.draw_pieces()

    def show_moves(self, peice, old_square_coords):
        for new_square_coords in self.chess.get_moves(peice, old_square_coords):
            self.draw_button_at_coordinates(
                square_coords=new_square_coords,
                colour=(0, 255, 0),
                on_release=self.move_piece,
                on_release_params=(
                    peice,
                    old_square_coords,
                    new_square_coords,
                ),
            )
            self.draw_piece(peice, old_square_coords)
        self.update()

    def move_piece(self, piece, old_square_coords, new_square_coords):
        self.chess.move(piece, old_square_coords, new_square_coords)
        self.draw_board()

    def __enter__(self):
        """Enables use of GUI in 'with' statement"""
        return self

    def mainloop(self, time_limit=float("inf")):
        """Keeps GUI running, handling events and rendering changes"""
        start_time = process_time()
        while self.running and (process_time() - start_time) < time_limit:
            for event in (events := pygame.event.get()):
                if event.type == pygame.QUIT:
                    self.__exit__()

            for button in self.buttons:
                button.listen(events)

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Enables use of GUI in 'with' statement, closing when with statement ends"""
        self.running = False


if __name__ == "__main__":
    chess_gui = ChessGUI()
    chess_gui.mainloop()
