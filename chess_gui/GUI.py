from __future__ import annotations
from itertools import cycle, product
from time import process_time
from types import TracebackType
from typing import Callable, Iterable, Union
import os

import pygame
import pygame_widgets
from pygame_widgets.button import Button

from core_chess.chess_logic import Chess, Coord, STARTING_FEN

# Instructs OS to open window slightly offset so all of it fits on the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0, 20"


class ChessGUI:
    """
    Enables the visualization of any board state via a GUI:
        - Displays moves possible for selected piece
        - Allows human input for moves from current position
    Coordinate conventions:
        - Pixel coordinates -> Increases moving right and downwards from top-left (0, 0)
        - Dimensional coordinates -> Uniquely identifies square via row and column in
          8x8 chess board (0-based increasing from top to bottom and left to right)
    """

    def __init__(self, display_size: Coord = (0, 0), fen=STARTING_FEN) -> None:
        """Initialises chess board state, pygame components, and draws board"""
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
        image_path = os.path.join(os.path.dirname(__file__), "images", "{}_{}.png")
        self.piece_images = {}
        for piece in self.chess.pieces:
            piece_image = pygame.image.load(
                image_path.format(self.chess.get_piece_side(piece), piece.upper())
            )
            cropped_image = piece_image.subsurface(piece_image.get_bounding_rect())
            self.piece_images[piece] = pygame.transform.scale(
                cropped_image,
                self.scale_coords(cropped_image.get_size()),
            )

        # Draws the board automatically
        self.draw_board()

    def clear(self) -> None:
        """Clears display (fills with black)"""
        self.design.fill("black")
        pygame_widgets.widget.WidgetHandler._widgets = []

    def update(self) -> None:
        """Scales dummy design window to actual screen size and renders changes"""
        pygame.transform.smoothscale(self.design, self.display.get_size(), self.display)
        pygame.display.flip()

    def scale_coords(self, coords: Iterable[Coord]) -> list[Coord]:
        """Generates coordinates after design coordinates scaled to display"""
        return [
            coord * display_size // design_size
            for coord, design_size, display_size in zip(
                coords, cycle(self.design.get_size()), cycle(self.display.get_size())
            )
        ]

    def dimension_to_pixel(self, dimension: int) -> int:
        """Scales row/column to pixel coordinate"""
        return dimension * self.square_size

    def square_to_pixel(self, square: Coord, scaled: bool = False) -> Coord:
        """Returns (scaled) pixel coordinate equivalent of square coordinate"""
        square_pixel_coords = list(map(self.dimension_to_pixel, square[::-1]))
        return self.scale_coords(square_pixel_coords) if scaled else square_pixel_coords

    def get_square_rect(self, square_coords) -> pygame.Rect:
        """Returns pygame 'Rect' object for specified row and column"""
        return pygame.Rect(
            *(self.square_to_pixel(square_coords) + [self.square_size] * 2)
        )

    def get_square_range(self, square: Coord, scaled: bool = False) -> Iterable[Coord]:
        """Returns all (scaled) coordinates within specified square"""
        square_details = self.get_square_rect(square)
        if scaled:
            square_details = self.scale_coords(square_details)
        square_x, square_y, x_square_size, y_square_size = square_details
        return product(
            range(square_x, square_x + x_square_size),
            range(square_y, square_y + y_square_size),
        )

    def get_square_colour(self, square: Coord) -> tuple[int, int, int]:
        """Returns colour on board of given square"""
        return self.board_colours[sum(square) % 2]

    def draw_button_at_square(
        self,
        square: Coord,
        colour: str,
        command_function: Callable,
        parameters: Union[tuple, list],
    ) -> None:
        """Draws button at given square"""
        button = Button(
            self.display,
            *self.scale_coords(self.get_square_rect(square)),
            inactiveColour=colour,
            image=self.piece_images.get(self.chess.get_piece_at_square(square)),
            onRelease=command_function,
            onReleaseParams=parameters,
        )
        button.draw()

    def draw_board_squares(self) -> None:
        """Draws the board on the screen"""
        # Loops through each row and column, drawing each square within the board
        for square_coords in self.chess.get_rows_and_columns():
            pygame.draw.rect(
                self.design,
                self.get_square_colour(square_coords),
                self.get_square_rect(square_coords),
            )
        self.update()

    def draw_pieces(self) -> None:
        """Draws the pieces at the correct positions on the screen"""
        # Loops through each row and column, drawing squares and pieces
        for square_coords in self.chess.get_rows_and_columns():
            # Draws piece at square if it exists
            if piece := self.chess.get_piece_at_square(square_coords):
                self.draw_button_at_square(
                    square_coords,
                    self.get_square_colour(square_coords),
                    self.show_moves,
                    (piece, square_coords),
                )
        pygame.display.flip()

    def draw_board(self) -> None:
        """Displays the current state of the board"""
        self.clear()
        self.draw_board_squares()
        self.draw_pieces()

    def show_moves(self, piece: str, old_square: Coord) -> None:
        """Display move buttons for clicked piece (double clicking clears moves)"""
        if self.selected_square is not None:
            self.draw_board()

        if self.selected_square == old_square:
            self.selected_square = None
        else:
            self.draw_pieces()
            self.selected_square = old_square
            for new_square_coords in self.chess.legal_moves_from_square(
                piece, old_square
            ):
                self.draw_button_at_square(
                    square=new_square_coords,
                    colour=self.move_button_colour,
                    command_function=self.move_piece,
                    parameters=(old_square, new_square_coords),
                )
            self.update()

    def move_piece(self, old_square: Coord, new_square: Coord) -> None:
        """Moves piece from one square to another and updates GUI accordingly"""
        self.chess.move(old_square, new_square)
        self.draw_board()

    def __enter__(self) -> ChessGUI:
        """Enables use of GUI in 'with' statement"""
        return self

    def mainloop(self, time_limit: int = float("inf")) -> None:
        """Keeps GUI running, managing events and buttons, and rendering changes"""
        time_limit /= 1000
        start_time = process_time()
        while self.running and (process_time() - start_time) < time_limit:
            for event in (events := pygame.event.get()):
                if event.type == pygame.QUIT:
                    self.__exit__()

            pygame_widgets.update(events)
            pygame.display.update()

    def __exit__(
        self,
        exc_type: BaseException = None,
        exc_val: BaseException = None,
        exc_tb: TracebackType = None,
    ) -> None:
        """Enables use of GUI in 'with' statement, closing when with statement ends"""
        self.running = False


if __name__ == "__main__":
    chess_gui = ChessGUI()
    chess_gui.mainloop()
