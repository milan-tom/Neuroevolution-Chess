"""Contains all unit tests for GUI"""

import unittest
from collections import Counter
from itertools import chain, cycle, product
from typing import Iterable

import pygame
import pygame_widgets

from chess_gui.gui import ChessGUI
from core_chess.chess_logic import Coord, EMPTY_FEN, ROWS_AND_COLUMNS
from core_chess.test_chess_logic import TEST_FENS

TEST_DISPLAY_SIZES = list(product(range(500, 1500, 200), repeat=2))


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
            == test_gui.move_button_colour
        ):
            yield square_coords


class ChessGUITest(unittest.TestCase):
    """TestCase subclass for GUI unit tests and relevant helper functions"""

    def test_square_fill(self) -> None:
        """Test if squares fill allocated space and handle borders correctly"""
        # Creates instance of GUI with empty board, preventing pieces from interfering
        with ChessGUI(fen=EMPTY_FEN) as test_gui:
            # Loops through beginnings of squares horizontally and vertically
            for square_coords in ROWS_AND_COLUMNS:
                with self.subTest(square_coords=square_coords):
                    test_pxarray = pygame.PixelArray(test_gui.design)
                    # Checks all pixels in square have same colour as first pixel
                    square_x, square_y = test_gui.design.square_to_pixel(square_coords)
                    square_colour = test_pxarray[square_x][square_y]
                    self.assertTrue(
                        all(
                            test_pxarray[x][y] == square_colour
                            for x, y in test_gui.get_square_range(square_coords)
                        ),
                    )

    def test_square_colours(self) -> None:
        """Tests a sample of squares within the chess board to check square colours"""
        with ChessGUI() as test_gui:
            # Stores test square coordinates and expected colours in dictionary
            light, dark = test_gui.design.board_colours
            expected_colours_for_squares = {
                light: (
                    (0, 0),  # Top-left square
                    (1, 1),  # Square diagonal to top-left
                    (0, 2),  # Light square below top-left
                    (2, 0),  # Light square to right of top-left
                    (7, 7),  # Bottom-right square
                ),
                dark: (
                    (0, 7),  # Bottom-left square
                    (7, 0),  # Top-right square
                ),
            }

            # Checks all test squares match expected colour
            for expected_colour, test_squares in expected_colours_for_squares.items():
                for test_square in test_squares:
                    with self.subTest(square_coords=test_square):
                        self.assertEqual(
                            test_gui.design.get_at(
                                test_gui.design.square_to_pixel(test_square)
                            )[:-1],
                            expected_colour,
                        )

    def test_piece_image_positioning_and_colours(self) -> None:
        """Tests that all pieces are centred and have the correct colour"""
        # Creates several test GUI instances for different FENs
        for display_size, fen in chain(
            zip(cycle(TEST_DISPLAY_SIZES[:1]), TEST_FENS),
            zip(TEST_DISPLAY_SIZES, cycle(TEST_FENS[:1])),
        ):
            with ChessGUI(display_size=display_size, fen=fen) as test_gui:
                test_pxarray = pygame.PixelArray(test_gui.display)
                # Loops through squares, performing the tests if there is a piece there
                for square_coords in ROWS_AND_COLUMNS:
                    if piece := test_gui.chess.get_piece_at_square(square_coords):
                        with self.subTest(
                            display_size=display_size,
                            fen=fen,
                            square_coords=square_coords,
                            piece=piece,
                        ):
                            # Stores the mapped colour values for pixels in the square
                            square_pxs = [
                                test_pxarray[x][y]
                                for x, y in test_gui.get_square_range(
                                    square_coords, scaled=True
                                )
                            ]
                            # Tests centring and colour of piece image in square
                            self.check_piece_image_centred(
                                test_gui, square_pxs, square_coords
                            )
                            self.check_piece_image_colours(test_gui, square_pxs, piece)

    def check_piece_image_centred(
        self, test_gui: ChessGUI, square_pxs: list[int], squares: Coord
    ) -> None:
        """Tests whether each piece is centred horizontally and vertically within its
        square"""
        # Filters coordinates of pixels different to square colourss
        mapped_square_colour = test_gui.display.map_rgb(
            test_gui.design.get_square_colour(squares)
        )
        ranges_inside_image = [
            coord
            for coord, px_colour in zip(
                test_gui.get_square_range(squares, scaled=True), square_pxs
            )
            if px_colour != mapped_square_colour
        ]
        # Loops through x and y coordinates separately for square and filtered pixels
        for square_coord, range_inside_image, scaled_square_size in zip(
            test_gui.scale_coords(test_gui.design.square_to_pixel(squares)),
            zip(*ranges_inside_image),
            test_gui.scale_coords([test_gui.design.square_size] * 2),
        ):
            # Checks paddings either side differ by at most 2 (allows rounding errors)
            self.assertLessEqual(
                abs(
                    min(range_inside_image)
                    + max(range_inside_image)
                    - 2 * square_coord
                    - scaled_square_size
                ),
                2,
            )

    def check_piece_image_colours(
        self, test_gui: ChessGUI, square_pxs: list[int], piece: str
    ) -> None:
        """
        Tests whether squares contain the correct colour piece image by checking that
        piece colour is second most common (first is background) colour in image
        """
        image_colour = Counter(square_pxs).most_common(2)[1][0]
        correct_piece_colour = "white" if piece.isupper() else "black"
        self.assertEqual(
            test_gui.display.unmap_rgb(image_colour),
            pygame.Color(correct_piece_colour),
            (
                piece,
                [
                    (test_gui.display.unmap_rgb(x), num)
                    for x, num in Counter(square_pxs).most_common(10)
                ],
            ),
        )

    def test_showing_moves(self) -> None:
        """Tests that moves are shown correctly when pieces are clicked"""
        with ChessGUI() as test_gui:
            test_square_coords = (6, 5)

            # Tests single click shows moves
            simulate_button_click(test_gui, test_square_coords)
            self.assertTrue(any(find_move_buttons(test_gui)))

            # Tests clicking same piece twice clears moves
            simulate_button_click(test_gui, test_square_coords)
            self.assertFalse(
                any(find_move_buttons(test_gui)),
            )

    def test_quit_button(self) -> None:
        """Tests if the quit button actually closes the GUI"""
        # Adds quit event to event queue, checking if GUI stops upon detecting it
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        # Creates test-specific GUI instance as testing quitting may disrupt other tests
        with ChessGUI() as test_gui:
            test_gui.mainloop(1)
            self.assertFalse(test_gui.running)


if __name__ == "__main__":
    unittest.main()
