import time
import random
from itertools import cycle

import asyncio
import curses

import curses_tools
import physics
import obstacles
import explosion
import game_scenario


TIC_TIMEOUT = 0.1

COROUTINES = []

OBSTACLES = []

OBSTACLES_IN_LAST_COLLISIONS = set()

YEAR = 1957


async def sleep(tics=1):
    for i in range(tics):
        await asyncio.sleep(0)


async def blink(canvas, row, column, offset_tics, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(offset_tics[0])

        canvas.addstr(row, column, symbol)
        await sleep(offset_tics[1])

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(offset_tics[2])

        canvas.addstr(row, column, symbol)
        await sleep(offset_tics[3])


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await sleep()

    canvas.addstr(round(row), round(column), 'O')
    await sleep()
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await sleep()
        canvas.addstr(round(row), round(column), ' ')
        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column):
                OBSTACLES_IN_LAST_COLLISIONS.add(obstacle)
                return
        row += rows_speed
        column += columns_speed


async def show_gameover(canvas, row, column, game_over):
    while True:
        curses_tools.draw_frame(canvas, row, column, game_over)
        await sleep()


async def animate_spaceship(canvas, row, column, ship_slides, game_over):
    row_speed = column_speed = 0
    for slide in cycle(ship_slides):        
        height, width = canvas.getmaxyx()
        rows_direction, columns_direction, space_pressed = curses_tools.read_controls(canvas)
        row_speed, column_speed = physics.update_speed(row_speed, column_speed, rows_direction, columns_direction)
        
        row += row_speed
        row = min(row, height - 11)
        row = max(row, 1)

        column += column_speed
        column = min(column, width - 8)
        column = max(column, 3)

        column_fire = column + 2

        if YEAR > 2019 and space_pressed:
            COROUTINES.append(fire(canvas, row, column_fire))

        for obstacle in OBSTACLES:
            crash = obstacles.has_collision(
                (obstacle.get_bounding_box_corner_pos()),   # верхний левый угол препятствия
                (obstacle.rows_size, obstacle.columns_size),     # размер препятствия
                (row, column),   # верхний левый угол второго объекта
            )
            if crash:
                row = height / 2 - 2
                column = width / 2 - 27
                await show_gameover(canvas, row, column, game_over)
                return
        
        curses_tools.draw_frame(canvas, row, column, slide)
        await sleep()
        curses_tools.draw_frame(canvas, row, column, slide, True)
        curses_tools.draw_frame(canvas, row, column, slide)
        await sleep()
        curses_tools.draw_frame(canvas, row, column, slide, True)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    row_size, column_size = curses_tools.get_frame_size(garbage_frame)

    while row < rows_number:
        obstacle = obstacles.Obstacle(row, column, row_size, column_size)
        OBSTACLES.append(obstacle)
        curses_tools.draw_frame(canvas, row, column, garbage_frame)
        await sleep()
        OBSTACLES.pop(0)
        curses_tools.draw_frame(canvas, row, column, garbage_frame, negative=True)
        if obstacle in OBSTACLES_IN_LAST_COLLISIONS:
            OBSTACLES_IN_LAST_COLLISIONS.remove(obstacle)
            center_row = row + obstacle.rows_size / 2
            center_column = column + obstacle.columns_size / 2
            await explosion.explode(canvas, center_row, center_column)
            return
        row += speed


async def fill_orbit_with_garbage(canvas, garbage, max_column):
    while not game_scenario.get_garbage_delay_tics(YEAR):
        await sleep()
    for garbage_frame in cycle(garbage):
        garbage_column = random.randint(1, max_column)
        COROUTINES.append(fly_garbage(canvas, garbage_column, garbage_frame))
        await sleep(game_scenario.get_garbage_delay_tics(YEAR))


async def game_progress(canvas_year, year_row, year_column):
    global YEAR
    while True:
        text = f"Year {YEAR} {game_scenario.PHRASES.get(YEAR, "")}"
        canvas_year.addstr(0, 0, text)
        canvas_year.refresh()
        await sleep(15)
        canvas_year.erase()
        canvas_year.refresh()
        YEAR += 1


def draw(canvas):
    canvas.nodelay(True)
    canvas.border()
    curses.curs_set(False)
    
    height, width = canvas.getmaxyx()
    max_row, max_column = height - 2, width - 2
    
    year_row_size, year_column_size = 2, 30
    year_row = height - year_row_size - 1
    year_column = width - year_column_size - 2
    canvas_year = canvas.derwin(year_row_size, year_column_size, year_row, year_column)
    
    with open("ship.txt", "r", encoding="UTF-8") as ship_file:
        ship = ship_file.read()
    ship_slides = ship.split("\n\n")
    
    center_row, center_column = height // 2, width // 2

    with open('garbage.txt', "r", encoding="UTF-8") as garbage_file:
        garbage = garbage_file.read()
    garbage = garbage.split("\n\n")

    with open('game_over.txt', "r", encoding="UTF-8") as game_over_file:
        game_over = game_over_file.read()

    COROUTINES.append(fill_orbit_with_garbage(canvas, garbage, max_column))
    COROUTINES.append(animate_spaceship(canvas, center_row, center_column, ship_slides, game_over))
    COROUTINES.append(game_progress(canvas_year, year_row, year_column))
    
    for i in range(160):
        offset_tics = [
            random.randint(0, 20),
            random.randint(0, 3),
            random.randint(0, 5),
            random.randint(0, 3),
        ]
        row = random.randint(1, max_row)
        star_column = random.randint(1, max_column)
        star = random.choice('+*.:')
        COROUTINES.append(blink(canvas, row, star_column, offset_tics, star))

    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)   
        canvas.refresh() 
        time.sleep(TIC_TIMEOUT)
  

if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)