"""Contains all functionality of chess engine"""

from typing import Optional

from numpy import argsort
from tensorflow.keras import layers, Sequential

from chess_logic.core_chess import Chess
from chess_logic.move_generation import Move


class ChessEngine:
    """Handles functionality of single engine powered by neural network"""

    def __init__(self):
        self.create_network()
        self.thinking = False

    def create_network(self):
        """Creates basic neural network mapping board state to output move"""
        self.network = Sequential(
            [
                layers.Dense(20, activation="relu"),
                layers.Dense(1000, activation="sigmoid"),
                layers.Dense(64 * 63, activation="softmax"),
            ]
        )

    def best_move(self, chess_state: Chess) -> Optional[Move]:
        """Returns valid move in list of network outputs with highest output weight"""
        self.thinking = True
        board_state = [
            board for piece, board in chess_state.boards.items() if len(piece) == 1
        ] + chess_state.int_metadata
        best_moves = self.network.predict([board_state])[0]
        valid_moves = tuple(map(int, chess_state.current_legal_moves))
        self.thinking = False
        return next(
            chess_state.current_legal_moves[valid_moves.index(move)]
            for move in argsort(best_moves)
            if move in valid_moves
        )
