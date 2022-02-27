# October 2021
# Boilerplate code for using NEAT in Python

import neat
from typing import Callable

def setup_and_run(func: Callable[[list[tuple[int, neat.DefaultGenome]], neat.Config], None]):
    def wrapper(config_path: str) -> neat.DefaultGenome:
        config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                    neat.DefaultSpeciesSet, neat.DefaultStagnation, config_path)

        population = neat.Population(config)

        population.add_reporter(neat.StdOutReporter(True))

        winner = population.run(func, 10)

        print(f"Best genome: \n{'-'*30}\n{winner}\n{'-'*30}")

        return winner
    return wrapper
