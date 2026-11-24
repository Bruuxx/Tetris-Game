import os
import random
import time
import tkinter as tk
from array import array

import customtkinter as ctk
import pygame

COLS, ROWS, CELL = 10, 20, 30
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL
PANEL_W = 140
SURF_W, SURF_H = BOARD_W + PANEL_W, BOARD_H

BG = (18, 18, 26)
GRID = (30, 30, 42)
WHITE = (240, 240, 240)

SHAPES = {
    "I": ([[1, 1, 1, 1]], (0, 216, 232)),
    "O": ([[1, 1], [1, 1]], (245, 217, 10)),
    "T": ([[0, 1, 0], [1, 1, 1]], (176, 79, 224)),
    "S": ([[0, 1, 1], [1, 1, 0]], (62, 207, 90)),
    "Z": ([[1, 1, 0], [0, 1, 1]], (232, 69, 60)),
    "J": ([[1, 0, 0], [1, 1, 1]], (61, 111, 240)),
    "L": ([[0, 0, 1], [1, 1, 1]], (242, 140, 30)),
}
LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


def rotate(matrix):
    return [list(row) for row in zip(*matrix[::-1])]


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over = False
        self.bag = []
        self.events = []
        self.fall_timer = 0.0
        self.next = self.new_piece()
        self.spawn()

    def new_piece(self):
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        shape, color = SHAPES[self.bag.pop()]
        return {"shape": [row[:] for row in shape], "color": color}

    def spawn(self):
        self.piece = self.next
        self.next = self.new_piece()
        self.px = COLS // 2 - len(self.piece["shape"][0]) // 2
        self.py = 0
        if not self.valid(self.piece["shape"], self.px, self.py):
            self.over = True
            self.events.append("over")

    def valid(self, shape, x, y):
        for r, row in enumerate(shape):
            for c, cell in enumerate(row):
                if not cell:
                    continue
                nx, ny = x + c, y + r
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return False
                if ny >= 0 and self.board[ny][nx]:
                    return False
        return True

    def interval(self):
        return max(80, 500 - (self.level - 1) * 40)

    def move(self, dx, dy):
        if self.over:
            return False
        if self.valid(self.piece["shape"], self.px + dx, self.py + dy):
            self.px += dx
            self.py += dy
            if dx:
                self.events.append("move")
            return True
        return False

    def rotate_piece(self):
        if self.over:
            return
        rotated = rotate(self.piece["shape"])
        for kick in (0, -1, 1, -2, 2):
            if self.valid(rotated, self.px + kick, self.py):
                self.piece["shape"] = rotated
                self.px += kick
                self.events.append("rotate")
                return

    def soft_drop(self):
        if self.over:
            return
        if self.move(0, 1):
            self.score += 1
        else:
            self.lock()

    def hard_drop(self):
        if self.over:
            return
        dist = 0
        while self.valid(self.piece["shape"], self.px, self.py + 1):
            self.py += 1
            dist += 1
        self.score += dist * 2
        self.lock()

    def ghost_y(self):
        gy = self.py
        while self.valid(self.piece["shape"], self.px, gy + 1):
            gy += 1
        return gy

    def lock(self):
        for r, row in enumerate(self.piece["shape"]):
            for c, cell in enumerate(row):
                if cell and self.py + r >= 0:
                    self.board[self.py + r][self.px + c] = self.piece["color"]
        self.events.append("lock")
        self.clear_lines()
        self.spawn()

    def clear_lines(self):
        remaining = [row for row in self.board if any(c is None for c in row)]
        cleared = ROWS - len(remaining)
        if cleared:
            self.board = [[None] * COLS for _ in range(cleared)] + remaining
            self.lines += cleared
            self.score += LINE_SCORES[cleared] * self.level
            self.level = self.lines // 10 + 1
            self.events.append("clear")

    def update(self, dt_ms):
        if self.over:
            return
        self.fall_timer += dt_ms
        if self.fall_timer >= self.interval():
            self.fall_timer = 0
            if not self.move(0, 1):
                self.lock()


def make_tone(freq, ms, volume=0.2, sweep=0.0):
    rate, _fmt, channels = pygame.mixer.get_init()
    n = int(rate * ms / 1000)
    amp = int(32767 * volume)
    buf = array("h")
    phase = 0.0
    for i in range(n):
        f = freq + sweep * (i / n)
        phase += f / rate
        value = amp if (phase % 1.0) < 0.5 else -amp
        fade = 1.0 - i / n
        for _ in range(channels):
            buf.append(int(value * fade))
    return pygame.mixer.Sound(buffer=buf.tobytes())


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Tetris (customtkinter + pygame)")
        self.resizable(False, False)

        self.game_frame = tk.Frame(self, width=SURF_W, height=SURF_H, bg="black")
        self.game_frame.grid(row=0, column=0, padx=15, pady=15)

        side = ctk.CTkFrame(self, corner_radius=12)
        side.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ns")

        self.score_label = ctk.CTkLabel(side, text="Score: 0", font=("Arial", 18, "bold"))
        self.score_label.pack(pady=(20, 4), padx=20)
        self.lines_label = ctk.CTkLabel(side, text="Lines: 0", font=("Arial", 16))
        self.lines_label.pack(pady=4)
        self.level_label = ctk.CTkLabel(side, text="Level: 1", font=("Arial", 16))
        self.level_label.pack(pady=4)

        ctk.CTkButton(side, text="New Game", command=self.new_game).pack(pady=(25, 5), padx=20)
        ctk.CTkButton(side, text="Pause (P)", command=self.toggle_pause).pack(pady=5, padx=20)
        self.sound_switch = ctk.CTkSwitch(side, text="Sound", command=self.refocus)
        self.sound_switch.select()
        self.sound_switch.pack(pady=15)

        ctk.CTkLabel(
            side,
            text="Controls\n← → move\n↑ rotate\n↓ soft drop\nSpace hard drop\nP pause",
            font=("Arial", 12), justify="left", text_color="gray70",
        ).pack(pady=(10, 20), padx=20)

        self.update()
        os.environ["SDL_WINDOWID"] = str(self.game_frame.winfo_id())
        if os.name == "nt":
            os.environ["SDL_VIDEODRIVER"] = "windows"
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((SURF_W, SURF_H))
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.big_font = pygame.font.SysFont("arial", 34, bold=True)

        self.sounds = {}
        try:
            pygame.mixer.init(22050, -16, 1)
            self.sounds = {
                "move": make_tone(500, 25),
                "rotate": make_tone(700, 40),
                "lock": make_tone(180, 70),
                "clear": make_tone(500, 260, sweep=700),
                "over": make_tone(400, 600, sweep=-300),
            }
        except Exception:
            self.sounds = {}

        self.bind("<Left>", lambda e: self.key(lambda: self.game.move(-1, 0)))
        self.bind("<Right>", lambda e: self.key(lambda: self.game.move(1, 0)))
        self.bind("<Down>", lambda e: self.key(self.game.soft_drop))
        self.bind("<Up>", lambda e: self.key(self.game.rotate_piece))
        self.bind("<space>", lambda e: self.key(self.game.hard_drop))
        self.bind("<p>", lambda e: self.toggle_pause())
        self.bind("<P>", lambda e: self.toggle_pause())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.game = Game()
        self.paused = False
        self.last_time = time.perf_counter()
        self._last_stats = None
        self.loop()
        self.refocus()

    def refocus(self):
        self.focus_set()

    def key(self, action):
        if not self.paused:
            action()
        return "break"

    def new_game(self):
        self.game.reset()
        self.paused = False
        self.last_time = time.perf_counter()
        self.refocus()

    def toggle_pause(self):
        if not self.game.over:
            self.paused = not self.paused
        self.refocus()

    def play_events(self):
        events, self.game.events = self.game.events, []
        if self.sound_switch.get():
            for name in events:
                sound = self.sounds.get(name)
                if sound:
                    sound.play()

    def loop(self):
        now = time.perf_counter()
        dt = (now - self.last_time) * 1000
        self.last_time = now

        if not self.paused:
            self.game.update(dt)
        self.play_events()
        self.draw()
        self.update_stats()

        pygame.event.pump()
        pygame.event.clear()
        self.after_id = self.after(16, self.loop)

    def update_stats(self):
        stats = (self.game.score, self.game.lines, self.game.level)
        if stats != self._last_stats:
            self._last_stats = stats
            self.score_label.configure(text=f"Score: {stats[0]}")
            self.lines_label.configure(text=f"Lines: {stats[1]}")
            self.level_label.configure(text=f"Level: {stats[2]}")

    def draw_cell(self, x, y, color, ghost=False):
        rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
        if ghost:
            pygame.draw.rect(self.screen, color, rect.inflate(-4, -4), width=2, border_radius=4)
        else:
            pygame.draw.rect(self.screen, color, rect.inflate(-2, -2), border_radius=4)
            highlight = tuple(min(255, c + 60) for c in color)
            pygame.draw.rect(self.screen, highlight, rect.inflate(-2, -2), width=2, border_radius=4)

    def draw(self):
        g = self.game
        s = self.screen
        s.fill(BG)

        for i in range(1, COLS):
            pygame.draw.line(s, GRID, (i * CELL, 0), (i * CELL, BOARD_H))
        for i in range(1, ROWS):
            pygame.draw.line(s, GRID, (0, i * CELL), (BOARD_W, i * CELL))
        pygame.draw.line(s, (60, 60, 80), (BOARD_W, 0), (BOARD_W, BOARD_H), 2)

        for r in range(ROWS):
            for c in range(COLS):
                if g.board[r][c]:
                    self.draw_cell(c, r, g.board[r][c])

        if not g.over:
            gy = g.ghost_y()
            for r, row in enumerate(g.piece["shape"]):
                for c, cell in enumerate(row):
                    if cell:
                        self.draw_cell(g.px + c, gy + r, g.piece["color"], ghost=True)
            for r, row in enumerate(g.piece["shape"]):
                for c, cell in enumerate(row):
                    if cell and g.py + r >= 0:
                        self.draw_cell(g.px + c, g.py + r, g.piece["color"])

        label = self.font.render("NEXT", True, WHITE)
        s.blit(label, (BOARD_W + (PANEL_W - label.get_width()) // 2, 20))
        shape = g.next["shape"]
        w, h = len(shape[0]) * CELL, len(shape) * CELL
        ox = BOARD_W + (PANEL_W - w) // 2
        oy = 70 + (4 * CELL - h) // 2
        for r, row in enumerate(shape):
            for c, cell in enumerate(row):
                if cell:
                    self.draw_cell((ox // CELL) + c + (ox % CELL) / CELL,
                                   (oy // CELL) + r + (oy % CELL) / CELL,
                                   g.next["color"])

        if g.over:
            self.overlay("GAME OVER")
        elif self.paused:
            self.overlay("PAUSED")

        pygame.display.flip()

    def overlay(self, text):
        band = pygame.Surface((BOARD_W, 80), pygame.SRCALPHA)
        band.fill((0, 0, 0, 170))
        self.screen.blit(band, (0, BOARD_H // 2 - 40))
        label = self.big_font.render(text, True, WHITE)
        self.screen.blit(label, ((BOARD_W - label.get_width()) // 2,
                                 BOARD_H // 2 - label.get_height() // 2))

    def on_close(self):
        self.after_cancel(self.after_id)
        pygame.quit()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()