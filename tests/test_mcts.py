"""Contains all tests for Monte Carlo Tree Search (MCTS)"""

import pytest

from chess_ai.mcts import MCTS
from chess_ai.training import get_best_engine
from chess_logic.board import Coord
from chess_logic.core_chess import Chess
from tests import CHECKMATE_IN_TWO_FENS
from tests.test_move_generation import MOVE_TEST_DATA

TEST_ENGINE = get_best_engine()


@pytest.mark.parametrize("chess", MOVE_TEST_DATA, indirect=True)
def test_chess_state_preservation(mcts: MCTS, chess: Chess) -> None:
    """Tests that MCTS rollouts does not change initial chess state"""
    initial_fen = chess.fen
    mcts.best_move(chess, TEST_ENGINE, 100)
    assert chess.fen == initial_fen


@pytest.mark.parametrize(
    "chess, best_moves", CHECKMATE_IN_TWO_FENS.items(), indirect=["chess"]
)
def test_checkmate_positions(
    mcts: MCTS, chess: Chess, best_moves: tuple[tuple[Coord, Coord], ...]
) -> None:
    """Tests that MCTS yields best move in checkmate positions"""
    for move_i, best_move in enumerate(best_moves):
        if move_i % 2:
            chess.move_piece(
                next(
                    move for move in chess.current_legal_moves if move[:2] == best_move
                )
            )
        else:
            predicted_move = mcts.best_move(chess, TEST_ENGINE, 1000)
            assert predicted_move[:2] == best_move
            chess.move_piece(predicted_move)
