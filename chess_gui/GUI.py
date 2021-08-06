import pygame


class ChessGUI:
    def __init__(self):
        """Initialises pygame components and draws board"""
        self.surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # Stores colour codes for light and dark squares, respectively
        self.board_colours = ((255, 255, 255), (120, 81, 45))
        # Maximises board square size based on available height, storing it in pixels
        self.square_size = self.surface.get_height() // 8
        
        self.draw_board()

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
                    self.surface, self.board_colours[(row + column) % 2], rectangle
                )
        # Updates display to render changes
        pygame.display.update()

    def mainloop(self):
        """Keeps GUI running, handling events and rendering changes"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False


chess_gui = ChessGUI()
chess_gui.mainloop()
