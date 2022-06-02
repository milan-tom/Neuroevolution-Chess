"""
A chess GUI, enabling visualisation of a chess states and making moves from the current
state
"""

import os
from bisect import bisect_right
from copy import deepcopy
from functools import partial
from itertools import cycle, product
from operator import mul, sub
from threading import Thread
from time import process_time
from typing import Any, Callable, Iterable, Optional
from warnings import warn

import pygame
import pygame.freetype
import pygame_widgets
from pygame_widgets.button import Button

from chess_logic.board import (
    PIECE_SIDE,
    PIECES,
    ROWS_AND_COLUMNS,
    SIDES,
    STARTING_FEN,
    Coord,
)
from chess_logic.core_chess import Chess, Move
from chess_logic.move_generation import PIECE_OF_SIDE

# Instructs OS to open window slightly offset so all of it fits on the screen
os.environ["SDL_VIDEO_WINDOW_POS"] = "0, 20"

# Imports all piece images and player icons
image_path = os.path.join(os.path.dirname(__file__), "images")


def load_image(name: str) -> pygame.surface.Surface:
    """Loads image from chess_gui/images directory given image filename"""
    image = pygame.image.load(os.path.join(image_path, f"{name}.png"))
    return image.subsurface(image.get_bounding_rect())


PIECE_IMAGES = {
    piece: load_image(f"{PIECE_SIDE[piece]}_{piece.upper()}") for piece in PIECES
}
RESTART_ICON = load_image("RESTART")

PLAYERS = ["HUMAN", "AI"]
try:
    from chess_ai.engine import best_engine_move
except FileNotFoundError:
    warn("Train the engine before opening the GUI in order to enable AI.")
    PLAYERS.pop()
PLAYER_ICONS = {
    player_type: {side: load_image(f"{side}_{player_type}") for side in SIDES}
    for player_type in PLAYERS
}

# Initialises pygame components and sets certain GUI parameters
pygame.init()
GAME_FONT: pygame.freetype.Font  # type: ignore[name-defined]
GAME_FONT = pygame.freetype.SysFont("Verdana", 0)
SCREEN_WIDTH, SCREEN_HEIGHT = DISPLAY_SIZE = 1536, 864
MOVE_COLOUR = 65, 187, 128


def rect_range(rect: pygame.Rect):
    """Returns all coordinates within specified pygame Rect object"""
    return product(*(range(rect[i], sum(rect[i::2])) for i in range(2)))


class Design(pygame.Surface):
    """Represents the design surface used by the GUI"""

    def __init__(self):
        """Initialises design surface and relevant attributes"""
        # Initialises parent class to creates dummy window for implementing design,
        # enabling scaling to any screen
        super().__init__(DISPLAY_SIZE)

        self.square_size = 108  # Size of square in pixels to fill dummy window's height
        # Stores colour codes for light and dark squares, respectively
        self.board_colours = (240, 217, 181), (187, 129, 65)

        # Creates subsurface for area of design window not covered by board
        board = self.square_size * 8, 0
        self.non_board_area = self.subsurface(*board, *map(sub, DISPLAY_SIZE, board))

    def dimension_to_pixel(self, dimension: int) -> int:
        """Scales row/column to pixel coordinate"""
        return dimension * self.square_size

    def square_to_pixel(self, square: Coord) -> Coord:
        """Returns pixel coordinate equivalent of square coordinate"""
        return tuple(
            map(self.dimension_to_pixel, square[::-1])  # type: ignore[return-value]
        )

    def get_square_rect(self, square: Coord) -> pygame.Rect:
        """Returns pygame 'Rect' object for specified row and column"""
        return pygame.Rect(
            *(list(self.square_to_pixel(square)) + [self.square_size] * 2)
        )

    def get_square_range(self, square: Coord) -> Iterable[Coord]:
        """Returns all coordinates within specified square"""
        return rect_range(self.get_square_rect(square))

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

    def __init__(
        self,
        display_size: Coord = (0, 0),
        fen: str = STARTING_FEN,
        display_only: bool = False,
        display_message: str = None,
    ) -> None:
        """Initialises chess board state and GUI components, and draws board"""
        pygame.display.set_caption("Chess GUI")

        self.design = Design()
        self.display = pygame.display.set_mode(display_size, pygame.RESIZABLE)
        self.selected_square: Optional[Coord] = None
        self.running = True
        self.searching = False
        self.best_engine_move: Optional[Move] = None

        # Initialises chess object (manages chess rules for GUI) and engine-related data
        self.chess = Chess(fen)
        self.current_players = dict(zip(SIDES, cycle(PLAYERS)))
        self.display_only = display_only
        self.display_message = display_message

        # Draws the board automatically
        self.draw_board()

    def update(self) -> None:
        """Scales dummy design window to actual screen size and renders changes"""
        pygame.transform.smoothscale(self.design, self.display.get_size(), self.display)

    def scale_coords(
        self,
        coords: Iterable[int | float],
        initial_resolution=DISPLAY_SIZE,
        final_resolution=None,
    ) -> list[int]:
        """Generates coordinates after design coordinates scaled to display"""
        if final_resolution is None:
            final_resolution = self.display.get_size()
        return [
            int(coord * final_size / initial_size)
            for coord, initial_size, final_size in zip(
                coords, cycle(initial_resolution), cycle(final_resolution)
            )
        ]

    def rect_scaled_img(
        self, img: pygame.surface.Surface, rect: pygame.rect.Rect
    ) -> pygame.surface.Surface:
        """Returns image after scaling it to fit inside Pygame 'Rect' object"""
        img_size = img.get_size()
        scale_args = img_size, [max(img_size)] * 2, map(lambda x: 0.7 * x, rect[2:])
        return pygame.transform.smoothscale(img, self.scale_coords(*scale_args))

    def scale_widget(
        self, widget: pygame_widgets.widget.WidgetBase, initial: Coord = DISPLAY_SIZE
    ) -> None:
        """Scales the x, y, width, and height attributes of widget to display size"""
        # pylint: disable=protected-access
        widget._x, widget._y, widget._width, widget._height = self.scale_coords(
            (widget._x, widget._y, widget._width, widget._height),
            initial,
        )

    def draw_button_at_rect(
        self,
        rect: pygame.rect.Rect,
        image: Optional[pygame.surface.Surface],
        func: Callable[[], Any],
        colour: Optional[str | tuple[int, int, int]] = "BLACK",
        **kwargs,
    ):
        """Draws button within specified Pygame 'Rect' object"""
        if image is not None:
            image = self.rect_scaled_img(image, rect)
        button = Button(
            self.design,
            *rect,
            inactiveColour=colour,
            image=image,
            onRelease=func,
            **kwargs,
        )
        button.draw()
        self.scale_widget(button)
        self.update()

    def draw_button_at_square(
        self, square: Coord, image: Optional[pygame.surface.Surface] = None, **kwargs
    ) -> None:
        """Draws button at given square"""
        if image is None:
            image = PIECE_IMAGES.get(self.chess.get_piece_at_square(square))
        if "colour" not in kwargs:
            kwargs["colour"] = (
                self.design.get_square_colour(square)
                if all(0 <= x <= 7 for x in square)
                else "WHITE"
            )
        self.draw_button_at_rect(self.design.get_square_rect(square), image, **kwargs)

    def show_text(
        self,
        text: str,
        rel_width: float = 0.8,
        rel_x: float = 0.5,
        rel_y: float = 0.5,
        destination_surface: Optional[pygame.surface.Surface] = None,
    ) -> pygame.Rect:
        """Displays text of the preconfigured font at the given location"""
        if destination_surface is None:
            destination_surface = self.design.non_board_area
        resolution = 0.1
        size = resolution * bisect_right(
            list(range(1, int(100 / resolution))),
            rel_width * destination_surface.get_rect().width,
            key=lambda x: GAME_FONT.get_rect(text, size=x * resolution).width,
        )
        text_rect = GAME_FONT.get_rect(text, size=size)
        text_rect.center = tuple(
            map(mul, (rel_x, rel_y), destination_surface.get_rect()[2:])
        )
        GAME_FONT.render_to(destination_surface, text_rect, text, "white", size=size)
        return text_rect

    def draw_pieces(self) -> None:
        """Draws the pieces at the correct positions on the screen"""
        # Loops through each row and column, drawing squares and pieces
        for square in ROWS_AND_COLUMNS:
            # Draws piece at square if it exists
            if piece := self.chess.get_piece_at_square(square):
                colour = (
                    "red"
                    if piece == PIECE_OF_SIDE[self.chess.next_side]["K"]
                    and self.chess.is_check
                    else self.design.get_square_colour(square)
                )
                self.draw_button_at_square(
                    square=square,
                    func=partial(self.show_moves, square),
                    colour=colour,
                )

    def draw_players(self) -> None:
        """Draws icons of current player types integrated into button to flip type"""
        for (side, player), shift_direction in zip(
            self.current_players.items(), [-1, 1]
        ):
            player_icon_rect = pygame.Rect(0, 0, 200, 200)
            player_icon_rect.center = self.design.non_board_area.get_rect().center
            player_icon_rect.centerx += (
                125 * shift_direction + self.design.non_board_area.get_offset()[0]
            )
            self.draw_button_at_rect(
                rect=player_icon_rect,
                image=PLAYER_ICONS[player][side],
                func=partial(self.switch_player, side),
                colour="white",
            )

    def draw_restart_button(self) -> None:
        """Draws button for restarting the game"""
        rect = RESTART_ICON.get_rect()
        rect.center = self.design.non_board_area.get_rect().center
        rect.centerx += self.design.non_board_area.get_offset()[0]
        rect.centery += 200
        self.draw_button_at_rect(
            rect=rect,
            image=RESTART_ICON,
            func=self.restart_game,
            radius=rect.width // 2,
        )

    def restart_game(self) -> None:
        """Restarts game and updates board"""
        self.chess = Chess()
        self.draw_board()

    def draw_board(self) -> None:
        """Displays the current state of the board"""
        self.design.fill("black")
        pygame_widgets.WidgetHandler.getWidgets().clear()
        self.design.draw_board_squares()
        self.draw_pieces()
        self.draw_restart_button()
        if self.chess.game_over:
            self.show_text(self.chess.game_over_message)
        elif self.display_only:
            self.show_text(self.display_message)
        else:
            self.draw_players()
            self.check_engine_move()

    def switch_player(self, side: str) -> None:
        """Switches type of player playing for side whose button clicked"""
        self.current_players[side] = PLAYERS[
            (PLAYERS.index(self.current_players[side]) + 1) % len(PLAYERS)
        ]
        self.draw_board()

    def draw_move_at_square(self, square: Coord, *args, **kwargs) -> None:
        """Draws button and circle for move to given square"""
        self.draw_button_at_square(square, *args, **kwargs)
        pygame.draw.circle(
            self.design, MOVE_COLOUR, self.design.get_square_rect(square).center, 15
        )

    def show_moves(self, old_square: Coord) -> None:
        """Display move buttons for clicked piece (double clicking clears moves)"""
        self.draw_board()

        if self.selected_square == old_square:
            self.selected_square = None
        else:
            self.selected_square = old_square
            legal_moves = self.chess.legal_moves_from_square(old_square)
            if legal_moves and legal_moves[0].context_flag == "PROMOTION":
                for promotion_set_i in range(0, len(legal_moves), 4):
                    promotion_moves = legal_moves[promotion_set_i : promotion_set_i + 4]
                    self.draw_move_at_square(
                        square=promotion_moves[0].new_square,
                        func=partial(self.show_promotion_moves, promotion_moves),
                    )
            else:
                for move in legal_moves:
                    self.draw_move_at_square(
                        square=move.new_square, func=partial(self.move_piece, move)
                    )
        self.update()

    def show_promotion_moves(self, promotion_moves: list[Move]):
        """Displays all choices for promoting pawn"""
        self.draw_board()
        for widget in pygame_widgets.WidgetHandler.getWidgets():
            widget.setOnRelease(lambda *args: None)
        self.show_text("Choose the promotion piece:", rel_y=0.075)
        for move_i, move in enumerate(promotion_moves):
            self.draw_button_at_square(
                square=(1, 9 + move_i),
                image=PIECE_IMAGES[move.context_data],
                func=partial(self.move_piece, move),
            )

    def move_piece(self, move: Move) -> None:
        """Moves piece from one square to another and updates GUI accordingly"""
        self.chess.move_piece(move)
        self.draw_board()

    def engine_move(self) -> None:
        """Gets the best engine move for the current side"""
        inital_side = self.chess.next_side
        self.searching = True
        best_move = best_engine_move(deepcopy(self.chess), 10000)
        self.searching = False
        # Verifies state hasn't changed since move request initiated
        if (
            self.chess.next_side == inital_side
            and self.current_players[inital_side] == "AI"
        ):
            self.best_engine_move = best_move

    def check_engine_move(self) -> None:
        """Checks if it is engine's turn to move, starting move search thread if so"""
        if (
            not (self.chess.game_over or self.searching)
            and self.current_players[self.chess.next_side] == "AI"
        ):
            Thread(target=self.engine_move).start()

    def mainloop(self, time_limit: int | float = float("inf")) -> None:
        """Keeps GUI running, managing events and buttons, and rendering changes"""
        time_limit /= 1000
        start_time = process_time()
        old_resolution = self.display.get_size()
        while self.running and (process_time() - start_time) < time_limit:
            for event in (events := pygame.event.get()):
                match event.type:
                    case pygame.VIDEORESIZE:
                        for widget in pygame_widgets.WidgetHandler.getWidgets():
                            self.scale_widget(widget, old_resolution)
                        old_resolution = self.display.get_size()
                        self.draw_board()
                    case pygame.QUIT:
                        self.running = False

            pygame_widgets.update(events)
            pygame.display.update()

            if self.best_engine_move is not None:
                self.move_piece(self.best_engine_move)
                self.best_engine_move = None


if __name__ == "__main__":
    chess_gui = ChessGUI()
    chess_gui.mainloop()
