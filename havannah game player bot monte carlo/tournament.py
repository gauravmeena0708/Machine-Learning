import os
import time
import json
import random
import argparse
import multiprocessing as mp
import pandas as pd
from datetime import datetime
from multiprocessing import Value
from threading import Thread
from typing import Tuple, Callable, Dict
import numpy as np
import tkinter as tk

# Local imports
from helper import get_valid_actions, check_win, HEXAGON_COORDS, CLICK_EVENT, PLAYER_TIME

# Import Players
# Import Players
from players.ai01 import AIPlayer as AIPlayer01
from players.ai02 import AIPlayer as AIPlayer02
from players.ai03 import AIPlayer as AIPlayer03
from players.ai04 import AIPlayer as AIPlayer04
from players.ai05 import AIPlayer as AIPlayer05
from players.ai06 import AIPlayer as AIPlayer06
from players.ai07 import AIPlayer as AIPlayer07
from players.ai08 import AIPlayer as AIPlayer08
from players.ai09 import AIPlayer as AIPlayer09
from players.ai10 import AIPlayer as AIPlayer10
from players.ai11 import AIPlayer as AIPlayer11
from players.ai12 import AIPlayer as AIPlayer12
from players.ai13 import AIPlayer as AIPlayer13
from players.random import RandomPlayer
from players.human import HumanPlayer


TimeLimitExceedAction = (1000, True)


def turn_worker(state: np.array, send_end, p_func: Callable[[np.array], Tuple[int, bool]], PLAYER_TIME):
    send_end.send(p_func(state, PLAYER_TIME))

def make_player(name, num, timer=PLAYER_TIME):
    if name == 'ai01':
        return AIPlayer01(num, timer)
    elif name == 'ai02':
        return AIPlayer02(num, timer)
    elif name == 'ai03':
        return AIPlayer03(num, timer)
    elif name == 'ai04':
        return AIPlayer04(num, timer)
    elif name == 'ai05':
        return AIPlayer05(num, timer)
    elif name == 'ai06':
        return AIPlayer06(num, timer)
    elif name == 'ai07':
        return AIPlayer07(num, timer)
    elif name == 'ai08':
        return AIPlayer08(num, timer)
    elif name == 'ai09':
        return AIPlayer09(num, timer)
    elif name == 'ai10':
        return AIPlayer10(num, timer)
    elif name == 'ai11':
        return AIPlayer11(num, timer)
    elif name == 'ai12':
        return AIPlayer12(num, timer)
    elif name == 'ai13':
        return AIPlayer13(num, timer)
    elif name == 'random':
        return RandomPlayer(num, timer)
    elif name == 'human':
        return HumanPlayer(num, timer)

class Game:
    def __init__(self, player1_name, player2_name, player1, player2, time: int, board_init: np.array, layers: int, mode: str):
        self.players = [player1, player2]
        self.colors = ['', 'yellow', 'red', 'black']
        self.layers = layers
        self.state = board_init
        self.gui_board = []
        PLAYER_TIME[0] = time
        PLAYER_TIME[1] = time
        self.use_gui = mode == "gui"
        self.structure_formed = None
        self.winning_path = []
        self.winner = None
        board = self.state

        self.current_turn = Value('i', 0)
        self.game_over = Value('b', False)
        self.pause_timer = Value('b', True)

        if self.use_gui:
            self.init_gui(player1, player2)

        self.parent_conn, self.child_conn = mp.Pipe()
        self.proc = mp.Process(target=self.player_workers, args=(make_player, self.game_over, self.child_conn, player1_name, player2_name, PLAYER_TIME))
        self.proc.start()

        # Wait for the game process to finish
        self.proc.join()

        # Record the winner
        if self.game_over.value:
            self.winner = 2 - self.current_turn.value

        # Clean up
        self.parent_conn.close()
        self.child_conn.close()

        # Process termination in Windows
        if self.proc.is_alive():
            self.proc.terminate()
        self.proc.close()

    def init_gui(self, player1, player2):
        root = tk.Tk()
        root.title('Extended Havannah')

        self.current = tk.Label(root, text="Current:")
        self.current.pack()

        player1_string = f"{player1.player_string} (Yellow) | Time Remaining {PLAYER_TIME[0]:.2f} s"
        self.player1_string = tk.Label(root, text=player1_string, anchor="w", width=50)
        self.player1_string.pack()

        player2_string = f"{player2.player_string} (Red)    | Time Remaining {PLAYER_TIME[1]:.2f} s"
        self.player2_string = tk.Label(root, text=player2_string, anchor="w", width=50)
        self.player2_string.pack()

        self.scale = 1
        height = (25 * np.sqrt(3) * (2 * self.layers - 1)) * self.scale
        width = (75 * self.layers - 25) * self.scale
        self.c = tk.Canvas(root, height=height, width=width)
        self.c.pack()
        for j in range(2 * self.layers - 1):
            column = []
            col_size = self.layers
            if j < self.layers:
                col_size += j
            else:
                col_size += 2 * self.layers - 2 - j

            for i in range(col_size):
                hex_coords = self.calculate_hexagon(i, j, 25, self.scale)
                c = self.state[i][j]
                self.display_coordinates(hex_coords, i, j)
                hexagon_id = self.c.create_polygon(hex_coords, fill=self.colors[c], outline="black")
                HEXAGON_COORDS[hexagon_id] = (i, j)
                column.append(hexagon_id)
                self.c.tag_bind(hexagon_id, "<Button-1>", self.on_click)
            self.gui_board.append(column)

        timer = Thread(target=self.display_time, args=(self.game_over,))
        timer.start()
        root.mainloop()

    def calculate_hexagon(self, i, j, size, scale=1):
        sqrt3 = np.sqrt(3)
        offset_x = j * size * 3 / 2
        offset_y = (abs(j - self.layers + 1) + 2 * i) * size * sqrt3 / 2
        return [
            ((size / 2 + offset_x) * scale, offset_y * scale),
            ((size * 3 / 2 + offset_x) * scale, offset_y * scale),
            ((size * 2 + offset_x) * scale, (size * sqrt3 / 2 + offset_y) * scale),
            ((size * 3 / 2 + offset_x) * scale, (size * sqrt3 + offset_y) * scale),
            ((size / 2 + offset_x) * scale, (size * sqrt3 + offset_y) * scale),
            (offset_x * scale, (size * sqrt3 / 2 + offset_y) * scale)
        ]

    def display_coordinates(self, hex_coords, i, j):
        x = sum([point[0] for point in hex_coords]) / 6
        y = sum([point[1] for point in hex_coords]) / 6
        self.c.create_text(x, y, text=f"({i},{j})", fill="black")

    def player_workers(self, make_player, game_over, pipe_conn, player1, player2, timer):
        players = [make_player(player1, 1, timer), make_player(player2, 2, timer)]
        while not game_over.value:
            current_turn, state = pipe_conn.recv()
            move = players[current_turn].get_move(state)
            pipe_conn.send(move)

def get_random_board(layers: int, blocks: int):
    assert layers > 1
    board = np.zeros([2 * layers - 1, 2 * layers - 1]).astype(np.uint8)
    for i in range(layers, 2 * layers - 1, 1):
        for j in range(0, i - layers + 1, 1):
            board[i][j] = 3
            board[i][2 * layers - 2 - j] = 3
    rand_x = np.random.randint(0, 2 * layers - 1, blocks)
    for x in rand_x:
        if x >= layers:
            y = np.random.randint(x - layers + 1, 3 * layers - 2 - x)
        else:
            y = np.random.randint(0, 2 * layers - 1)
        board[x][y] = 3
    return board


def get_start_board(file_pth: str) -> Tuple[int, np.array]:
    b = []
    file_pth = os.path.join('havannah', 'initial_states', file_pth)
    with open(file_pth) as f:
        for line in f:
            line = line.strip()
            row = [int(ch) for ch in line.split(' ')]
            b.append(row)
    board = np.array(b, dtype=int)
    return board
    
def run_tournament():
    ai_bots = [f'ai{str(i).zfill(2)}' for i in range(1, 14)]
    results = []
    player1, player2 = ai_bots[0], ai_bots[1]
    dim = 4
    blocks = 0
    board = get_random_board(dim, blocks)
    
    print(f"Starting match between {player1} and {player2}")
    
    try:
        game = Game(player1, player2, make_player(player1, 1), make_player(player2, 2), 240, board, 4, "server")  # Use "server" mode to avoid GUI issues
        winner = game.winner
        print(f"{player1} vs {player2}, winner: {winner}")
        results.append({
            'Match': f'{player1} vs {player2}',
            'Winner': f'{player1}' if winner == 1 else f'{player2}',
            'Winning_Structure': game.structure_formed
        })
    except Exception as e:
        print(f"An error occurred: {e}")
    
    df_results = pd.DataFrame(results)
    df_results.to_excel('tournament_results.xlsx', index=False)
    print("Tournament completed. Results saved to 'tournament_results.xlsx'.")

if __name__ == '__main__':
    run_tournament()


if __name__ == '__main__':
    run_tournament()

