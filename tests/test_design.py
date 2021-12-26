"""Contains all unit tests for GUI"""

import pygame

from chess_logic.board import ROWS_AND_COLUMNS


def test_square_fill(design) -> None:
    """Test if squares fill allocated space and handle borders correctly"""
    # Loops through beginnings of squares horizontally and vertically
    for square_coords in ROWS_AND_COLUMNS:
        test_pxarray = pygame.PixelArray(design)
        # Checks all pixels in square have same colour as first pixel
        square_x, square_y = design.square_to_pixel(square_coords)
        square_colour = test_pxarray[square_x][square_y]
        assert all(
            test_pxarray[x][y] == square_colour
            for x, y in design.get_square_range(square_coords)
        )


def test_square_colours(design) -> None:
    """Tests a sample of squares within the chess board to check square colours"""
    design.draw_board_squares()

    # Stores test square coordinates and expected colours in dictionary
    light, dark = design.board_colours
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
            actual_colour = design.get_at(design.square_to_pixel(test_square))[:-1]
            assert expected_colour == actual_colour
