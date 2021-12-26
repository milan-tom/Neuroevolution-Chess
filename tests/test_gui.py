"""Contains all unit tests for GUI"""

from collections import Counter
from itertools import chain, cycle, product
from typing import Iterable

import pygame
import pygame_widgets
import pytest

from chess_gui.gui import ChessGUI
from chess_logic.board import Coord, ROWS_AND_COLUMNS
from tests import TEST_FENS

TEST_DISPLAY_SIZES = list(product(range(500, 1500, 200), repeat=2))


@pytest.mark.parametrize(
    "gui",
    chain(
        zip(cycle(TEST_DISPLAY_SIZES[:1]), TEST_FENS),
        zip(TEST_DISPLAY_SIZES, cycle(TEST_FENS[:1])),
    ),
    indirect=True,
)
def test_piece_image_positioning_and_colours(gui: ChessGUI) -> None:
    """Tests that all pieces are centred and have the correct colour"""
    # Creates several test GUI instances for different FENs
    test_pxarray = pygame.PixelArray(gui.display)
    # Loops through squares, performing the tests if there is a piece there
    for square_coords in ROWS_AND_COLUMNS:
        if piece := gui.chess.get_piece_at_square(square_coords):
            # Stores the mapped colour values for pixels in the square
            square_pxs = [
                test_pxarray[x][y] for x, y in gui.get_square_range(square_coords)
            ]
            # Tests centring and colour of piece image in square
            check_piece_image_centred(gui, square_pxs, square_coords)
            check_piece_image_colours(gui, square_pxs, piece)


def check_piece_image_centred(
    test_gui: ChessGUI, square_pxs: list[int], squares: Coord
) -> None:
    """Tests whether each piece is centred horizontally and vertically within its
    square"""
    # Filters coordinates of pixels different to square colours
    mapped_square_colour = test_gui.display.map_rgb(
        test_gui.design.get_square_colour(squares)
    )
    ranges_inside_image = [
        coord
        for coord, px_colour in zip(test_gui.get_square_range(squares), square_pxs)
        if px_colour != mapped_square_colour
    ]
    # Loops through x and y coordinates separately for square and filtered pixels
    for square_coord, image_range, square_size in zip(
        test_gui.scale_coords(test_gui.design.square_to_pixel(squares)),
        zip(*ranges_inside_image),
        test_gui.scale_coords([test_gui.design.square_size] * 2),
    ):
        # Checks paddings either side differ by at most 2 (allows rounding errors)
        assert (
            abs(min(image_range) + max(image_range) - 2 * square_coord - square_size)
            <= 2
        )


def check_piece_image_colours(
    test_gui: ChessGUI, square_pxs: list[int], piece: str
) -> None:
    """
    Tests whether squares contain the correct colour piece image by checking that
    piece colour is second most common (first is background) colour in image
    """
    image_colour = Counter(square_pxs).most_common(2)[1][0]
    expected_colour = "white" if piece.isupper() else "black"
    assert test_gui.display.unmap_rgb(image_colour) == pygame.Color(expected_colour)


def simulate_button_click(test_gui: ChessGUI, square_coords: Coord) -> None:
    """Simulates a button press at the given coordinates"""
    # pylint: disable=protected-access
    test_coords = test_gui.design.get_square_rect(square_coords).center
    pygame.event.set_grab(True)
    test_gui.mainloop(100)
    pygame.mouse.set_pos(*test_gui.scale_coords(test_coords))
    pygame.event.set_grab(False)
    test_gui.mainloop(100)
    pygame_widgets.mouse.Mouse._mouseState = pygame_widgets.mouse.MouseState.CLICK
    pygame_widgets.widget.WidgetHandler.main([])
    test_gui.mainloop(100)


def find_move_buttons(test_gui: ChessGUI) -> Iterable[Coord]:
    """Generator yielding all square coordinates shown as possible moves"""
    for square_coords in ROWS_AND_COLUMNS:
        if (
            test_gui.display.get_at(
                test_gui.scale_coords(test_gui.design.square_to_pixel(square_coords))
            )
            == test_gui.default_button_colour
        ):
            yield square_coords


def test_showing_moves(gui: ChessGUI) -> None:
    """Tests that moves are shown correctly when pieces are clicked"""
    test_square_coords = (6, 5)
    gui.chess.update_board_state()

    # Tests single click shows moves
    simulate_button_click(gui, test_square_coords)
    assert any(find_move_buttons(gui))

    # Tests clicking same piece twice clears moves
    simulate_button_click(gui, test_square_coords)
    assert not any(find_move_buttons(gui))


def test_quit_button(gui) -> None:
    """Tests if the quit button actually closes the GUI"""
    # Adds quit event to event queue, checking if GUI stops upon detecting it
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    gui.mainloop(1)
    assert not gui.running
