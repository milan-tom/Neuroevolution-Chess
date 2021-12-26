"""Contains all unit tests for GUI"""

import unittest
import pygame

from chess_gui.gui import Design
from chess_logic.board import ROWS_AND_COLUMNS


test_design = Design()


class DesignTest(unittest.TestCase):
    """TestCase subclass for design window unit tests"""

    def test_square_fill(self) -> None:
        """Test if squares fill allocated space and handle borders correctly"""
        # Loops through beginnings of squares horizontally and vertically
        for square_coords in ROWS_AND_COLUMNS:
            with self.subTest(square_coords=square_coords):
                test_pxarray = pygame.PixelArray(test_design)
                # Checks all pixels in square have same colour as first pixel
                square_x, square_y = test_design.square_to_pixel(square_coords)
                square_colour = test_pxarray[square_x][square_y]
                self.assertTrue(
                    all(
                        test_pxarray[x][y] == square_colour
                        for x, y in test_design.get_square_range(square_coords)
                    ),
                )

    def test_square_colours(self) -> None:
        """Tests a sample of squares within the chess board to check square colours"""
        # Stores test square coordinates and expected colours in dictionary
        light, dark = test_design.board_colours
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
                        test_design.get_at(test_design.square_to_pixel(test_square))[
                            :-1
                        ],
                        expected_colour,
                    )
