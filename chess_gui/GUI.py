import os
from itertools import cycle, product
from time import process_time

import pygame
import pygame_widgets
from pygame_widgets.button import Button

from core_chess.chess_logic import Chess, STARTING_FEN

# Instructs OS to open window slightly offset so all of it fits on the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0, 20"


class ChessGUI:
    """Displays a GUI for a given chess state"""

    def __init__(self, display_size=(0, 0), fen=STARTING_FEN):
        """Initialises pygame components and draws board"""
        pygame.init()
        pygame.display.set_caption("Chess GUI")
        self.display = pygame.display.set_mode(display_size, pygame.RESIZABLE)
        self.selected_square = None
        self.running = True

        # Initialises chess object to manage chess rules for GUI
        self.chess = Chess(fen)

        # Stores colour codes for light and dark squares, respectively, and move button
        self.board_colours = (240, 217, 181), (187, 129, 65)
        self.move_button_colour = (0, 255, 0)

        # Creates dummy window for implementing design, enabling scaling to any screen
        self.design = pygame.Surface((1536, 864))
        self.square_size = 108  # Size of square in pixels to fill dummy window's height

        # Imports all piece images (source:
        # https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
        image_path = os.path.join(os.path.dirname(__file__), "images", "{}{}.png")
        self.piece_images = {}
        for piece in self.chess.pieces:
            piece_image = pygame.image.load(
                image_path.format(self.chess.players[piece.islower()], piece.upper())
            )
            cropped_image = piece_image.subsurface(piece_image.get_bounding_rect())
            self.piece_images[piece] = pygame.transform.scale(
                cropped_image,
                self.scale_coords(cropped_image.get_size()),
            )

        # Draws the board automatically
        self.draw_board()

    def clear(self):
        self.design.fill("black")
        pygame_widgets.widget.WidgetHandler._widgets = []

    def update(self):
        """Scales dummy design window to actual screen size and renders changes"""
        pygame.transform.smoothscale(self.design, self.display.get_size(), self.display)
        pygame.display.flip()

    def scale_coords(self, coords):
        return [
            coord * display_size // design_size
            for coord, design_size, display_size in zip(
                coords, cycle(self.design.get_size()), cycle(self.display.get_size())
            )
        ]

    def dimension_to_pixel(self, dimension):
        return dimension * self.square_size

    def square_to_pixel(self, square_coords, scaled=False):
        square_pixel_coords = list(map(self.dimension_to_pixel, square_coords[::-1]))
        return self.scale_coords(square_pixel_coords) if scaled else square_pixel_coords

    def get_square_rect(self, square_coords) -> pygame.Rect:
        """Returns pygame 'Rect' object for specified row and column"""
        return pygame.Rect(
            *(self.square_to_pixel(square_coords) + [self.square_size] * 2)
        )

    def get_dimension_range(self, dimension):
        return range(*self.square_to_pixel((dimension + 1, dimension)))

    def get_square_range(self, square_coords, scaled=False):
        square_details = self.get_square_rect(square_coords)
        if scaled:
            square_details = self.scale_coords(square_details)
        square_x, square_y, x_square_size, y_square_size = square_details
        return product(
            range(square_x, square_x + x_square_size),
            range(square_y, square_y + y_square_size),
        )

    def get_square_colour(self, square_coords):
        return self.board_colours[sum(square_coords) % 2]

    def draw_button_at_coordinates(
        self,
        square_coords,
        colour,
        on_release,
        on_release_params=(),
        image=None,
    ):
        button = Button(
            self.display,
            *self.scale_coords(self.get_square_rect(square_coords)),
            inactiveColour=colour,
            image=image,
            onRelease=on_release,
            onReleaseParams=on_release_params,
        )
        button.draw()

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

    def draw_pieces(self):
        """Draws the pieces at the correct positions on the screen"""
        # Loops through each row and column, drawing squares and pieces
        for square_coords in self.chess.get_rows_and_columns():
            # Draws piece at square if it exists
            if piece := self.chess.get_piece_at_square(square_coords):
                self.draw_button_at_coordinates(
                    square_coords,
                    self.get_square_colour(square_coords),
                    self.show_moves,
                    (piece, square_coords),
                    self.piece_images[piece],
                )
        pygame.display.flip()

    def draw_board(self):
        """Displays the current state of the board"""
        self.clear()
        self.draw_board_squares()
        self.draw_pieces()

    def show_moves(self, piece, old_square_coords):
        if self.selected_square is not None:
            self.draw_board()

        if self.selected_square == old_square_coords:
            self.selected_square = None
        else:
            self.draw_pieces()
            self.selected_square = old_square_coords
            for new_square_coords in self.chess.get_moves(piece, old_square_coords):
                self.draw_button_at_coordinates(
                    square_coords=new_square_coords,
                    colour=self.move_button_colour,
                    on_release=self.move_piece,
                    on_release_params=(
                        old_square_coords,
                        new_square_coords,
                    ),
                )
            self.update()

    def move_piece(self, old_square_coords, new_square_coords):
        self.chess.move(old_square_coords, new_square_coords)
        self.draw_board()

    def __enter__(self):
        """Enables use of GUI in 'with' statement"""
        return self

    def mainloop(self, time_limit=float("inf")):
        """Keeps GUI running, handling events and rendering changes"""
        time_limit /= 1000
        start_time = process_time()
        while self.running and (process_time() - start_time) < time_limit:
            for event in (events := pygame.event.get()):
                if event.type == pygame.QUIT:
                    self.__exit__()

            pygame_widgets.update(events)
            pygame.display.update()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Enables use of GUI in 'with' statement, closing when with statement ends"""
        self.running = False


if __name__ == "__main__":
    chess_gui = ChessGUI()
    chess_gui.mainloop()
