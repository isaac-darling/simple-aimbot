# October 2021
# main function for running aim trainer using NEAT

import pickle
import neat
import fovaaks
from boilerplate import neat_

@neat_.setup_and_run
def train(genomes: list[tuple[int, neat.DefaultGenome]], config: neat.Config) -> None:
    fovaaks.train(genomes, config)

def test(config_path: str) -> None:
    with open("./assets/genome.pkl", "rb") as f:
        genome = pickle.load(f)

    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_path)

    nnet = neat.nn.FeedForwardNetwork.create(genome, config)

    fovaaks.test(nnet)

def main() -> None:
    winner = train("config-feedforward.conf")
    with open("./assets/genome.pkl", "wb") as f:
        pickle.dump(winner, f)

    #test("config-feedforward.conf")

if __name__=="__main__":
    main()
