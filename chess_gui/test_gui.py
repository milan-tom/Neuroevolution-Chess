import unittest
from collections import Counter

import pygame
import pygame_widgets

from chess_gui.GUI import ChessGUI
from core_chess.chess_logic import EMPTY_FEN
from core_chess.test_chess_logic import TEST_FENS


class ChessGUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Creates common GUI instance to be used by most tests"""
        cls.test_gui = ChessGUI()
        cls.square_size = cls.test_gui.square_size

    def test_square_fill(self):
        """Test if squares fill allocated space and handle borders correctly"""
        # Creates instance of GUI with empty board, preventing pieces from interfering
        with ChessGUI(fen=EMPTY_FEN) as test_gui:
            # Loops through beginnings of squares horizontally and vertically
            for square_coords in test_gui.chess.get_rows_and_columns():
                with self.subTest(square_coords=square_coords):
                    test_pxarray = test_gui.pxarray
                    # Checks all pixels in square have same colour as first pixel
                    square_x, square_y = test_gui.square_to_pixel(square_coords)
                    square_colour = test_pxarray[square_x][square_y]
                    self.assertTrue(
                        all(
                            test_pxarray[x][y] == square_colour
                            for x, y in test_gui.get_square_range(square_coords)
                        ),
                    )

    def test_square_colours(self):
        """Tests a sample of squares within the chess board to check square colours"""
        # Stores test square coordinates and expected colours in dictionary
        light, dark = self.test_gui.board_colours
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
                        self.test_gui.design.get_at(
                            self.test_gui.square_to_pixel(test_square)
                        )[:-1],
                        expected_colour,
                    )

    def test_piece_image_positioning_and_colours(self):
        # Creates several test GUI instances for different FENs
        for fen in TEST_FENS:
            # Draws pieces manually on grey background, preventing square colours
            # from interfering with tests
            with ChessGUI(fen=fen) as test_gui:
                test_pxarray = test_gui.pxarray
                # Loops through squares, performing the tests if there is a piece there
                for square_coords in test_gui.chess.get_rows_and_columns():
                    if piece := test_gui.chess.get_piece_at_square(square_coords):
                        with self.subTest(
                            fen=fen, square_coords=square_coords, piece=piece
                        ):
                            # Stores the mapped colour values for pixels in the square
                            square_pxs = [
                                test_pxarray[x][y]
                                for x, y in test_gui.get_square_range(square_coords)
                            ]
                            # Tests centring and colour of piece image in square
                            self.check_piece_image_centred(
                                test_gui, square_pxs, square_coords
                            )
                            self.check_piece_image_colours(test_gui, square_pxs, piece)

    def check_piece_image_centred(self, test_gui, square_pxs, square_coords):
        """Tests whether each piece is centred horizontally and vertically within its
        square"""
        # Filters coordinates of pixels different to square colour
        mapped_square_colour = test_gui.design.map_rgb(
            test_gui.get_square_colour(square_coords)
        )
        ranges_inside_image = [
            coord
            for coord, px_colour in zip(
                test_gui.get_square_range(square_coords), square_pxs
            )
            if px_colour != mapped_square_colour
        ]
        # Loops through x and y coordinates separately for square and filtered pixels
        for square_coord, range_inside_image in zip(
            test_gui.square_to_pixel(square_coords),
            zip(*ranges_inside_image),
        ):
            # Checks padding on either side differs by 0 or 1 (even/odd total padding)
            self.assertLessEqual(
                abs(
                    min(range_inside_image)
                    + max(range_inside_image)
                    - 2 * square_coord
                    - self.square_size
                ),
                1,
            )

    def check_piece_image_colours(self, test_gui, square_pxs, piece):
        """
        Tests whether squares contain the correct colour piece image by checking that
        piece colour is second most common (first is background) colour in image
        """
        image_colour = Counter(square_pxs).most_common(2)[1][0]
        correct_piece_colour = "white" if piece.isupper() else "black"
        self.assertEqual(
            test_gui.design.unmap_rgb(image_colour),
            pygame.Color(correct_piece_colour),
        )

    def find_move_buttons(self, test_gui):
        """Generator yielding all square coordinates shown as possible moves"""
        for square_coords in test_gui.chess.get_rows_and_columns():
            if (
                test_gui.design.get_at(self.test_gui.square_to_pixel(square_coords))
                == test_gui.move_button_colour
            ):
                yield square_coords

    def simulate_button_click(self, test_gui, square_coords):
        """Simulates a button press at the given coordinates"""
        test_coords = test_gui.get_square_rect(square_coords).center
        pygame.mouse.set_pos(*test_gui.design_coord_to_display(test_coords))
        test_gui.mainloop(1)
        pygame_widgets.mouse.Mouse._mouseState = pygame_widgets.mouse.MouseState.CLICK
        pygame_widgets.widget.WidgetHandler.main([])
        test_gui.mainloop(1)

    def test_showing_moves(self):
        """Tests that moves are shown correctly when pieces are clicked"""
        with ChessGUI() as test_gui:
            test_square_coords = (6, 5)

            # Tests single click shows moves
            self.simulate_button_click(test_gui, test_square_coords)
            self.assertTrue(any(self.find_move_buttons(test_gui)))

            # Tests clicking same piece twice clears moves
            self.simulate_button_click(test_gui, test_square_coords)
            self.assertFalse(
                any(self.find_move_buttons(test_gui)),
            )

    def test_quit_button(self):
        """Tests if the quit button actually closes the GUI"""
        # Adds quit event to event queue, checking if GUI stops upon detecting it
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        # Creates test-specific GUI instance as testing quitting may disrupt other tests
        with ChessGUI() as test_gui:
            test_gui.mainloop(1)
            self.assertFalse(test_gui.running)


if __name__ == "__main__":
    unittest.main()
