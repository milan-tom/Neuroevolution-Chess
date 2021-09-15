import unittest
from itertools import product

import pygame.event

from chess_gui.GUI import ChessGUI


class ChessGUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Creates common GUI instance to be used by most tests"""
        cls.test_gui = ChessGUI()
        cls.square_size = cls.test_gui.square_size

    def test_square_fill(self):
        """Test if squares fill allocated space and handle borders correctly"""
        # Loops through beginnings of squares horizontally and vertically
        for square_coordinates in product(range(8), repeat=2):
            with self.subTest(square_coordinates=square_coordinates):
                # Checks all pixels in square have same colour as first pixel
                x, y = map(lambda coord: coord * self.square_size, square_coordinates)
                square_colour = self.test_gui.design.get_at((x, y))
                self.assertTrue(
                    all(
                        self.test_gui.design.get_at((x + x_move, y + y_move))
                        == square_colour
                        for x_move, y_move in product(range(self.square_size), repeat=2)
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

    def test_quit_button(self):
        """Tests if the quit button actually closes the GUI"""
        # Adds quit event to event queue, checking if GUI stops upon detecting it
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        # Creates test-specific GUI instance as testing quitting may disrupt other tests
        with ChessGUI() as test_gui:
            self.assertFalse(test_gui.running)
