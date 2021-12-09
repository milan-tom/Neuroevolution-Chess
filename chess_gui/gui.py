"""
A chess GUI, enabling visualisation of a chess states and making moves from the current
state
"""

from __future__ import annotations
from functools import partial
from itertools import cycle, product
from time import process_time
from types import TracebackType
from typing import Callable, Iterable, Optional, Union
import os

import pygame
import pygame.freetype
import pygame_widgets
from pygame_widgets.button import Button

from chess_logic.board import Coord, PIECE_SIDE, PIECES, ROWS_AND_COLUMNS, STARTING_FEN
from chess_logic.core_chess import Chess, Move

# Instructs OS to open window slightly offset so all of it fits on the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0, 20"

# Imports all piece images (source:
# https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
image_path = os.path.join(os.path.dirname(__file__), "images", "{}_{}.png")
PIECE_IMAGES = {
    piece: (
        piece_image := pygame.image.load(
            image_path.format(PIECE_SIDE[piece], piece.upper())
        )
    ).subsurface(piece_image.get_bounding_rect())
    for piece in PIECES
}

# Initialises pygame components and sets certain GUI parameters
pygame.init()
GAME_FONT = "Verdana"


class Design(pygame.Surface):
    """Represents the design surface used by the GUI"""

    def __init__(self):
        """Initialises design surface and relevant attributes"""
        # Initialises parent class to creates dummy window for implementing design,
        # enabling scaling to any screen
        super().__init__((1536, 864))

        self.square_size = 108  # Size of square in pixels to fill dummy window's height
        # Stores colour codes for light and dark squares, respectively
        self.board_colours = (240, 217, 181), (187, 129, 65)

    def dimension_to_pixel(self, dimension: int) -> int:
        """Scales row/column to pixel coordinate"""
        return dimension * self.square_size

    def square_to_pixel(self, square: Coord) -> Coord:
        """Returns (scaled) pixel coordinate equivalent of square coordinate"""
        return tuple(map(self.dimension_to_pixel, square[::-1]))

    def get_square_rect(self, square: Coord) -> pygame.Rect:
        """Returns pygame 'Rect' object for specified row and column"""
        return pygame.Rect(
            *(list(self.square_to_pixel(square)) + [self.square_size] * 2)
        )

    def get_square_colour(self, square: Coord) -> tuple[int, int, int]:
        """Returns colour on board of given square"""
        return self.board_colours[sum(square) % 2]

    def draw_board_squares(self) -> None:
        """Draws the board on the screen"""
        # Loops through each row and column, drawing each square within the board
        for square_coords in ROWS_AND_COLUMNS:
            pygame.draw.rect(
                self,
                self.get_square_colour(square_coords),
                self.get_square_rect(square_coords),
            )


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
        """Initialises chess board state and GUI components, and draws board"""
        pygame.display.set_caption("Chess GUI")

        self.design = Design()
        self.display = pygame.display.set_mode(display_size, pygame.RESIZABLE)
        self.selected_square: Optional[Coord] = None
        self.running = True
        self.default_button_colour = (0, 255, 0)

        # Initialises chess object to manage chess rules for GUI
        self.chess = Chess(fen)

        # Scales piece images to size of GUI
        self.piece_images = {
            piece: pygame.transform.scale(
                piece_image,
                self.scale_coords(piece_image.get_size()),
            )
            for piece, piece_image in PIECE_IMAGES.items()
        }

        # Draws the board automatically
        self.draw_board()

    def update(self) -> None:
        """Scales dummy design window to actual screen size and renders changes"""
        pygame.transform.smoothscale(self.design, self.display.get_size(), self.display)
        pygame.display.flip()

    def scale_coords(self, coords: Iterable[int]) -> list[int]:
        """Generates coordinates after design coordinates scaled to display"""
        return [
            coord * display_size // design_size
            for coord, design_size, display_size in zip(
                coords, cycle(self.design.get_size()), cycle(self.display.get_size())
            )
        ]

    def get_square_range(self, square: Coord, scaled: bool = False) -> Iterable[Coord]:
        """Returns all (scaled) coordinates within specified square"""
        square_details = self.design.get_square_rect(square)
        if scaled:
            square_details = self.scale_coords(square_details)
        square_x, square_y, x_square_size, y_square_size = square_details
        return product(
            range(square_x, square_x + x_square_size),
            range(square_y, square_y + y_square_size),
        )

    def draw_button_at_square(
        self,
        square: Coord,
        func: Callable,
        colour: tuple[int, int, int] = None,
        image: Optional[pygame.Surface] = None,
    ) -> None:
        """Draws button at given square"""
        if colour is None:
            colour = self.default_button_colour
        if image is None:
            image = self.piece_images.get(self.chess.get_piece_at_square(square))
        Button(
            self.display,
            *self.scale_coords(self.design.get_square_rect(square)),
            inactiveColour=colour,
            image=image,
            onRelease=func,
        ).draw()

    def show_text(self, text: str, size: int, location: Coord) -> None:
        """Displays text of the prconfigured font at the given location"""
        pygame.freetype.SysFont(GAME_FONT, size).render_to(
            self.design, location, text, "white"
        )
        self.update()

    def draw_pieces(self) -> None:
        """Draws the pieces at the correct positions on the screen"""
        # Loops through each row and column, drawing squares and pieces
        for square in ROWS_AND_COLUMNS:
            # Draws piece at square if it exists
            if self.chess.get_piece_at_square(square):
                self.draw_button_at_square(
                    square=square,
                    func=partial(self.show_moves, square),
                    colour=self.design.get_square_colour(square),
                )
        pygame.display.flip()

    def draw_board(self) -> None:
        """Displays the current state of the board"""
        self.design.fill("black")
        pygame_widgets.WidgetHandler.getWidgets().clear()
        self.design.draw_board_squares()
        self.update()
        self.draw_pieces()

    def show_moves(self, old_square: Coord) -> None:
        """Display move buttons for clicked piece (double clicking clears moves)"""
        if self.selected_square is not None:
            self.draw_board()

        if self.selected_square == old_square:
            self.selected_square = None
        else:
            self.draw_pieces()
            self.selected_square = old_square

            legal_moves = self.chess.legal_moves_from_square(old_square)
            if legal_moves and legal_moves[0].context_flag == "PROMOTION":
                for promotion_set_i in range(0, len(legal_moves), 4):
                    promotion_moves = legal_moves[promotion_set_i : promotion_set_i + 4]
                    self.draw_button_at_square(
                        square=promotion_moves[0].new_square,
                        func=partial(self.show_promotion_moves, promotion_moves),
                    )
            else:
                for move in legal_moves:
                    self.draw_button_at_square(
                        square=move.new_square, func=partial(self.move_piece, move)
                    )

    def show_promotion_moves(self, promotion_moves: list[Move]):
        """Displays all choices for promoting pawn"""
        for widget in pygame_widgets.WidgetHandler.getWidgets():
            widget.setOnRelease(lambda *args: None)
        self.show_text("Choose the promotion piece:", 30, (970, 50))
        for move_i, move in enumerate(promotion_moves):
            self.draw_button_at_square(
                square=(1, 9 + move_i),
                func=partial(self.move_piece, move),
                image=self.piece_images[move.context_data],
            )

    def move_piece(self, move: Move) -> None:
        """Moves piece from one square to another and updates GUI accordingly"""
        self.chess.move_piece(move)
        self.draw_board()

    def __enter__(self) -> ChessGUI:
        """Enables use of GUI in 'with' statement"""
        return self

    def mainloop(self, time_limit: Union[int, float] = float("inf")) -> None:
        """Keeps GUI running, managing events and buttons, and rendering changes"""
        time_limit /= 1000
        start_time = process_time()
        while self.running and (process_time() - start_time) < time_limit:
            # pylint: disable=superfluous-parens
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
