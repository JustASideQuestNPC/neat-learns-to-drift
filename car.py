import pygame as pg
from typing import Tuple
from ast import literal_eval
from math import inf as infinity
from math import sqrt
# These get used so often that it's easier if they don't have a prefix
from pygame.math import clamp
from pygame import Vector2
# I know there's an official python library for this (configparser), but configobj has more options and supports things like nested config sections.
from configobj import ConfigObj
cfg = ConfigObj("config.txt")["CAR"]

# Pygame has trouble rotating images around their center for some reason.
def blitRotateCenter(surf, image, topleft, angle):

    rotated_image = pg.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)

    surf.blit(rotated_image, new_rect)

# Maps a value from one range of values to the equivalent place in another range of values.
def map_ranges(value, from_min, from_max, to_min, to_max):
    from_span = from_max - from_min
    to_span = to_max - to_min

    scaled = float(value - from_min) / float(from_span)

    return to_min + (scaled * to_span)

class Car:
    # The values for constants can be found (and messed with) in the config.txt file
    # Control constants
    (MAX_SPEED,
     TURN_SPEED_MULT,
     SPEED_START_DELTA,
     SPEED_END_DELTA,
     ACCELERATION,
     BRAKING_FORCE,
     FRICTION) = [literal_eval(value) for _, value in cfg["CONTROL"].items()]

    # Steering constants
    (STEERING_RESPONSE,
     TURN_STEERING_MULT,
     STEER_START_DELTA,
     STEER_END_DELTA) = [literal_eval(value) for _, value in cfg["STEERING"].items()]

    # Grip constants, determine how "drifty" the car is
    (SNAP_THRESHOLD,
     MAX_DELTA,
     NO_OVERSHOOT,
     MIN_GRIP,
     MAX_GRIP,
     POINT_SCALAR,
     GRIP_EXP) = [literal_eval(value) for _, value in cfg["PHYSICS"].items()]
    if MAX_GRIP < 0 or MAX_GRIP < MIN_GRIP:
        MAX_GRIP = infinity

    # Display constants
    (WIDTH,
     LENGTH,
     BODY_COLOR) = [literal_eval(value) for _, value in cfg["DISPLAY"].items()]

    # Debug constants
    (VECTOR_DEBUG,
     VELOCITY_COLOR,
     FACING_COLOR,
     LINE_WIDTH,
     DEBUG_TEXT) = [literal_eval(value) for _, value in cfg["DEBUG"].items()]

    # Used for checkpoint passes and collisions with track border.
    hitbox = ((0, 0,), (WIDTH, 0), (WIDTH, LENGTH), (0, LENGTH))
    last_cp = [10000, 0] # Distance and angle to the last checkpoint
    distance_since_last = 10000

    # Which checkpoints have already been passed, prevents
    # checkpoints from being counted more than once per lap.
    passed_checkpoints = []

    def __init__(self, surface:pg.surface.Surface, debug_font:pg.font.SysFont, start_position:Tuple[float,float],
                start_angle:float, initial_velocity:float=0,) -> None:
        self.surface = surface
        self.debug_font = debug_font
        
        # Create vectors for position, velocity, and acceleration
        self.position = Vector2(start_position[0], start_position[1])
        self.speed = initial_velocity

        # The velocity angle needs to be the reverse of the facing angle or the car moves backwards.
        # Why does it do this? I have no idea...pygame is weird sometimes.
        self.facing_angle = start_angle
        self.velocity_angle = -start_angle
        self.angle_delta = 0

    # Parses control input, applies physics, and moves the car
    # Steering and throttle input are both between -1 to 1
    # Positive steering values turn right and negative ones turn left
    # Positive throttle values accelerate and negative ones brake
    def move(self, throttle:float, steering_input:float) -> None:

        if throttle > 0:
            accel = self.ACCELERATION
        elif throttle < 0:
            accel = -self.BRAKING_FORCE
        else:
            accel = -self.FRICTION

        
        self.speed += accel
        speed_reduction = map_ranges(abs(self.angle_delta), self.SPEED_START_DELTA, self.SPEED_END_DELTA,
                                1, self.TURN_SPEED_MULT)
        if self.TURN_SPEED_MULT <= 1:
            speed_reduction = clamp(speed_reduction, self.TURN_SPEED_MULT, 1)
        else:
            speed_reduction = clamp(speed_reduction, 1, self.TURN_SPEED_MULT)
        current_top_speed = self.MAX_SPEED * speed_reduction
        self.speed = clamp(self.speed, 0, current_top_speed)

        # Calculate steering reduction based on facing angle, then update facing angle
        steering_amount = self.STEERING_RESPONSE * steering_input
        steering_reduction = map_ranges(abs(self.angle_delta), self.STEER_START_DELTA, self.STEER_END_DELTA,
                                1, self.TURN_STEERING_MULT)
        if self.TURN_STEERING_MULT <= 1:
            steering_reduction = clamp(steering_reduction, self.TURN_STEERING_MULT, 1)
        else:
            steering_reduction = clamp(steering_reduction, 1, self.TURN_STEERING_MULT)

        self.facing_angle -= steering_amount * steering_reduction

        # Do all the drift physics calculations
        self.angle_delta = -self.facing_angle - self.velocity_angle
        self.__turn_velocity()

        applied_velocity = Vector2(0, self.speed)
        applied_velocity.rotate_ip(self.velocity_angle)

        # Update car's position and the distance it moved since the last update
        old_position = (self.position.x, self.position.y)
        self.position += applied_velocity
        new_position = (self.position.x, self.position.y)
        dx = new_position[0] - old_position[0]
        dy = new_position[1] - old_position[1]
        self.distance_since_last = sqrt(dx**2 + dy**2)

        self.hitbox = ((self.position.x - self.WIDTH / 2, self.position.y - self.LENGTH / 2),
                        (self.position.x + self.WIDTH / 2, self.position.y - self.LENGTH / 2),
                        (self.position.x + self.WIDTH / 2, self.position.y + self.LENGTH / 2),
                        (self.position.x - self.WIDTH / 2, self.position.y + self.LENGTH / 2))


    def __calc_turn_amount(self) -> float:
        delta = abs(self.angle_delta)
        turn_amount = clamp(self.GRIP_EXP ** (0.1 *(delta - self.POINT_SCALAR)), self.MIN_GRIP, self.MAX_GRIP)
        
        if self.angle_delta < 0:
            turn_amount *= -1
        
        return turn_amount


    def __turn_velocity(self) -> None:
        if abs(self.angle_delta) < self.SNAP_THRESHOLD:
            self.velocity_angle = -self.facing_angle
            return

        turn_amount = self.__calc_turn_amount()

        self.velocity_angle += turn_amount
        self.velocity_angle = clamp(self.velocity_angle,
            -self.facing_angle - self.MAX_DELTA, -self.facing_angle + self.MAX_DELTA)
        
        new_delta = -(self.facing_angle + self.velocity_angle)
        if ((self.angle_delta < 0 and new_delta > 0) or (self.angle_delta > 0 and new_delta < 0))\
            and self.NO_OVERSHOOT:
            self.velocity_angle = -self.facing_angle


    def display(self) -> None:
        sub_surface = pg.Surface((self.WIDTH, self.LENGTH), pg.SRCALPHA)
        pg.draw.rect(sub_surface, self.BODY_COLOR,
                    pg.rect.Rect(0, 0, self.WIDTH, self.LENGTH))
        sub_rect = sub_surface.get_rect()
        sub_rect.center = (self.position.x, self.position.y)

        blitRotateCenter(self.surface, sub_surface, sub_rect.topleft, self.facing_angle)

        if self.VECTOR_DEBUG:
            v_scaled = Vector2(0, self.speed * 50)
            v_scaled.rotate_ip(self.velocity_angle)
            v_end = (self.position + v_scaled)
            pg.draw.line(self.surface, self.VELOCITY_COLOR,
                         (self.position.x, self.position.y),
                         (v_end.x, v_end.y), self.LINE_WIDTH)

            f_scaled = Vector2(0, self.speed * 50)
            f_scaled.rotate_ip(-self.facing_angle)
            f_end = (self.position + f_scaled)
            pg.draw.line(self.surface, self.FACING_COLOR,
                         (self.position.x, self.position.y),
                         (f_end.x, f_end.y), self.LINE_WIDTH)

        if self.DEBUG_TEXT:
            # pygame fonts can only render one line at a time
            lines = [
                f"Current Speed: {self.speed}",
                f"Angle Delta: {self.angle_delta}"
            ]
            for i, line in enumerate(lines):
                img = self.debug_font.render(line, True, (255, 255, 255))
                self.surface.blit(img, (10, i*20)) 