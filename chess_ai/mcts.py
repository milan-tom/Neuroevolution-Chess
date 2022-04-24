"""Handles all functionality associated with MCTS"""

from __future__ import annotations

from collections import deque
from math import inf, log, sqrt
from typing import Optional

import neat.nn
from neat.nn import FeedForwardNetwork

from chess_logic.board import State
from chess_logic.core_chess import Chess, PerformedMove
from chess_logic.move_generation import Move, Moves


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
        if self.visited:
            if self.parent.visited:
                return self.reward / self.visited + sqrt(
                    2 * log(self.parent.visited) / self.visited
                )
            return self.reward / self.visited
        return inf

    def best_child(self) -> Node:
        """Returns child of node with highest UCB score"""
        return max(self.children, key=lambda child: child.ucb)

    def calculate_reward(self, chess_state: Chess, engine: neat.nn.FeedForwardNetwork):
        """Returns the estimated (exact for terminal node) reward value for node"""
        if self.cached_reward is None and chess_state.game_over:
            self.cached_reward = 0 if chess_state.is_check else 0.5
        if self.cached_reward is not None:
            return self.cached_reward
        return engine.activate(chess_state.numeric_repr)[0]

    def backpropagate(self, reward: int | float) -> None:
        """Feeds reward of simulated node up tree to parent at each level"""
        node = self
        while node.parent is not None:
            node.reward += reward
            node.visited += 1
            node = node.parent


class MCTS:
    """Handles all aspects of Monte Carlo Tree Search to find best move"""

    def __init__(self) -> None:
        """Initialises MCTS parameters"""
        self.chess_state: Optional[Chess] = None
        self.root: Optional[Node] = None
        self.initial_moves: Optional[Moves] = None
        self.initial_state: Optional[State] = None

    def best_move(
        self, chess_state: Chess, engine: FeedForwardNetwork, num_simulations: int
    ) -> Move:
        """Uses MCTS simulations and value network to find best move in current state"""
        self.chess_state = chess_state
        initial_side = self.chess_state.next_side
        self.initial_moves = self.chess_state.current_legal_moves
        self.initial_state = self.chess_state.current_state
        self.root = Node()
        self.expand_node(self.root)

        # Runs cycles of selection, expansion, simulation, and backpropagation
        for _ in range(num_simulations):
            node = self.select_node()
            undo_path = self.move_to_node_state(node)
            if node.cached_reward is None:
                if not node.children:
                    self.expand_node(node)
                node = node.best_child()
                undo_path.append(self.chess_state.move_piece(node.move))
            reward = node.calculate_reward(self.chess_state, engine)
            if self.chess_state.next_side != initial_side:
                reward = 1 - reward
            node.backpropagate(reward)
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
        if node == self.root:
            return deque()
        path = deque((node.move,))
        while (node := node.parent).parent is not None:
            path.appendleft(node.move)
        return deque(
            map(lambda move: self.chess_state.move_piece(move, update=False), path)
        )

    def expand_node(self, node: Node) -> None:
        """Adds all child nodes to given node"""
        self.chess_state.update_board_state()
        for move in self.chess_state.current_legal_moves:
            node.children.append(Node(node, move))

    def revert_state(self, undo_path: deque[PerformedMove]) -> None:
        """Undoes moves made to chess state based on order given"""
        for performed_move in reversed(undo_path):
            self.chess_state.undo_move(performed_move, update=False)
        self.chess_state.update_board_state(self.initial_moves, self.initial_state)
