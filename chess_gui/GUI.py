from os import environ
from threading import Thread

import pygame

# Instructs OS to open window slightly offset so all of it fits on the screen
environ["SDL_VIDEO_WINDOW_POS"] = "0, 30"


class ChessGUI:
    """Displays a GUI for a given chess state"""

    def __init__(self):
        """Initialises pygame components and draws board"""
        pygame.display.set_caption("Chess GUI")
        self.display = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        # Stores colour codes for light and dark squares, respectively
        self.board_colours = ((255, 255, 255), (120, 81, 45))

        # Creates dummy window for implementing design, enabling scaling to any screen
        self.design = pygame.Surface((1536, 864))
        self.square_size = 108  # Size of square in pixels to fill dummy window's height

        self.draw_board()

    def update(self):
        """Scales dummy design window to actual screen size and renders changes"""
        frame = pygame.transform.scale(self.design, self.display.get_size())
        self.display.blit(frame, frame.get_rect())
        pygame.display.flip()

    def draw_board(self):
        """Displays the current state of the board"""
        # Initialises list of rectangle (i.e. board square) coordinates
        rectangle = [0, 0, self.square_size, self.square_size]
        # Loops through each row and column, drawing squares and pieces
        for row in range(8):
            # Updates coordinates and square colours as appropriate
            rectangle[1] = row * self.square_size
            for column in range(8):
                rectangle[0] = column * self.square_size
                # Draws chess board square
                pygame.draw.rect(
                    self.design, self.board_colours[(row + column) % 2], rectangle
                )

    def __enter__(self):
        """
        Enables use of GUI in 'with' statement, keeping while loop that keeps GUI open
        running in separate thread to allow other code to execute
        """
        self.update()
        Thread(target=self.mainloop).start()
        return self

    def mainloop(self):
        """Keeps GUI running, handling events and rendering changes"""
        self.running = True
        while self.running:
            self.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Enables use of GUI in 'with' statement, closing when with statement ends"""
        self.running = False


if __name__ == "__main__":
    chess_gui = ChessGUI()
    chess_gui.mainloop()
