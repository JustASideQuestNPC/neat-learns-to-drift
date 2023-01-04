# Normally I don't like having a "utils" file,
# but main was just getting a little too crowded
# for my tastes.

from shapely import Point
from typing import List
from track import *
from car import *
from math import degrees, atan2

# Takes a track object and a car object, and returns the distance and angle
# to the nearest checkpoint the car hasn't passed. Used for AI training.
def find_nearest_cp(track:Track, car:Car) -> List:
    unpassed = track.get_unpassed_checkpoints(car.passed_checkpoints)
    unpassed_midpoints = [i[1] for i in unpassed]
    car_pos = Point(car.position.x, car.position.y)

    nearest_distance = 10000
    nearest_angle = 0
    for point in unpassed_midpoints:
        dist = car_pos.distance(point)
        if dist < nearest_distance:
            dy = point.coords[0][1] - car_pos.coords[0][1]
            dx = point.coords[0][0] - car_pos.coords[0][0]
            nearest_angle = degrees(atan2(dy, dx))
            nearest_distance = dist
        
    return [nearest_distance, -car.facing_angle - nearest_angle]