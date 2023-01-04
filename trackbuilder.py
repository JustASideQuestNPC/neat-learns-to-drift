import pygame as pg
from typing import List, Tuple
# Shapely is a library with a ton of very useful geometry tools
from shapely.geometry import LineString, Point, JOIN_STYLE
from shapely.ops import nearest_points
import json
from pathlib import Path

GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
LINE_WIDTH = 3
BORDER_OFFSET = 100

def compute_point_loop(points:List[Tuple[float,float]]) -> List[Tuple[float,float]]:
    newpoints = [i for i in points]
    mp = pg.mouse.get_pos()
    newpoints.append(mp)
    newpoints.append(newpoints[0])
    return newpoints

def draw_point_loop(surface:pg.surface.Surface, points:List[Tuple[float,float]],
            color:Tuple[int,int,int]) -> None:
    for i in range(0, len(points) - 1):
        pg.draw.line(surface, color, points[i], points[i + 1], LINE_WIDTH)

def generate_offset_loop(points:List[Tuple[float,float]],
            offset:float) -> List[Tuple[float,float]]:
    l_str = LineString(points)
    o_str = l_str.offset_curve(offset, join_style=JOIN_STYLE.bevel)
    return [i for i in o_str.coords]

def make_loop(line:LineString) -> LineString:
    points = [i for i in line.coords]
    points.append(points[0])
    return LineString(points)

def write_json(borders:Tuple[Tuple[float,float]], start_point:Tuple[float, float],
        checkpoints:List[Tuple[Tuple[float,float]]], finish_line:Tuple[Tuple[float,float]], path:str) -> None:
    track_data = {
        "inner border": borders[0],
        "outer border": borders[1],
        "start point": start_point,
        "checkpoints": checkpoints,
        "finish line": finish_line
    }
    with open(Path(path), 'r') as tracks_raw:
        tracks = json.load(tracks_raw)
        tracks.append(track_data)

    with open(Path(path), 'w') as tracks_raw:
        json.dump(tracks, tracks_raw)
        print("write successful")


window = pg.display.set_mode((1080, 720))
pg.display.init()
pg.display.update()

clock = pg.time.Clock()

# NOTE: "inner" and "outer" are only used because
# they make sense as names for the two borders.
# The "inner" loop will end up on the outside
# of the track in a lot of cases (not that it matters).
midline_points = LineString()
inner_points = LineString()
outer_points = LineString()
midline_point_loop = []
start_point = ()
checkpoints = []

# Used for displaying track loops and checkpoints
midline_display_loop = midline_point_loop
outer_display_loop = []
inner_display_loop = []
preview_cp = ()

# Used for testing if the track is valid (does not self-intersect)
test_points = LineString()

# Used when placing checkpoints and the starting point
closest_midline_point = ()

track_valid = True
update_display = False

builder_state = "track"

running = True
while running:
    clock.tick(100)
    mouse_pos = pg.mouse.get_pos()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

        # Update the loops when the mouse is being moved
        # and the track is being drawn
        if event.type == pg.MOUSEMOTION:
            update_display = True

        if event.type == pg.MOUSEBUTTONDOWN:
            if builder_state == "track":
                # Add a point if the left mouse is pressed
                if event.button == 1 and track_valid:
                    midline_point_loop.append(mouse_pos)
                    if len(midline_point_loop) > 1:
                        midline_points = LineString(midline_point_loop)
                    if len(midline_display_loop) > 3:
                        temploop = midline_display_loop + midline_display_loop[:2]
                        outer_points = LineString(generate_offset_loop(temploop, BORDER_OFFSET / 2))
                        inner_points = LineString(generate_offset_loop(temploop, -BORDER_OFFSET / 2))
                # Remove the last point if right mouse is pressed
                elif event.button == 3 and len(midline_point_loop) >= 1:
                    if len(midline_point_loop) == 1:
                        midline_point_loop = []
                    else:
                        midline_point_loop.pop(-1)
                    if len(midline_point_loop) > 1:
                        midline_points = LineString(midline_point_loop)
                    if len(display_loop) > 3:
                        temploop = midline_display_loop + midline_display_loop[:2]
                        outer_points = LineString(generate_offset_loop(temploop, BORDER_OFFSET / 2))
                        inner_points = LineString(generate_offset_loop(temploop, -BORDER_OFFSET / 2))

                display_loop = compute_point_loop(midline_point_loop)
                update_display = True
            elif builder_state == "start point":
                builder_state = "checkpoints"
            elif builder_state == "checkpoints":
                checkpoints.append(preview_cp)

        # If the enter key is pressed, move to the next step of the process
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN:
                if builder_state == "track":
                    builder_state = "start point"
                    update_display = True
                elif builder_state == "checkpoints":
                    start = Point(start_point)
                    fp_point1 = nearest_points(make_loop(outer_points), start)[0]
                    fp_point2 = nearest_points(make_loop(inner_points), start)[0]
                    finish_line = ((fp_point1.x, fp_point1.y), (fp_point2.x, fp_point2.y))
                    write_json((inner_display_loop[0:-1], outer_display_loop[0:-1]),
                                start_point, checkpoints, finish_line, "data/tracks.json")
                    running = False

    if update_display:
        if builder_state == "track":
            # Update display loops to add mouse position
            display_loop = compute_point_loop(midline_point_loop)
            if len(display_loop) >= 2:
                temploop = display_loop + display_loop[:2]
                outer_display_loop = generate_offset_loop(temploop, BORDER_OFFSET / 2)
                inner_display_loop = generate_offset_loop(temploop, -BORDER_OFFSET / 2)

            if len(display_loop) > 3:
                test_points = LineString(display_loop)

            # Check if the track intersects itself
            track_valid = test_points.is_simple
        else:
            outer_display_loop = [i for i in outer_points.coords]
            inner_display_loop = [i for i in inner_points.coords]

            mp = Point(mouse_pos)
            cmp = nearest_points(make_loop(midline_points), mp)[0]
            closest_midline_point = (cmp.x, cmp.y)
        if builder_state == "start point":
            start_point = closest_midline_point
        elif builder_state == "checkpoints":
            midpoint = Point(closest_midline_point)
            cp_point1 = nearest_points(make_loop(outer_points), midpoint)[0]
            cp_point2 = nearest_points(make_loop(inner_points), midpoint)[0]
            preview_cp = ((cp_point1.x, cp_point1.y), (cp_point2.x, cp_point2.y))
        
    # Refresh the display
    window.fill(GRAY)

    draw_point_loop(window, inner_display_loop, WHITE if track_valid else RED)
    draw_point_loop(window, outer_display_loop, WHITE if track_valid else RED)

    if builder_state != "track":
        pg.draw.circle(window, GREEN, start_point, 5)
    if builder_state == "checkpoints":
        for cp in checkpoints:
            pg.draw.line(window, RED, cp[0], cp[1], LINE_WIDTH)
        pg.draw.line(window, RED, preview_cp[0], preview_cp[1], LINE_WIDTH)
    
    pg.display.flip()

    moved = False