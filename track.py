import pygame as pg
from typing import Tuple, Dict, List
from ast import literal_eval
from math import degrees, atan2
# Shapely is a library with a ton of very useful geometry tools
from shapely import LineString, Polygon, LinearRing
# I know there's an official python library for this (configparser), but configobj has more options and supports things like nested config sections.
from configobj import ConfigObj
cfg = ConfigObj("config.txt")["TRACKS"]

class Track:
    
    (LINE_WIDTH,
     SHOW_CHECKPOINTS,
     SHOW_COLLISIONS,
     BORDER_COLOR,
     BORDER_COLLIDE_COLOR,
     CHECKPOINT_COLOR,
     CHECKPOINT_COLLIDE_COLOR,
     FINISH_LINE_COLOR,
     FINISH_LINE_COLLIDE_COLOR) = [literal_eval(value) for _, value in cfg.items()]

    def __init__(self, surface:pg.surface.Surface, surface_size:Tuple[int,int], track:Dict,) -> None:
        self.surface = surface
        self.surface_size = surface_size  # Used for collision
        self.inner_border = track["inner border"]  # List of tuples
        self.outer_border = track["outer border"]  # List of tuples
        self.start_point = track["start point"]    # Tuple
        self.checkpoints = track["checkpoints"]    # List of tuples of tuples
        self.finish_line = track["finish line"]    # Tuple of tuples
        self.__create_geometries()
        # Borders and checkpoints that are CURRENTLY being collided with
        self.outer_border_collision = False
        self.inner_border_collision = False
        self.checkpoint_collisions = []
        self.finish_line_collision = False

    # Converts lists of points into shapely geometries
    def __create_geometries(self) -> None:
        # Swaps the inner and outer borders if necessary so that the outer
        # border geometry is actually on the outside of the track.
        inner_test = Polygon(self.inner_border)
        outer_test = Polygon(self.outer_border)
        if outer_test.contains(inner_test):
            self.outer_border_geometry = LinearRing(self.outer_border)
            self.inner_border_geometry = LinearRing(self.inner_border)
        else:
            self.outer_border_geometry = LinearRing(self.inner_border)
            self.inner_border_geometry = LinearRing(self.outer_border)
            self.outer_border = self.outer_border_geometry.coords
            self.inner_border = self.inner_border_geometry.coords
        

        self.checkpoint_geometries = [LineString(i) for i in self.checkpoints]
        self.finish_line_geometry = LineString(self.finish_line)

        # Find starting angle for the start point
        self.cp_midpoints = [self.checkpoint_geometries[i].interpolate(0.5, True)
                        for i in range(len(self.checkpoint_geometries))]
        midpoint_coords = self.cp_midpoints[0].coords[0]
        self.start_angle = degrees(atan2(
            midpoint_coords[0] - self.start_point[0],
            midpoint_coords[1] - self.start_point[1]
        ))

    # Takes a tuple containing each checkpoint a car has passed,
    # and returns all the checkpoints it hasn't passed, with
    # their midpoints included. Used for AI training.
    def get_unpassed_checkpoints(self, passed:List[int]) -> List:
        unpassed = [(self.checkpoints[i], self.cp_midpoints[i])
                for i in range(len(self.checkpoints))]

        # The cars don't store the coordinates of the checkpoints they've
        # passed, only the indices of those checkpoints in the track's
        # checkpoint list. Apparently, this was a much better solution
        # than I first thought.
        for i in passed:
            if i < len(unpassed):
                unpassed.pop(i)

        return unpassed

    # Checks for collisions and checkpoint passes
    def collide(self, box:Tuple, passed_checkpoints:List) -> Tuple:
        hitbox = Polygon(box)
        border_collision = False
        new_checkpoint = -1  # Which checkpoint the car has passed for the first time, if any.
        new_lap = False

        self.inner_border_collision = False
        if hitbox.intersects(self.inner_border_geometry):
            border_collision = True
            self.inner_border_collision = True
        
        self.outer_border_collision = False
        if hitbox.intersects(self.outer_border_geometry):
            border_collision = True
            self.outer_border_collision = True

        self.checkpoint_collisions = []
        for i, geo in enumerate(self.checkpoint_geometries):
            if hitbox.intersects(geo):
                self.checkpoint_collisions.append(i)
                if i not in passed_checkpoints:
                    new_checkpoint = i

        self.finish_line_collision = False
        if hitbox.intersects(self.finish_line_geometry):
            self.finish_line_collision = True
            if len(self.checkpoints) == len(passed_checkpoints): # This *should* ensure every checkpoint has been passed before starting a new lap
                new_lap = True
                new_checkpoint = len(self.checkpoints) # The finish line is *technically* a checkpoint too
        
        return (border_collision, new_checkpoint, new_lap)

    def display(self) -> None:
        if self.SHOW_CHECKPOINTS:
            finish_color = self.FINISH_LINE_COLOR
            if self.finish_line_collision and self.SHOW_COLLISIONS:
                finish_color = self.FINISH_LINE_COLLIDE_COLOR
            pg.draw.line(self.surface, finish_color, self.finish_line[0],
                        self.finish_line[1], self.LINE_WIDTH)

            for i, cp in enumerate(self.checkpoints):
                cp_color = self.CHECKPOINT_COLOR
                if i in self.checkpoint_collisions and self.SHOW_COLLISIONS:
                    cp_color = self.CHECKPOINT_COLLIDE_COLOR
                pg.draw.line(self.surface, cp_color, cp[0], cp[1], self.LINE_WIDTH)

        inner_color = self.BORDER_COLOR
        if self.inner_border_collision and self.SHOW_COLLISIONS:
            inner_color = self.BORDER_COLLIDE_COLOR
        pg.draw.lines(self.surface, inner_color, True, self.inner_border, self.LINE_WIDTH)

        outer_color = self.BORDER_COLOR
        if self.outer_border_collision and self.SHOW_COLLISIONS:
            outer_color = self.BORDER_COLLIDE_COLOR
        pg.draw.lines(self.surface, outer_color, True, self.outer_border, self.LINE_WIDTH)