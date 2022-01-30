"""Contains """

from numpy import argsort, binary_repr
from tensorflow import keras

from chess_logic.core_chess import Chess


class ChessEngine:
    """Handles functionality of single engine powered by neural network"""

    def __init__(self):
        self.chess = Chess()
        self.create_network()

    def create_network(self):
        """Creates basic neural network mapping board state to output move"""
        self.network = keras.Sequential(
            [
                keras.layers.Dense(12 * 64, activation="relu"),
                keras.layers.Dense(1000, activation="sigmoid"),
                keras.layers.Dense(64 * 63, activation="softmax"),
            ]
        )

    def best_move(self):
        """Returns valid move in list of network outputs with highest output weight"""
        board_state = [
            bit
            for piece, board in self.chess.boards.items()
            if len(piece) == 1
            for bit in map(int, binary_repr(board, width=64))
        ]
        best_moves = self.network.predict([board_state])[0]
        valid_moves = tuple(map(int, self.chess.current_legal_moves))
        return next(
            self.chess.current_legal_moves[valid_moves.index(move)]
            for move in argsort(best_moves)
            if move in valid_moves
        )
