import unittest
from itertools import product
from collections import Counter

import pygame.event

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
            for square_coordinates in product(range(8), repeat=2):
                with self.subTest(square_coordinates=square_coordinates):
                    # Checks all pixels in square have same colour as first pixel
                    x, y = map(
                        lambda coord: coord * self.square_size, square_coordinates
                    )
                    square_colour = test_gui.design.get_at((x, y))
                    self.assertTrue(
                        all(
                            test_gui.design.get_at((x + x_move, y + y_move))
                            == square_colour
                            for x_move, y_move in product(
                                range(self.square_size), repeat=2
                            )
                        ),
                    )

    def test_square_colours(self):
        """Tests a sample of squares within the chess board to check square colours"""
        # Stores test square coordinates and expected colours in dictionary
        light, dark = self.test_gui.board_colours
        expected_colours_for_squares = {
            light: (
                (0, 0),  # Top-left square
                (self.square_size, self.square_size),  # Square diagonal to top-left
                (0, self.square_size * 2),  # Light square below top-left
                (self.square_size * 2, 0),  # Light square to right of top-left
                (self.square_size * 7, self.square_size * 7),  # Bottom-right square
            ),
            dark: (
                (0, self.square_size * 7),  # Bottom-left square
                (self.square_size * 7, 0),  # Top-right square
            ),
        }

        # Checks all test squares match expected colour
        for expected_colour, test_squares in expected_colours_for_squares.items():
            for test_square in test_squares:
                with self.subTest(square_coordinates=test_square):
                    self.assertEqual(
                        self.test_gui.design.get_at(test_square)[:-1],
                        expected_colour,
                    )

    def test_piece_image_positioning_and_colours(self):
        # Creates several test GUI instances for different FENs
        for fen in TEST_FENS:
            # Draws pieces manually on grey background, preventing square colours
            # from interfering with tests
            with ChessGUI(fen=fen, draw_board=False, bg="gray") as test_gui:
                test_gui.draw_pieces()
                # Stores 'PixelArray' screen wrapper for quicker pixel colour access
                test_pxarray = test_gui.pxarray
                # Loops through squares, performing the test if there is a piece there
                for square_coordinates in test_gui.chess.get_rows_and_columns():
                    if piece := test_gui.chess.get_piece_at_square(*square_coordinates):
                        with self.subTest(
                            fen=fen, square_coordinates=square_coordinates, piece=piece
                        ):
                            square_pxs = [
                                test_pxarray[x][y]
                                for x, y in test_gui.get_square_range(
                                    *square_coordinates
                                )
                            ]
                            self.check_piece_image_positioning(
                                test_gui, square_pxs, square_coordinates
                            )
                            self.check_piece_image_colours(test_gui, square_pxs, piece)

    def check_piece_image_positioning(self, test_gui, square_pxs, square_coordinates):
        """Tests whether each piece is centered horizontally and veritcally within its
        square"""
        # Filters coordinates of pixels different to background colour
        ranges_inside_image = [
            coord
            for coord, px_colour in zip(
                test_gui.get_square_range(*square_coordinates), square_pxs
            )
            if px_colour != test_gui.mapped_bg
        ]
        # Loops through x and y coordinates separately for square and filtered pixels
        for square_coord, range_inside_image in zip(
            map(test_gui.dimension_to_pixel, square_coordinates[::-1]),
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

    def test_quit_button(self):
        """Tests if the quit button actually closes the GUI"""
        # Adds quit event to event queue, checking if GUI stops upon detecting it
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        # Creates test-specific GUI instance as testing quitting may disrupt other tests
        with ChessGUI() as test_gui:
            self.assertFalse(test_gui.running)


if __name__ == "__main__":
    unittest.main()
