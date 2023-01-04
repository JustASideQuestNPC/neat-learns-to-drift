import pygame as pg
from shapely.geometry import LineString, Point, LinearRing
from shapely.affinity import rotate, translate
from typing import Tuple
# I know there's an official python library for this (configparser), but configobj has more options and supports things like nested config sections.
from configobj import ConfigObj
from ast import literal_eval
r_cfg = ConfigObj("config.txt")["RAYCASTING"]


class Ray:
    (CAST_LENGTH,
     TRUNCATE_RAY,
     RAY_COLOR,
     RAY_WIDTH,
     SHOW_INTERSECTION,
     INTERSECT_RADIUS,
     INTERSECT_COLOR,
     SHOW_DISTANCE,
     DISTANCE_DECIMALS) = [literal_eval(value) for _, value in r_cfg.items()]
    
    # String operator for rounding to a specified number of decimal places
    ROUNDING_STRING = f'%.{DISTANCE_DECIMALS}f'

    BASE_LINE = LineString(((0, 0), (0, CAST_LENGTH)))  # This is copied and moved to create the rays used for casting.
    def __init__(self, surface:pg.surface.Surface, font:pg.font.SysFont, origin:Tuple[float,float], angle:float) -> None:
        self.surface = surface
        self.font = font
        self.origin = Point(origin)
        self.angle = angle
        self.last_distance = None
        self.last_intersection = None
        self.__update_ray()

    def __update_ray(self) -> None:
        rotated_ray = rotate(self.BASE_LINE, self.angle, (0, 0))
        self.ray = translate(rotated_ray, self.origin.coords[0][0], self.origin.coords[0][1])

    # Returns a tuple containing the distance at which the ray intersects
    # with the geometry, as well as the coordinates of the point of intersection.
    # If there is no intersection, it returns the maximum cast distance, and the point (0, 0)
    def cast(self, geometry) -> Tuple:
        self.last_intersection = None
        self.last_distance = self.CAST_LENGTH
        if self.ray.intersects(geometry):
            intersection_point = self.ray.intersection(geometry)
            
            if type(intersection_point) == Point:
                distance = self.origin.distance(intersection_point)
                self.last_distance = distance
                self.last_intersection = intersection_point.coords[0]
                return (distance, intersection_point.coords[0])
            else:
                intersections = list(intersection_point.geoms)
                distances = [self.origin.distance(pt) for pt in intersections]
                closest_index = min(range(len(distances)), key=distances.__getitem__)
                closest = intersections[closest_index]
                self.last_intersection = closest.coords[0]
                self.last_distance = self.origin.distance(closest)
                return (self.origin.distance(closest), closest.coords[0])
                
        else:
            return (-1, (0, 0))

    # Casts to multiple geometries, and returns the distance to the closest intersection with any of them.
    def multi_cast(self, geometries:Tuple) -> Tuple:
        closest_point = (0, 0)
        closest_distance = self.CAST_LENGTH
        for geo in geometries:
            point = self.cast(geo)
            if point[0] < closest_distance and point[0] > 0:
                closest_distance = point[0]
                closest_point = point[1]

        if closest_distance == self.CAST_LENGTH:
            self.last_distance = self.CAST_LENGTH
            self.last_intersection = None
            return(-1, (0, 0))
        else:
            self.last_distance = closest_distance
            self.last_intersection = closest_point
            return (closest_distance, closest_point)


    def display(self) -> None:
        if self.TRUNCATE_RAY and self.last_intersection != None:
            pg.draw.line(self.surface, self.RAY_COLOR, self.ray.coords[0], self.last_intersection, self.RAY_WIDTH)
        else:
            pg.draw.line(self.surface, self.RAY_COLOR, self.ray.coords[0], self.ray.coords[1], self.RAY_WIDTH)

        if self.SHOW_INTERSECTION and self.last_intersection != None:
            pg.draw.circle(self.surface, self.INTERSECT_COLOR, self.last_intersection, self.INTERSECT_RADIUS)
            if self.SHOW_DISTANCE and self.last_distance != self.CAST_LENGTH:
                img = self.font.render(self.ROUNDING_STRING % self.last_distance, True, self.INTERSECT_COLOR)
                self.surface.blit(img, (self.last_intersection[0] + 10, self.last_intersection[1]))


    def set_angle(self, new_angle:float, relative:bool=False) -> None:
        if relative:
            self.angle += new_angle
        else:
            self.angle = new_angle
        self.__update_ray()

    def set_origin(self, new_origin:Tuple[float, float], relative:bool=False) -> None:
        if relative:
            old_origin = self.origin.coords
            self.origin = Point((old_origin[0] + new_origin[0], old_origin[1] + new_origin[1]))
        else:
            self.origin = Point(new_origin)
        self.__update_ray()