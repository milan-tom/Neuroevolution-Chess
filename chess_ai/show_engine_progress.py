"""
Visualises the various aspects of the training of the engine:
    1. Speciation
    2. Average fitness
    3. NeuroEvolution of the best genome
    4. Best simulated matches played during training via NEAT
"""

from os import listdir, path

import pygame
from httpimport import remote_repo

from chess_ai.training import SavedStatisticsReporter  # pylint: disable=unused-import
from chess_ai.training import (
    BEST_GENOMES_DIR,
    CONFIG,
    CURRENT_PATH,
    STATS_FILE,
    TRAINING_MATCHES_DIR,
    GenomePlayers,
    load_from_pickle,
)
from chess_gui.gui import ChessGUI
from chess_logic.board import CASTLING_SYMBOLS, PIECES
from chess_logic.move_generation import Moves

with remote_repo(
    ["visualize"],
    "https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/examples/xor",
):
    from visualize import draw_net, plot_species, plot_stats

# Imports pickled best genome files and training match files
BEST_GENOMES, TRAINING_MATCHES = [
    [
        load_from_pickle(path.join(load_dir, match_file))
        for match_file in sorted(listdir(path.join(CURRENT_PATH, load_dir)), key=int)
    ]
    for load_dir in [BEST_GENOMES_DIR, TRAINING_MATCHES_DIR]
]


def show_best_genomes() -> None:
    """Displays best genomes from each generation using GUI window"""
    gui = ChessGUI(display_only=True)
    display_rect = gui.display.get_rect()
    display_rect.height = int(display_rect.height * 0.8)
    image_space = gui.display.subsurface(display_rect)
    image_space_rect = image_space.get_rect()

    image_path = path.join(CURRENT_PATH, "best_genome.png")
    node_names = list(PIECES) + ["EP"] + [right + "C" for right in CASTLING_SYMBOLS]
    keys = dict(zip(range(-1, -18, -1), node_names))
    for generation, genome in enumerate(BEST_GENOMES):
        gui.display.fill("black")
        draw_net(CONFIG, genome, filename=image_path[:-4], node_names=keys, fmt="png")
        best_genome_image = pygame.image.load(image_path)

        if (image_height := best_genome_image.get_height()) > image_space_rect.height:
            scale = image_space_rect.height / image_height
            best_genome_image = pygame.transform.smoothscale(
                best_genome_image, [x * scale for x in best_genome_image.get_size()]
            )

        (image_rect := best_genome_image.get_rect()).center = image_space_rect.center
        image_space.blit(best_genome_image, image_rect)
        gui.show_text(
            f"Generation {generation}", rel_y=0.9, destination_surface=gui.display
        )
        pygame.display.flip()
        pygame.time.wait(1000)


def show_match(match: Moves, message: str) -> None:
    """Displays a given match with a given message displayed throughout match"""
    gui = ChessGUI(display_only=True, display_message=message)
    for move in match:
        gui.move_piece(move)
        gui.mainloop(50)
    gui.mainloop(1000)


def best_training_match(training_matches: list[tuple[GenomePlayers, Moves]]) -> Moves:
    """Returns the best training match"""
    return max(training_matches, key=lambda x: sum(player.fitness for player in x[0]))[
        1
    ]


def show_matches() -> None:
    """Displays best training draws and wins from each generation using GUI window"""
    for generation, generation_matches in enumerate(TRAINING_MATCHES):
        if draws := generation_matches[(0, 0)]:
            show_match(
                best_training_match(draws), f"Generation {generation} - Best Draw"
            )
        wins = [
            match
            for rewards, matches in generation_matches.items()
            if rewards != (0, 0)
            for match in matches
        ]
        if wins:
            show_match(best_training_match(wins), f"Generation {generation} - Best Win")


if __name__ == "__main__":
    stats = load_from_pickle(STATS_FILE)
    plot_stats(stats, ylog=False, view=True)
    plot_species(stats, view=True)

    show_best_genomes()
    show_matches()
