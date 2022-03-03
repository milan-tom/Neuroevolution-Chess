"""Handles functions of the engine based on the best saved genome"""

from chess_ai.mcts import MCTS
from chess_ai.training import get_best_engine
from chess_logic.core_chess import Chess
from chess_logic.move_generation import Move

mcts = MCTS()
best_engine = get_best_engine()


def best_engine_move(chess_state: Chess, num_simulations: int) -> Move:
    """Gets the best move in the current chess state using the best engine"""
    return mcts.best_move(chess_state, best_engine, num_simulations)
