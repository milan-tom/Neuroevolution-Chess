import pygame


class ChessGUI:
    def __init__(self):
        """Initialises pygame components, and draws board"""
        self.surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # Stores colour codes for light and dark squares, respectively
        self.board_colours = ((255, 255, 255), (120, 81, 45))
        # Maximises board square size based on available height, storing it in pixels
        self.square_size = self.surface.get_height() // 8
        
        self.draw_board()

    def draw_board(self):
        rectangle = [0, 0, self.square_size, self.square_size]
        for row in range(8):
            rectangle[1] = row * self.square_size
            for column in range(8):
                rectangle[0] = column * self.square_size
                pygame.draw.rect(
                    self.surface, self.board_colours[(row + column) % 2], rectangle
                )

        pygame.display.update()

    def mainloop(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False


chess_gui = ChessGUI()
chess_gui.mainloop()
