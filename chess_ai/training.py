"""Handles training of value network for MCTS using NEAT (parallel version)"""

from multiprocessing import cpu_count
from os import path

import neat

from chess_logic.board import SIDES
from chess_logic.core_chess import Chess
from chess_ai.mcts import MCTS

mcts = MCTS()


def simulate_match(
    test_player: neat.nn.FeedForwardNetwork,
    benchmark_player: neat.nn.FeedForwardNetwork,
    test_side: str,
) -> int:
    """Simulates match between 2 players, giving reward from test player perspective"""
    players = test_player, benchmark_player
    if test_side == "BLACK":
        players = players[::-1]
    sides_to_players = dict(zip(SIDES, players[:: (1 if test_side == "WHITE" else -1)]))
    chess_state = Chess()
    num_moves = 0
    while not chess_state.game_over:
        num_moves += 1
        move = mcts.best_move(chess_state, sides_to_players[chess_state.next_side])
        chess_state.move_piece(move)
    if chess_state.winner is None:
        return 0
    if chess_state.winner == test_side:
        return 1
    return -1


class Trainer:
    """Trains value network for MCTS using NEAT"""

    def __init__(self) -> None:
        # Load configuration.
        self.config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            path.join(path.dirname(__file__), "config-feedforward"),
        )
        self.best = self.best_genome = self.population = None

    def run(self) -> None:
        """Runs NEAT for certain number of generations using provided configuration"""
        # Create the population, which is the top-level object for a NEAT run.
        self.population = neat.Population(self.config)

        # Add a stdout reporter to show progress in the terminal.
        self.population.add_reporter(neat.StdOutReporter(True))
        stats = neat.StatisticsReporter()
        self.population.add_reporter(stats)

        # Store best genome and network associated with that genome
        self.best = self.best_genome = None

        # Run for up to 300 generations.
        population_evaluator = neat.ParallelEvaluator(cpu_count(), self.eval_genome)
        self.population.run(population_evaluator.evaluate, 300)

    def eval_genome(self, genome: neat.DefaultGenome, config: neat.Config) -> int:
        """Evaluates individual genome via competition with best genome until now"""
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        if self.population.best_genome != self.best_genome:
            self.best_genome = self.population.best_genome
            self.best = neat.nn.FeedForwardNetwork.create(
                self.best_genome, self.population.config
            )
        return (
            sum(simulate_match(net, self.best, side) for side in SIDES)
            * self.population.best_genome.fitness
            if self.population.best_genome is not None
            else 1
        )


if __name__ == "__main__":
    trainer = Trainer()
    trainer.run()
