"""Handles all functionality associated with MCTS"""

from __future__ import annotations
from collections import deque
from math import inf, log, sqrt
from typing import Iterable

from neat.nn import FeedForwardNetwork

from chess_logic.board import rotate_bitboard, swap_halves
from chess_logic.core_chess import Chess, PerformedMove
from chess_logic.move_generation import Move


class Node:
    """Represents single node in MCTS"""

    def __init__(self, parent=None, move=None):
        self.parent = parent
        self.move = move
        self.children = []
        self.visited = self.reward = 0
        self.cached_reward = None

    @property
    def ucb(self):
        """Returns Upper Confidence Bound (UCB) score for node"""
        if self.visited and self.parent.visited:
            return self.reward / self.visited + sqrt(
                2 * log(self.parent.visited) / self.visited
            )
        return inf

    def best_child(self) -> Node:
        """Returns child of node with highest UCB score"""
        return max(self.children, key=lambda child: child.ucb)

    def calculate_reward(self, chess_state, engine):
        """Returns the estimated (exact for terminal node) reward value for node"""
        if self.cached_reward is None and chess_state.game_over:
            self.cached_reward = -1 * chess_state.is_check
        if self.cached_reward is not None:
            return self.cached_reward
        bitboards = [
            board for piece, board in chess_state.boards.items() if len(piece) == 1
        ]
        if chess_state.next_side == "BLACK":
            bitboards = list(map(rotate_bitboard, swap_halves(bitboards, 6)))
        return engine.activate(bitboards + chess_state.int_metadata)[0]

    def backpropagate(self, reward: int | float) -> None:
        """Feeds reward of simulated node up tree to parent at each level"""
        node = self
        while node is not None:
            node.reward += reward
            node.visited += 1
            reward *= -1
            node = node.parent


class MCTS:
    """Handles all aspects of Monte Carlo Tree Search to find best move"""

    def __init__(self) -> None:
        """Initialises MCTS parameters"""
        self.chess_state = self.root = None

    def best_move(self, chess_state: Chess, engine: FeedForwardNetwork) -> Move:
        """Uses MCTS simulations and value network to find best move in current state"""
        self.chess_state = chess_state
        self.root = Node()
        self.expand_node(self.root)

        # Runs cycles of selection, expansion, simulation, and backpropogation
        for _ in range(100):
            node = self.select_node()
            undo_path = self.move_to_node_state(node)
            if node.cached_reward is None:
                if not node.children:
                    self.expand_node(node)
                node = node.best_child()
                undo_path.append(self.chess_state.move_piece(node.move))
            node.backpropagate(node.calculate_reward(self.chess_state, engine))
            self.revert_state(undo_path)

        return max(self.root.children, key=lambda child: child.visited).move

    def select_node(self) -> Node:
        """Returns best node in current tree state"""
        node = self.root
        while node.children and all(child.visited for child in node.children):
            node = node.best_child()
        return node

    def move_to_node_state(self, node: Node) -> deque[PerformedMove]:
        """Moves chess state to that of given node, returning order to undo moves"""
        if node != self.root:
            path = deque((node.move,))
            while (node := node.parent).parent is not None:
                path.appendleft(node.move)
            return deque(
                map(lambda move: self.chess_state.move_piece(move, update=False), path)
            )
        return deque()

    def expand_node(self, node: Node) -> None:
        """Adds all child nodes to given node"""
        self.chess_state.update_board_state()
        for move in self.chess_state.current_legal_moves:
            node.children.append(Node(node, move))

    def revert_state(self, undo_path: Iterable[PerformedMove]) -> None:
        """Undoes moves made to chess state based on order given"""
        deque(map(self.chess_state.undo_move, reversed(undo_path)), maxlen=0)
