import time
import random
from itertools import cycle

import asyncio
import curses

import curses_tools


TIC_TIMEOUT = 0.1


async def blink(canvas, row, column, offset_tics, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for i in range(offset_tics[0]):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(offset_tics[1]):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for i in range(offset_tics[2]):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(offset_tics[3]):
            await asyncio.sleep(0)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(canvas, row, column, ship_slides):
    for slide in cycle(ship_slides):
        height, width = canvas.getmaxyx()
        rows_direction, columns_direction, space_pressed = curses_tools.read_controls(canvas)
        
        row += rows_direction
        row = min(row, height - 11)
        row = max(row, 1)

        column += columns_direction
        column = min(column, width - 8)
        column = max(column, 3)
        
        curses_tools.draw_frame(canvas, row, column, slide)
        for i in range(2):
            await asyncio.sleep(0)
        curses_tools.draw_frame(canvas, row, column, slide, True)


def draw(canvas):
    canvas.nodelay(True)
    canvas.border()
    curses.curs_set(False)
    
    height, width = canvas.getmaxyx()
    with open("ship.txt", "r", encoding="UTF-8") as my_file:
        ship = my_file.read()
    ship_slides = ship.split("\n\n")
    
    coroutine_ship = animate_spaceship(canvas, height // 2, width // 2 - 2, ship_slides)
    coroutine_fire = fire(canvas, height // 2, width // 2)
    coroutines = [coroutine_fire, coroutine_ship]
    
    for i in range(160):
        offset_tics = [
            random.randint(0, 20),
            random.randint(0, 3),
            random.randint(0, 5),
            random.randint(0, 3),
        ]
        row = random.randint(1, height - 2)
        column = random.randint(1, width - 2)
        star = random.choice('+*.:')
        coroutines.append(blink(canvas, row, column, offset_tics, star))

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)   
        canvas.refresh() 
        time.sleep(TIC_TIMEOUT)
  

if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)