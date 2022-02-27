# November 2021
# simple FPS aim trainer

"""
TODO optimizations
"""

from __future__ import annotations
from win_info import GetClientPosition

import json
import neat
import pyautogui
import pygame as pg
from math import sqrt
from time import sleep
from random import randint
from typing import Callable

class UserExit(BaseException):
    """Raised on pg.QUIT"""

class ScoreCounter:
    __slots__ = "val"

    def __init__(self) -> None:
        self.val = 0

    def add(self, addend: float = 1) -> None:
        self.val += addend

    def adjust(self, avg_size: float, accuracy: float) -> int:
        return int(self.val * (accuracy - (avg_size - 1)/1000))

    def __str__(self) -> str:
        return str(int(self.val))

class Tile(pg.sprite.Sprite):
    __slots__ = "size", "value", "image", "rect"

    def __init__(self, spawn_area: dict[str, dict[str, int]], *groups: pg.sprite.Group, size: int | None = None) -> None:
        super().__init__(*groups)

        self.size = size or randint(30, 100) # hard coded normal range
        self.value = 100/sqrt(self.size)

        self.image = pg.Surface((self.size, self.size))
        self.image.fill((255, 0, 0))
        self.rect = pg.Rect(randint(spawn_area["min"]["x"], spawn_area["max"]["x"]-self.size), randint(spawn_area["min"]["y"], spawn_area["max"]["y"]-self.size), self.size, self.size)

    def update(self, mouse_pos: tuple[int, int], score: ScoreCounter) -> None:
        if self.rect.collidepoint(mouse_pos) and len(self.groups()[0]) == 3:
            self.kill()
            score.add(self.value)

class TileFactory:
    __slots__ = "sizes"

    def __init__(self) -> None:
        self.sizes = []

    def avg_size(self) -> float:
        return sum(self.sizes) / len(self.sizes)

    def create_n_tiles(self, spawn_area: dict[str, dict[str, int]], *groups: pg.sprite.Group, size: int | None = None, n: int = 1) -> list[Tile] | Tile:
        groups = groups or []

        if n == 1:
            new = Tile(spawn_area, *groups, size=size)
            self.sizes.append(new.size)
            return new

        new_tiles = [Tile(spawn_area, *groups, size=size) for _ in range(n)]
        self.sizes += [tile.size for tile in new_tiles]
        return new_tiles

class Button(pg.sprite.Sprite):
    __slots__ = "font", "label", "image", "rect", "func"

    def __init__(self, font: pg.font.Font, color: tuple[int, int, int], pos: tuple[int, int], *groups: pg.sprite.Group, label: str = "Button",
        func: Callable[[Button], None] = lambda _: None, right_justify: bool = False) -> None:
        super().__init__(*groups)

        x, y = pos
        label_w, label_h = font.size(label)
        if right_justify:
            x += 27
        else:
            x -= 37 + label_w

        self.font = font
        self.color = color
        self.label = label
        self.image = font.render(label, True, color)
        self.rect = pg.Rect(x, y, label_w, label_h)
        self.func = func

    def update(self, mouse_pos: tuple[int, int], clicked: bool) -> None:
        if clicked and self.rect.collidepoint(mouse_pos):
            self.func(self)
        elif self.rect.collidepoint(mouse_pos):
            self.image = self.font.render(self.label, True, (255, 0, 0))
        else:
            self.image = self.font.render(self.label, True, self.color)

def hud_time(duration: int) -> str:
    minutes = duration // 60
    seconds = duration % 60
    placeholder = "0" if seconds < 10 else ""

    return f"{minutes}:{placeholder}{seconds}"

def hud_size(hud_pos: dict[str, tuple[int, int]],font: pg.font.Font, score_str: str, time_str: str) -> dict[str, int]:
    score_size = font.size(score_str)
    time_size = font.size(time_str)

    score_x = hud_pos["score"][0] + score_size[0]
    score_y = hud_pos["score"][1] + score_size[1]
    time_x = hud_pos["time"][0] + time_size[0]
    time_y = hud_pos["time"][1] + time_size[1]

    return {"x": max(score_x, time_x)+10, "y": max(score_y, time_y)+10} # constant 10 provides padding around the HUD

def draw_hud(screen: pg.Surface, hud_pos: dict[str, tuple[int, int]], font: pg.font.Font, score: ScoreCounter, duration: int) -> None:
    score_str = str(score)
    time_str = hud_time(duration)

    screen.blit(font.render(score_str, True, (255, 255, 255)), hud_pos["score"])
    screen.blit(font.render(time_str, True, (255, 255, 255)), hud_pos["time"])

def draw_stats(screen: pg.Surface, font: pg.font.Font, clicks: int, hits: int, avg_size: float, adjusted_score: int) -> None:
    center_x, center_y = screen.get_rect().center
    bg = pg.Surface((bg_w:=0.7*screen.get_width(), bg_h:=0.7*screen.get_height()))
    bg.fill((128, 128, 128))

    with open("./assets/highscore.json") as f:
        highscores = json.load(f)

    stats_summary = (
        f"Tiles destroyed: {hits}",
        f"Accuracy: {int(100*hits/clicks)}%",
        f"Average tile size: {avg_size:.2f}",
        f"Adjusted score: {adjusted_score}",
        f"Human highscore: {highscores['Human']}",
        f"Computer highscore: {highscores['Computer']}"
    )
    stats_render = [font.render(x, True, (255, 255, 255)) for x in stats_summary]

    for i, x in enumerate(stats_render):
        bg.blit(x, (5, 5+22*i)) # matches default padding of the HUD

    screen.blit(bg, (center_x-bg_w//2, center_y-bg_h//2))

def manual(screen: pg.Surface) -> None:
    FRAMERATE = 60
    FONT = pg.font.SysFont("Consolas", 20)
    HUD_POS = {
        "score": (5, 5),
        "time": (5, 25)
    }

    factory = TileFactory()
    score = ScoreCounter()
    game_over = False
    countdown = 10
    fps_counter = 0
    click_count = 0
    hit_count = 0

    spawn_area = {
        "min": hud_size(HUD_POS, FONT, str(score), hud_time(countdown)),
        "max": {
            "x": screen.get_width(),
            "y": screen.get_height()
        }
    }

    tile_group = pg.sprite.Group(factory.create_n_tiles(spawn_area, n=3))
    clock = pg.time.Clock()

    while not game_over:
        screen.fill((0, 0, 0))
        tile_group.draw(screen)
        draw_hud(screen, HUD_POS, FONT, score, countdown)

        spawn_area["min"] = hud_size(HUD_POS, FONT, str(score), hud_time(countdown))
        pg.display.flip()

        if countdown == 0:
            game_over = True

        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise UserExit("game window was closed by the user")

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                tile_group.update(event.pos, score)
                click_count += 1
                break

        if len(tile_group) < 3:
            factory.create_n_tiles(spawn_area, tile_group)
            hit_count += 1

        fps_counter += 1
        if fps_counter == FRAMERATE:
            countdown -= 1
            fps_counter = 0

        clock.tick(FRAMERATE)

    click_count = click_count or 1 # prevents division by zero
    final_score = score.adjust(factory.avg_size(), hit_count/click_count)
    with open("./assets/highscore.json", "r+") as f:
        highscores = json.load(f)
        if final_score > highscores["Human"]:
            highscores["Human"] = final_score
            f.seek(0)
            f.truncate()
            f.write(json.dumps(highscores))

    button_group = pg.sprite.Group(
        Button(FONT, (255, 255, 255), (0.5*screen.get_width(), 0.6*screen.get_height()), label="Quit", func=lambda self: self.groups()[0].empty()),
        Button(FONT, (255, 255, 255), (0.5*screen.get_width(), 0.6*screen.get_height()), label="Replay", func=lambda self: self.kill(), right_justify=True)
    )
    num_buttons = len(button_group)
    game_over = False
    sleep(0.5)

    while not game_over:
        draw_stats(screen, FONT, click_count, hit_count, factory.avg_size(), final_score)
        button_group.draw(screen)
        pg.display.flip()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise UserExit("game window was closed by the user")

            if event.type == pg.MOUSEMOTION:
                button_group.update(event.pos, False)

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                button_group.update(event.pos, True)
                if not button_group:
                    return
                if len(button_group) < num_buttons:
                    game_over = True
                    manual(screen)
                break

        clock.tick(FRAMERATE)

def auto(screen: pg.Surface, nnet: neat.nn.FeedForwardNetwork, genome: neat.DefaultGenome | None = None, gui: bool = False) -> None:
    FRAMERATE = 8
    FONT = pg.font.SysFont("Consolas", 20)
    HUD_POS = {
        "score": (5, 5),
        "time": (5, 25)
    }

    factory = TileFactory()
    score = ScoreCounter()
    game_over = False
    countdown = 30 if gui else 3
    fps_counter = 0
    click_count = 0
    hit_count = 0

    spawn_area = {
        "min": hud_size(HUD_POS, FONT, str(score), hud_time(countdown)),
        "max": {
            "x": screen.get_width(),
            "y": screen.get_height()
        }
    }

    AutoClick = pg.event.custom_type()
    tile_group = pg.sprite.Group(factory.create_n_tiles(spawn_area, n=3))
    clock = pg.time.Clock()

    while not game_over:
        screen.fill((0, 0, 0))
        tile_group.draw(screen)
        draw_hud(screen, HUD_POS, FONT, score, countdown)

        spawn_area["min"] = hud_size(HUD_POS, FONT, str(score), hud_time(countdown))
        pg.display.flip()

        if countdown == 0:
            game_over = True

        pixel_dict = {tuple(screen.get_at((x, y))[:-1]): (x, y) for x in range(screen.get_width()) for y in range(screen.get_height())}

        for pixel in pixel_dict:
            if nnet.activate(pixel)[0] > 0.5:
                if gui:
                    x, y = map(sum, zip(pixel_dict[pixel], GetClientPosition(pg.display.get_wm_info()["window"])))
                    pyautogui.click(x, y, _pause=False)
                else:
                    pg.event.post(pg.event.Event(AutoClick, pos=pixel_dict[pixel]))
                break

        """ np_surface = pg.surfarray.pixels3d(screen)

        for x in range(screen.get_width()):
            for y in range(screen.get_height()):
                if nnet.activate(np_surface[x, y].tolist())[0] > 0.5:
                    pg.event.post(pg.event.Event(AutoClick, pos=(x, y)))
                    break

        del np_surface """

        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise UserExit("game window was closed by the user")

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                tile_group.update(event.pos, score)
                click_count += 1
                break

            if event.type == AutoClick:
                tile_group.update(event.pos, score)
                click_count += 1
                break

        if len(tile_group) < 3:
            factory.create_n_tiles(spawn_area, tile_group)
            hit_count += 1

        fps_counter += 1
        if fps_counter == FRAMERATE:
            countdown -= 1
            fps_counter = 0

        clock.tick(FRAMERATE)

    click_count = click_count or 1 # prevents division by zero
    final_score = score.adjust(factory.avg_size(), hit_count/click_count)

    if not gui:
        genome.fitness = final_score

    with open("./assets/highscore.json", "r+") as f:
        highscores = json.load(f)
        if final_score > highscores["Computer"]:
            highscores["Computer"] = final_score
            f.seek(0)
            f.truncate()
            f.write(json.dumps(highscores))

def train(genomes: list[tuple[int, neat.DefaultGenome]], config: neat.Config) -> None:
    pg.init()
    pg.display.set_icon(pg.image.load("./assets/icon.png"))
    pg.display.set_caption("FovaaK 0.2")

    net_dict = {genome: neat.nn.FeedForwardNetwork.create(genome, config) for _, genome in genomes}

    try:
        for _, genome in genomes:
            auto(pg.display.set_mode((400, 400)), net_dict[genome], genome)
    except UserExit as e:
        print(f"UserExit: {e}")

    pg.quit()

def test(nnet: neat.nn.FeedForwardNetwork) -> None:
    pg.init()
    pg.display.set_icon(pg.image.load("./assets/icon.png"))
    pg.display.set_caption("FovaaK 0.2")

    try:
        auto(pg.display.set_mode((400, 400)), nnet, gui=True)
    except UserExit as e:
        print(f"UserExit: {e}")

    pg.quit()

def main() -> None:
    pg.init()
    pg.display.set_icon(pg.image.load("./assets/icon.png"))
    pg.display.set_caption("FovaaK 0.2")

    try:
        manual(pg.display.set_mode((400, 400)))
    except UserExit as e:
        print(f"UserExit: {e}")

    pg.quit()

if __name__=="__main__":
    main()
