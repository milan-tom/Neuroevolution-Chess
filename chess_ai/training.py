"""Handles training of value network for MCTS using NEAT (parallel version)"""

from itertools import permutations
from multiprocessing import cpu_count, Pool
from os import path

from tqdm import tqdm
import neat

from chess_logic.board import SIDES
from chess_logic.core_chess import Chess
from chess_ai.mcts import MCTS

CONFIG = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    path.join(path.dirname(__file__), "config-feedforward"),
)
mcts = MCTS()
ValueNet = neat.nn.FeedForwardNetwork


def simulate_match(
    white_player: neat.nn.FeedForwardNetwork,
    black_player: neat.nn.FeedForwardNetwork,
) -> int:
    """Simulates match between 2 players, giving reward from test player perspective"""
    sides_to_players = dict(zip(SIDES, (white_player, black_player)))
    chess_state = Chess()
    while not chess_state.game_over and chess_state.move_number <= 50:
        move = mcts.best_move(chess_state, sides_to_players[chess_state.next_side])
        chess_state.move_piece(move)
    if chess_state.winner is None:
        return 0, 0
    if chess_state.winner == "WHITE":
        return 1, -1
    return -1, 1


def eval_genomes(
    genomes_data: list[tuple[int, neat.DefaultGenome]], config: neat.Config
) -> int:
    """Evaluates all genomes via competition with each other"""
    genomes = [genome_data[1] for genome_data in genomes_data]
    for genome in genomes:
        genome.fitness = 0
    nets = {
        genome: neat.nn.FeedForwardNetwork.create(genome, config) for genome in genomes
    }

    # Runs evaluation in parallel
    with Pool(cpu_count()) as pool:
        matches = tuple(permutations(genomes, 2))
        jobs = [
            pool.apply_async(simulate_match, tuple(map(nets.get, players)))
            for players in matches
        ]

        for job, players in tqdm(tuple(zip(jobs, matches))):
            for genome, reward in zip(players, job.get()):
                genome.fitness += reward


def run_training(num_generations: int) -> None:
    """Runs NEAT for certain number of generations using provided configuration"""
    # Create the population, which is the top-level object for a NEAT run.
    population = neat.Population(CONFIG)

    # Add a stdout reporter to show progress in the terminal.
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    population.run(eval_genomes, num_generations)


if __name__ == "__main__":
    run_training(300)