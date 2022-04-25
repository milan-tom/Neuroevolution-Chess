"""Handles training of value network for MCTS using NEAT (parallel version)"""

from collections import defaultdict
from functools import partial
from multiprocessing import Pool, cpu_count
from os import listdir, mkdir, path
from pickle import dump, load
from random import sample
from typing import Any

import neat
from tqdm import tqdm

from chess_ai.mcts import MCTS
from chess_logic.core_chess import Chess
from chess_logic.move_generation import Move, Moves


def get_latest(directory: str, default: Any) -> str:
    """Returns latest file in folder of numerically-labelled files"""
    return max(listdir(directory), key=int, default=str(default))


CURRENT_PATH = path.dirname(__file__)
SAVE_DIRS = BEST_GENOMES_DIR, TRAINING_MATCHES_DIR, CHECKPOINT_DIR = (
    "best_genomes",
    "training_matches",
    "neat_checkpoints",
)
for save_dir in SAVE_DIRS:
    if not path.exists(absolute_path := path.join(CURRENT_PATH, save_dir)):
        mkdir(absolute_path)
STATS_FILE = "stats"
CONFIG = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    path.join(CURRENT_PATH, "config-feedforward"),
)

GenomePlayers = tuple[neat.DefaultGenome, neat.DefaultGenome]


def simulate_match(
    players: tuple[neat.nn.FeedForwardNetwork, neat.nn.FeedForwardNetwork]
) -> tuple[tuple[int | float, int | float], Moves]:
    """Simulates match between 2 players, giving reward from test player perspective"""
    chess_state = Chess()
    mcts = MCTS()
    moves: list[Move] = []
    while not chess_state.game_over and chess_state.move_number <= 50:
        move = mcts.best_move(chess_state, players[len(moves) % 2], 1000)
        chess_state.move_piece(move)
        moves.append(move)
    rewards = (0, 0) if chess_state.winner is None else (1.25, -1)
    return (rewards[::-1] if chess_state.winner == "BLACK" else rewards), tuple(moves)


def save_to_pickle(obj: Any, filename: Any, directory: str = "") -> None:
    """Saves object to pickle file at path relative to current directory"""
    with open(path.join(CURRENT_PATH, directory, str(filename)), "wb") as pickle_file:
        dump(obj, pickle_file)


def load_from_pickle(filename: Any, directory: str = "") -> Any:
    """Loads object from pickle file  at path relative to current directory"""
    if path.exists(file_path := path.join(CURRENT_PATH, directory, filename)):
        with open(file_path, "rb") as pickle_file:
            return load(pickle_file)
    raise FileNotFoundError(f"{file_path} not found")


save_best = partial(save_to_pickle, directory=BEST_GENOMES_DIR)
save_matches = partial(save_to_pickle, directory=TRAINING_MATCHES_DIR)


def get_best_engine() -> neat.nn.FeedForwardNetwork:
    """Returns the engine encoded by the best genome from the last trained generation"""
    return neat.nn.FeedForwardNetwork.create(
        load_from_pickle(
            get_latest(path.join(CURRENT_PATH, BEST_GENOMES_DIR), 0), BEST_GENOMES_DIR
        ),
        CONFIG,
    )


class SavedStatisticsReporter(neat.StatisticsReporter):
    # pylint: disable=too-few-public-methods
    """Introduces self-saving functionality to NEAT-Python's StatisticsReporter"""

    def post_evaluate(self, *args, **kwargs) -> None:
        """Saves itself as pickle file after performing normal post-evaluation duties"""
        super().post_evaluate(*args, **kwargs)
        save_to_pickle(self, STATS_FILE)


class Trainer(neat.Population):
    """Trains value network for MCTS using NEAT"""

    def __init__(self) -> None:
        """Initialises population from checkpoints if present else from scratch"""
        # Instantiates checkpointer to store/restore generations
        checkpointer = neat.Checkpointer(
            1, filename_prefix=path.join(CURRENT_PATH, CHECKPOINT_DIR)
        )

        if latest := get_latest(CHECKPOINT_DIR, ""):
            population = checkpointer.restore_checkpoint(
                path.join(CHECKPOINT_DIR, latest)
            )
            super().__init__(
                population.config,
                (population.population, population.species, population.generation),
            )
            stats = load_from_pickle(STATS_FILE)
            for stats_list in (stats.most_fit_genomes, stats.generation_statistics):
                del stats_list[self.generation :]
        else:
            super().__init__(CONFIG)
            stats = SavedStatisticsReporter()

        # Add reporters to track progress and display information in the terminal
        for reporter in (neat.StdOutReporter(True), stats, checkpointer):
            self.add_reporter(reporter)
        self.genomes: list[neat.DefaultGenome] = []

    def run_training(self, num_generations: int) -> None:
        """Runs NEAT for certain number of generations using provided configuration"""
        self.run(self.eval_genomes, num_generations - self.generation + 1)

    def generate_matches(self, num_to_face: int) -> list[GenomePlayers]:
        """Generates matches between each genome and certain sample of other genomes"""
        matches = []
        for _ in range(len(self.genomes)):
            genome = self.genomes.pop()
            for opponent_genome in sample(self.genomes, num_to_face):
                matches.append((genome, opponent_genome))
            self.genomes.insert(0, genome)
        return matches

    def eval_genomes(
        self, genomes_data: list[tuple[int, neat.DefaultGenome]], config: neat.Config
    ) -> None:
        """Evaluates all genomes via competition with each other"""
        self.genomes = [genome_data[1] for genome_data in genomes_data]
        for genome in self.genomes:
            genome.fitness = 0
        nets = {
            genome: neat.nn.FeedForwardNetwork.create(genome, config)
            for genome in self.genomes
        }

        training_matches = defaultdict(list)
        matches = self.generate_matches(10)
        # Runs evaluation in parallel
        with Pool(cpu_count()) as pool:
            jobs = [
                pool.apply_async(simulate_match, (tuple(map(nets.get, players)),))
                for players in matches
            ]

            for job, players in tqdm(tuple(zip(jobs, matches))):
                rewards, moves = job.get()
                training_matches[rewards].append((players, moves))
                for genome, reward in zip(players, rewards):
                    genome.fitness += reward

        save_best(max(self.genomes, key=lambda x: x.fitness), self.generation)
        save_matches(training_matches, self.generation)


if __name__ == "__main__":
    trainer = Trainer()
    trainer.run_training(300)
