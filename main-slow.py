import pygame as pg
import json
from pathlib import Path
from car import *
from track import *
from raycast import *
from utils import *
from random import choice
import neat

# I know there's an official python library for this (configparser), but configobj has more options and supports things like nested config sections.
from configobj import ConfigObj
from ast import literal_eval
g_cfg = ConfigObj("config.txt")["GAME"]
GAME_CONFIG = {}
for key, value in g_cfg.items():
    GAME_CONFIG.update({key : literal_eval(value)})

t_cfg = ConfigObj("config.txt")["AI_TRAINING"]
TRAINING_CONFIG = {}
for key, value in t_cfg.items():
    TRAINING_CONFIG.update({key : literal_eval(value)})

TRAINING_CONFIG["TIME_MULTIPLIER_DECAY"] = TRAINING_CONFIG["TIME_MULTIPLIER_DECAY"] / 1000

# Load tracks
with open(Path("data/tracks.json"), 'r') as tracks_raw:
    tracks = json.load(tracks_raw)

# Load fonts, can take several seconds to complete
pg.init()
default_font = pg.font.SysFont("monospace", 15)
ray_distance_font = pg.font.SysFont("monospace", 15)

# Create game display and game clock
window = pg.display.set_mode((1080, 720))
pg.display.init()
pg.display.update()
UPDATE_GAME = pg.USEREVENT
update_timer = pg.time.set_timer(UPDATE_GAME, 10)

ray_angles = (-90, -45, 0, 45, 90)

current_track = choice(tracks)
generations_since_change = TRAINING_CONFIG["GENERATIONS_PER_TRACK"]

def main(genomes, config) -> None:
    global current_track
    global generations_since_change
    if TRAINING_CONFIG["CHANGE_TRACKS"]:
        generations_since_change -= 1
        if generations_since_change == 0:
            current_track = choice(tracks)
            generations_since_change = TRAINING_CONFIG["GENERATIONS_PER_TRACK"]
            

    nets = []
    ge = []
    track = Track(window, (1080, 720), choice(tracks))
    cars = []
    car_rays = []
    car_multipliers = []

    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        car = Car(window, default_font, track.start_point,
                track.start_angle, TRAINING_CONFIG["SPAWN_VELOCITY"])
        car.last_cp = find_nearest_cp(track, car)
        cars.append(car)
        car_rays.append([Ray(window, ray_distance_font, (car.position.x, car.position.y),
                    -car.facing_angle + i) for i in ray_angles])
        car_multipliers.append(TRAINING_CONFIG["MAX_TIME_MULTIPLIER"])
        g.fitness = 0
        ge.append(g)

    for i, car in enumerate(cars):
        running = True
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                    pg.quit()
                    quit()
                elif event.type == UPDATE_GAME:
                    if car.distance_since_last < TRAINING_CONFIG["MIN_MOVE_AMOUNT"]:
                        ge[i].fitness -= TRAINING_CONFIG["DEATH_PENALTY"]
                        cars.pop(i)
                        car_rays.pop(i)
                        car_multipliers.pop(i)
                        nets.pop(i)
                        ge.pop(i)
                        running = False
                        break
                    
                     # Calculate distances from raycasts
                    input = []
                    for ii, ray in enumerate(car_rays[i]):
                        ray.set_origin((car.position.x, car.position.y))
                        ray.set_angle(-car.facing_angle + ray_angles[ii])
                        intersect = ray.multi_cast((track.inner_border_geometry,
                        track.outer_border_geometry))
                        input.append(intersect[0])
                    
                    # Get control inputs from the AI, move the car, and calculate any
                    # collisions or checkpoint passes
                    input += (car.speed, car.angle_delta, car.last_cp[1])
                    output = nets[i].activate(input)

                    if output[0] > TRAINING_CONFIG["STEERING_SNAP"]:
                        steering_input = 1
                    elif output[0] < -TRAINING_CONFIG["STEERING_SNAP"]:
                        steering_input = -1
                    else:
                        steering_input = 0

                    if output[1] > TRAINING_CONFIG["THROTTLE_SNAP"]:
                        throttle = 1
                    elif output[1] < -TRAINING_CONFIG["THROTTLE_SNAP"]\
                        and TRAINING_CONFIG["ALLOW_BRAKING"]:
                        throttle = -1
                    else:
                        throttle = 0

                    car.move(throttle, steering_input)

                    border_collision, new_checkpoint, new_lap =\
                        track.collide(car.hitbox, car.passed_checkpoints)

                    # Kill the AI if its car hits the track walls
                    if border_collision:
                        ge[i].fitness -= TRAINING_CONFIG["DEATH_PENALTY"]
                        cars.pop(i)
                        car_rays.pop(i)
                        car_multipliers.pop(i)
                        nets.pop(i)
                        ge.pop(i)
                        running = False
                        break

                    # Assign fitness values
                    if new_checkpoint != -1:
                        # If the car has passed a checkpoint, increase its fitness based
                        # on the time multiplier, then reset the time multiplier
                        score = TRAINING_CONFIG["CHECKPOINT_SCORE"] * car_multipliers[i]
                        ge[i].fitness += score
                        car_multipliers[i] = TRAINING_CONFIG["MAX_TIME_MULTIPLIER"]

                        # Add the checkpoint to the list of checkpoints the car has passed.
                        car.passed_checkpoints.append(new_checkpoint)

                        # Reset the car's passed checkpoints if it completes a lap
                        if new_lap:
                            car.passed_checkpoints = []
                        
                        # Reset the car's distance to the next checkpoint
                        car.last_cp = find_nearest_cp(track, car)

                    else:
                        # Decrease the car's time multiplier to a minimum of 1
                        car_multipliers[i] -= TRAINING_CONFIG["TIME_MULTIPLIER_DECAY"]
                        if car_multipliers[i] < 1:
                            car_multipliers[i] = 1

                        # Alter the AI's fitness based on its distance to the next checkpoint
                        new_distance = find_nearest_cp(track, car)
                        if new_distance[0] < car.last_cp[0]:
                            ge[i].fitness += (car.last_cp[0] - new_distance[0])\
                                                * TRAINING_CONFIG["CHECKPOINT_ADVANCE_SCORE"]
                            car.last_cp[0] = new_distance[0]
                        car.last_cp[1] = new_distance[1]

                    if len(cars) == 0:
                        running = False

            # Refresh the display
            window.fill(GAME_CONFIG["BACKGROUND_COLOR"])

            track.display()
            car.display()
            if GAME_CONFIG["SHOW_RAYS"]:
                for ray in car_rays[i]:
                    ray.display()

            pg.display.update()

def run(config_path:Path) -> None:
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                neat.DefaultStagnation, config_path)

    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    p.add_reporter(neat.StatisticsReporter())
    
    winner = p.run(main, TRAINING_CONFIG["NUM_GENERATIONS"])


if __name__ == "__main__":
    config_path = Path("neat_config.txt")
    run(config_path)