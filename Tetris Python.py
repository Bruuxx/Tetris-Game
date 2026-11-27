import json
import os
import random
import time
import tkinter as tk
from array import array

import customtkinter as ctk
import pygame

COLS, ROWS = 10, 20
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tetris_data.json")

DAS_MS, ARR_MS, SOFT_MS = 150, 35, 40
LOCK_MS, MAX_LOCK_RESETS, CLEAR_MS = 500, 15, 450

NAVY, PANEL, BORDER = "#081a4d", "#0c2266", "#4d8dff"
BLUE, BLUE_HOVER, BLUE_EDGE = "#1f55e0", "#3a74ff", "#8fb8ff"
RED, RED_HOVER, RED_EDGE = "#c62828", "#e53935", "#ff9a94"
GOLD = "#ffd84d"

SHAPES = {
    "I": ([[1, 1, 1, 1]], (0, 216, 232)),
    "O": ([[1, 1], [1, 1]], (245, 217, 10)),
    "T": ([[0, 1, 0], [1, 1, 1]], (176, 79, 224)),
    "S": ([[0, 1, 1], [1, 1, 0]], (62, 207, 90)),
    "Z": ([[1, 1, 0], [0, 1, 1]], (232, 69, 60)),
    "J": ([[1, 0, 0], [1, 1, 1]], (61, 111, 240)),
    "L": ([[0, 0, 1], [1, 1, 1]], (242, 140, 30)),
}
KICKS = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
CLEAR_NAMES = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "TETRIS!"}

ACTIONS = [
    ("left", "Move left"), ("right", "Move right"), ("soft", "Soft drop"), ("hard", "Hard drop"),
    ("rotate_cw", "Rotate right"), ("rotate_ccw", "Rotate left"), ("hold", "Hold piece"), ("pause", "Pause"),
]
DEFAULT_KEYS = {
    "left": "a", "right": "d", "soft": "s", "hard": "space",
    "rotate_cw": "w", "rotate_ccw": "v", "hold": "c", "pause": "escape",
}

GLYPHS = {
    "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
    "E": ["#####", "#....", "####.", "#....", "#####"],
    "R": ["####.", "#...#", "####.", "#..#.", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "#####"],
    "S": [".####", "#....", ".###.", "....#", "####."],
}
TITLE_COLORS = [(229, 57, 53), (242, 140, 30), (245, 217, 10), (62, 207, 90), (0, 216, 232), (176, 79, 224)]


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


def pretty(key):
    names = {"space": "SPACE", "escape": "ESC", "return": "ENTER", "shift_l": "L-SHIFT",
             "shift_r": "R-SHIFT", "control_l": "L-CTRL", "control_r": "R-CTRL", "tab": "TAB"}
    return names.get(key, key.upper())


def rot_cw(m):
    return [list(r) for r in zip(*m[::-1])]


def rot_ccw(m):
    return [list(r) for r in zip(*m)][::-1]


def load_data():
    data = {"nickname": "", "volume": 60, "keys": dict(DEFAULT_KEYS), "players": {}}
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        for k in data:
            if k in saved:
                data[k] = saved[k]
        data["keys"] = {**DEFAULT_KEYS, **data["keys"]}
        data["volume"] = max(0, min(100, int(data["volume"])))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return data


def save_data(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def make_tone(freq, ms, volume=0.25, sweep=0.0):
    rate, _fmt, channels = pygame.mixer.get_init()
    n = int(rate * ms / 1000)
    amp = int(32767 * volume)
    buf = array("h")
    phase = 0.0
    for i in range(n):
        phase += (freq + sweep * (i / n)) / rate
        value = amp if (phase % 1.0) < 0.5 else -amp
        for _ in range(channels):
            buf.append(int(value * (1.0 - i / n)))
    return pygame.mixer.Sound(buffer=buf.tobytes())


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.score = self.lines = 0
        self.level = 1
        self.over = False
        self.bag, self.queue = [], []
        self.hold, self.can_hold = None, True
        self.events, self.popup = [], None
        self.clearing, self.clear_t = [], 0.0
        self.das_dir, self.das_t, self.arr_t, self.soft_t = 0, 0.0, 0.0, 0.0
        self.piece = None
        self.fill_queue()
        self.spawn(self.pop_next())

    def fill_queue(self):
        while len(self.queue) < 6:
            if not self.bag:
                self.bag = list(SHAPES)
                random.shuffle(self.bag)
            self.queue.append(self.bag.pop())

    def pop_next(self):
        name = self.queue.pop(0)
        self.fill_queue()
        return name

    def spawn(self, name):
        shape, color = SHAPES[name]
        self.piece = {"name": name, "shape": [r[:] for r in shape], "color": color}
        self.px = COLS // 2 - len(shape[0]) // 2
        self.py = 0
        self.fall_t = self.lock_t = 0.0
        self.resets, self.lowest = 0, 0
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

    def active(self):
        return not self.over and not self.clearing and self.piece is not None

    def interval(self):
        return max(50, int(600 * 0.85 ** (self.level - 1)))

    def grounded(self):
        return not self.valid(self.piece["shape"], self.px, self.py + 1)

    def bump_lock(self):
        if self.grounded() and self.resets < MAX_LOCK_RESETS:
            self.lock_t = 0.0
            self.resets += 1

    def move(self, dx):
        if not self.active() or not self.valid(self.piece["shape"], self.px + dx, self.py):
            return False
        self.px += dx
        self.events.append("move")
        self.bump_lock()
        return True

    def down(self, points=0):
        if not self.active() or not self.valid(self.piece["shape"], self.px, self.py + 1):
            return False
        self.py += 1
        self.score += points
        if self.py > self.lowest:
            self.lowest, self.resets = self.py, 0
        return True

    def rotate(self, cw=True):
        if not self.active():
            return False
        rotated = rot_cw(self.piece["shape"]) if cw else rot_ccw(self.piece["shape"])
        for dx, dy in KICKS:
            if self.valid(rotated, self.px + dx, self.py + dy):
                self.piece["shape"] = rotated
                self.px += dx
                self.py += dy
                self.events.append("rotate")
                self.bump_lock()
                return True
        return False

    def ghost_y(self):
        gy = self.py
        while self.valid(self.piece["shape"], self.px, gy + 1):
            gy += 1
        return gy

    def hard_drop(self):
        if not self.active():
            return
        gy = self.ghost_y()
        self.score += 2 * (gy - self.py)
        self.py = gy
        self.lock()

    def hold_piece(self):
        if not self.active() or not self.can_hold:
            return
        current = self.piece["name"]
        incoming = self.pop_next() if self.hold is None else self.hold
        self.hold = current
        self.can_hold = False
        self.events.append("hold")
        self.spawn(incoming)

    def lock(self):
        for r, row in enumerate(self.piece["shape"]):
            for c, cell in enumerate(row):
                if cell and 0 <= self.py + r < ROWS:
                    self.board[self.py + r][self.px + c] = self.piece["color"]
        self.events.append("lock")
        self.can_hold = True
        self.piece = None
        rows = [r for r, row in enumerate(self.board) if all(row)]
        if rows:
            self.clearing, self.clear_t = rows, 0.0
            self.events.append("tetris" if len(rows) == 4 else "clear")
        else:
            self.spawn(self.pop_next())

    def finish_clear(self):
        n = len(self.clearing)
        keep = [row for r, row in enumerate(self.board) if r not in self.clearing]
        self.board = [[None] * COLS for _ in range(n)] + keep
        self.lines += n
        self.score += LINE_SCORES[n] * self.level
        self.level = self.lines // 10 + 1
        self.popup = (CLEAR_NAMES[n], 1200.0)
        self.clearing = []
        self.spawn(self.pop_next())

    def press_dir(self, d):
        self.move(d)
        self.das_dir = d
        self.das_t = self.arr_t = 0.0

    def update(self, dt, held):
        if self.popup:
            text, t = self.popup
            self.popup = (text, t - dt) if t - dt > 0 else None
        if self.over:
            return
        if self.clearing:
            self.clear_t += dt
            if self.clear_t >= CLEAR_MS:
                self.finish_clear()
            return

        left, right = "left" in held, "right" in held
        if left and not right:
            want = -1
        elif right and not left:
            want = 1
        elif left and right:
            want = self.das_dir
        else:
            want = 0
        if want == 0:
            self.das_dir, self.das_t, self.arr_t = 0, 0.0, 0.0
        elif want != self.das_dir:
            self.das_dir, self.das_t, self.arr_t = want, 0.0, 0.0
        else:
            self.das_t += dt
            if self.das_t >= DAS_MS:
                self.arr_t += dt
                while self.arr_t >= ARR_MS:
                    self.arr_t -= ARR_MS
                    if not self.move(want):
                        self.arr_t = 0.0
                        break

        if "soft" in held:
            self.soft_t += dt
            self.fall_t = 0.0
            while self.soft_t >= SOFT_MS:
                self.soft_t -= SOFT_MS
                if not self.down(1):
                    self.soft_t = 0.0
                    break
        else:
            self.soft_t = 0.0
            self.fall_t += dt
            iv = self.interval()
            while self.fall_t >= iv:
                self.fall_t -= iv
                if not self.down():
                    self.fall_t = 0.0
                    break

        if self.piece is not None and self.grounded():
            self.lock_t += dt
            if self.lock_t >= LOCK_MS:
                self.lock()
        else:
            self.lock_t = 0.0


def draw_title(canvas, cell):
    for i, ch in enumerate("TETRIS"):
        col = TITLE_COLORS[i]
        dark = hexc([v * 0.5 for v in col])
        light = hexc([min(255, v + 80) for v in col])
        for r, line in enumerate(GLYPHS[ch]):
            for c, mark in enumerate(line):
                if mark == "#":
                    x, y = 10 + (i * 6 + c) * cell, 10 + r * cell
                    canvas.create_rectangle(x, y, x + cell, y + cell, fill=hexc(col), outline=dark, width=2)
                    canvas.create_line(x + 3, y + 3, x + cell - 3, y + 3, fill=light, width=2)
                    canvas.create_line(x + 3, y + 3, x + 3, y + cell - 3, fill=light, width=2)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("Tetris")
        self.configure(fg_color=NAVY)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.after(400, lambda: self.attributes("-fullscreen", True))
        self.data = load_data()
        self.game = Game()
        self.mode, self.current = "menu", "nick"
        self.paused, self.capture, self.closing = False, None, False
        self.held, self.sounds, self.keymap, self.panels = set(), {}, {}, {}
        self.pg_ready = False
        self.recorded = self.new_record = False
        self.loop_id, self.frame_no, self.last_t = None, 0, 0.0
        self.sw, self.sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.rebuild_keymap()
        self.init_audio()
        self.build_background()
        self.build_nick()
        self.build_menu()
        self.build_options()
        self.build_scores()
        self.game_frame = tk.Frame(self, bg="black")
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<FocusOut>", lambda e: self.held.clear() if e.widget is self else None)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.animate_bg()
        self.show("nick")

    # ---------- audio ----------
    def init_audio(self):
        try:
            pygame.mixer.init(22050, -16, 1)
            self.sounds = {
                "move": make_tone(500, 25), "rotate": make_tone(700, 40),
                "hold": make_tone(600, 70, sweep=300), "lock": make_tone(180, 70),
                "clear": make_tone(500, 260, sweep=700), "tetris": make_tone(600, 520, sweep=1200),
                "over": make_tone(400, 700, sweep=-300),
            }
        except Exception:
            self.sounds = {}
        self.apply_volume()

    def apply_volume(self):
        for s in self.sounds.values():
            s.set_volume(self.data["volume"] / 100)

    def play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()

    # ---------- menu screens ----------
    def font(self, size):
        return ctk.CTkFont(family="Consolas", size=size, weight="bold")

    def build_background(self):
        self.bg = tk.Canvas(self, bg=NAVY, highlightthickness=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.blocks = []
        for _ in range(26):
            s = random.randint(24, 64)
            col = random.choice(list(SHAPES.values()))[1]
            fill = hexc([v * 0.35 + b * 0.65 for v, b in zip(col, (8, 26, 77))])
            edge = hexc([v * 0.5 + b * 0.5 for v, b in zip(col, (8, 26, 77))])
            x, y = random.randint(0, max(1, self.sw - s)), random.randint(-self.sh, self.sh)
            item = self.bg.create_rectangle(x, y, x + s, y + s, fill=fill, outline=edge, width=2)
            self.blocks.append([x, y, s, random.randint(1, 3), item])

    def animate_bg(self):
        if self.closing:
            return
        if self.mode != "game":
            for b in self.blocks:
                b[1] += b[3]
                if b[1] > self.sh:
                    b[0], b[1] = random.randint(0, max(1, self.sw - b[2])), -b[2]
                self.bg.coords(b[4], b[0], b[1], b[0] + b[2], b[1] + b[2])
        self.after(40, self.animate_bg)

    def make_panel(self, name):
        p = ctk.CTkFrame(self, fg_color=PANEL, border_color=BORDER, border_width=6, corner_radius=0)
        self.panels[name] = p
        return p

    def show(self, name):
        for p in self.panels.values():
            p.place_forget()
        self.current = name
        self.panels[name].place(relx=0.5, rely=0.5, anchor="center")
        if name == "menu":
            best = self.data["players"].get(self.data["nickname"], {}).get("best", 0)
            self.menu_info.configure(text=f"PLAYER: {self.data['nickname']}    BEST: {best}")
        elif name == "scores":
            self.refresh_scores()
        elif name == "nick":
            self.nick_entry.focus_set()

    def block_button(self, parent, text, cmd, red=False, width=380, height=60, size=24):
        col, hov, edge = (RED, RED_HOVER, RED_EDGE) if red else (BLUE, BLUE_HOVER, BLUE_EDGE)
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=height, corner_radius=0,
                             border_width=5, border_color=edge, fg_color=col, hover_color=hov,
                             text_color="white", font=self.font(size))

    def title_canvas(self, parent, cell):
        cv = tk.Canvas(parent, width=35 * cell + 20, height=5 * cell + 20, bg=PANEL, highlightthickness=0)
        draw_title(cv, cell)
        cv.pack(pady=(26, 8), padx=30)

    def build_nick(self):
        p = self.make_panel("nick")
        self.title_canvas(p, 14)
        ctk.CTkLabel(p, text="ENTER YOUR NICKNAME", font=self.font(22), text_color="white").pack(pady=(10, 8))
        self.nick_entry = ctk.CTkEntry(p, width=420, height=58, corner_radius=0, border_width=4,
                                       border_color=BORDER, fg_color=NAVY, justify="center",
                                       font=self.font(26))
        self.nick_entry.pack(pady=8, padx=40)
        self.nick_entry.insert(0, self.data["nickname"])
        self.nick_entry.bind("<Return>", lambda e: self.confirm_nick())
        self.nick_msg = ctk.CTkLabel(p, text="", text_color=RED_EDGE, font=self.font(16))
        self.nick_msg.pack()
        self.block_button(p, "CONTINUE", self.confirm_nick).pack(pady=(8, 30), padx=40)

    def confirm_nick(self):
        name = self.nick_entry.get().strip()[:12]
        if not name:
            self.nick_msg.configure(text="Please type a nickname.")
            return
        self.nick_msg.configure(text="")
        self.data["nickname"] = name
        save_data(self.data)
        self.show("menu")

    def build_menu(self):
        p = self.make_panel("menu")
        self.title_canvas(p, 14)
        self.menu_info = ctk.CTkLabel(p, text="", font=self.font(20), text_color=GOLD)
        self.menu_info.pack(pady=(4, 14))
        self.block_button(p, "START", self.start_game).pack(pady=7, padx=50)
        self.block_button(p, "HIGH SCORES", lambda: self.show("scores")).pack(pady=7, padx=50)
        self.block_button(p, "OPTIONS", lambda: self.show("options")).pack(pady=7, padx=50)
        self.block_button(p, "CHANGE PLAYER", lambda: self.show("nick")).pack(pady=7, padx=50)
        self.block_button(p, "EXIT", self.quit_app, red=True).pack(pady=(7, 34), padx=50)

    def build_options(self):
        p = self.make_panel("options")
        ctk.CTkLabel(p, text="OPTIONS", font=self.font(36), text_color="white").pack(pady=(22, 6))
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", padx=30, pady=(8, 4))
        ctk.CTkLabel(row, text="VOLUME", width=200, anchor="w", font=self.font(18)).pack(side="left")
        self.vol_label = ctk.CTkLabel(row, text=f"{self.data['volume']}%", width=60, font=self.font(18))
        self.vol_label.pack(side="right")
        self.vol_slider = ctk.CTkSlider(row, from_=0, to=100, number_of_steps=20, width=220,
                                        command=self.on_volume)
        self.vol_slider.set(self.data["volume"])
        self.vol_slider.pack(side="right", padx=8)
        self.vol_slider.bind("<ButtonRelease-1>", lambda e: (save_data(self.data), self.play("rotate")))
        ctk.CTkLabel(p, text="CONTROLS  (click a key to change it)", font=self.font(16),
                     text_color=BLUE_EDGE).pack(pady=(14, 4))
        self.key_btns = {}
        for act, label in ACTIONS:
            r = ctk.CTkFrame(p, fg_color="transparent")
            r.pack(fill="x", padx=30, pady=2)
            ctk.CTkLabel(r, text=label.upper(), width=260, anchor="w", font=self.font(16)).pack(side="left")
            b = self.block_button(r, "", lambda a=act: self.start_capture(a), width=200, height=38, size=18)
            b.pack(side="right")
            self.key_btns[act] = b
        bottom = ctk.CTkFrame(p, fg_color="transparent")
        bottom.pack(pady=(16, 24))
        self.block_button(bottom, "RESET KEYS", self.reset_keys, width=200, height=48, size=18).pack(side="left", padx=8)
        self.block_button(bottom, "BACK", lambda: self.show("menu"), width=200, height=48, size=18).pack(side="left", padx=8)
        self.refresh_keys()

    def on_volume(self, value):
        self.data["volume"] = int(value)
        self.vol_label.configure(text=f"{int(value)}%")
        self.apply_volume()

    def rebuild_keymap(self):
        self.keymap = {k: a for a, k in self.data["keys"].items()}

    def refresh_keys(self):
        for act, btn in self.key_btns.items():
            btn.configure(text="PRESS A KEY..." if self.capture == act else pretty(self.data["keys"][act]))

    def start_capture(self, act):
        self.capture = None if self.capture == act else act
        self.refresh_keys()

    def finish_capture(self, key):
        act, keys = self.capture, self.data["keys"]
        for other, k in keys.items():
            if k == key and other != act:
                keys[other] = keys[act]
        keys[act] = key
        self.capture = None
        self.rebuild_keymap()
        save_data(self.data)
        self.refresh_keys()

    def reset_keys(self):
        self.data["keys"] = dict(DEFAULT_KEYS)
        self.capture = None
        self.rebuild_keymap()
        save_data(self.data)
        self.refresh_keys()

    def build_scores(self):
        p = self.make_panel("scores")
        ctk.CTkLabel(p, text="HIGH SCORES", font=self.font(36), text_color="white").pack(pady=(22, 10))
        self.score_box = ctk.CTkFrame(p, fg_color=NAVY, border_color=BORDER, border_width=4, corner_radius=0)
        self.score_box.pack(padx=30, pady=6)
        self.block_button(p, "BACK", lambda: self.show("menu"), width=240, height=50, size=20).pack(pady=(14, 24))

    def refresh_scores(self):
        for w in self.score_box.winfo_children():
            w.destroy()
        players = [(n, d) for n, d in self.data["players"].items() if isinstance(d, dict)]
        players.sort(key=lambda nd: nd[1].get("best", 0), reverse=True)
        if not players:
            ctk.CTkLabel(self.score_box, text="No scores yet - be the first!", font=self.font(18),
                         width=520, height=80).pack(padx=20, pady=20)
            return
        for c, h in enumerate(["#", "PLAYER", "SCORE", "LINES", "LEVEL"]):
            ctk.CTkLabel(self.score_box, text=h, font=self.font(16), text_color=BLUE_EDGE,
                         width=[50, 190, 110, 80, 80][c]).grid(row=0, column=c, padx=4, pady=(10, 4))
        for i, (name, d) in enumerate(players[:10], start=1):
            col = GOLD if name == self.data["nickname"] else "white"
            vals = [str(i), name, str(d.get("best", 0)), str(d.get("lines", 0)), str(d.get("level", 1))]
            for c, v in enumerate(vals):
                ctk.CTkLabel(self.score_box, text=v, font=self.font(18), text_color=col,
                             width=[50, 190, 110, 80, 80][c]).grid(row=i, column=c, padx=4, pady=3)
        ctk.CTkLabel(self.score_box, text="", height=6).grid(row=11, column=0)

    # ---------- game flow ----------
    def init_pygame(self):
        os.environ["SDL_WINDOWID"] = str(self.game_frame.winfo_id())
        if os.name == "nt":
            os.environ["SDL_VIDEODRIVER"] = "windows"
        pygame.display.init()
        pygame.font.init()
        w, h = self.game_frame.winfo_width(), self.game_frame.winfo_height()
        if w < 200 or h < 200:
            w, h = self.sw, self.sh
        self.screen = pygame.display.set_mode((w, h))
        self.layout()
        self.pg_ready = True

    def start_game(self):
        self.mode = "game"
        for p in self.panels.values():
            p.place_forget()
        self.game_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.update()
        if not self.pg_ready:
            self.init_pygame()
        self.restart()
        self.loop()

    def restart(self):
        self.game.reset()
        self.paused = self.recorded = self.new_record = False
        self.held.clear()
        self.last_t = time.perf_counter()

    def to_menu(self):
        if self.loop_id:
            self.after_cancel(self.loop_id)
            self.loop_id = None
        self.mode = "menu"
        self.held.clear()
        self.game_frame.place_forget()
        self.show("menu")

    def quit_app(self):
        self.closing = True
        try:
            pygame.quit()
        except Exception:
            pass
        self.destroy()

    def record_score(self):
        self.recorded = True
        g = self.game
        p = self.data["players"].setdefault(self.data["nickname"], {"best": 0, "lines": 0, "level": 1, "games": 0})
        p["games"] = p.get("games", 0) + 1
        if g.score > p.get("best", 0):
            p.update(best=g.score, lines=g.lines, level=g.level)
            self.new_record = g.score > 0
        save_data(self.data)

    def loop(self):
        if self.mode != "game" or self.closing:
            return
        now = time.perf_counter()
        dt = min(100.0, (now - self.last_t) * 1000)
        self.last_t = now
        g = self.game
        if not self.paused:
            g.update(dt, {self.keymap[k] for k in self.held if k in self.keymap})
        if g.over and not self.recorded:
            self.record_score()
        events, g.events = g.events, []
        for name in events:
            self.play(name)
        self.draw()
        pygame.event.pump()
        pygame.event.clear()
        self.frame_no += 1
        if self.frame_no % 30 == 0 and not self.capture:
            self.focus_force()
        self.loop_id = self.after(16, self.loop)

    # ---------- keyboard ----------
    def on_key_press(self, e):
        key = e.keysym.lower()
        if self.capture:
            self.finish_capture(key)
            return "break"
        if self.mode != "game":
            if key == "escape" and self.current in ("options", "scores"):
                self.show("menu")
            return None
        if key in self.held:
            return None
        self.held.add(key)
        g, act = self.game, self.keymap.get(key)
        if g.over:
            if key in ("return", "kp_enter"):
                self.restart()
            elif act == "pause" or key == "escape":
                self.to_menu()
        elif act == "pause":
            self.paused = not self.paused
        elif self.paused:
            if key == "q":
                self.to_menu()
        elif act in ("left", "right"):
            g.press_dir(-1 if act == "left" else 1)
        elif act == "rotate_cw":
            g.rotate(True)
        elif act == "rotate_ccw":
            g.rotate(False)
        elif act == "hold":
            g.hold_piece()
        elif act == "hard":
            g.hard_drop()
        return None

    def on_key_release(self, e):
        self.held.discard(e.keysym.lower())

    # ---------- drawing (pygame) ----------
    def layout(self):
        W, H = self.screen.get_size()
        c = max(16, int(H * 0.88) // ROWS)
        self.cell = c
        self.bx, self.by = (W - COLS * c) // 2, (H - ROWS * c) // 2
        pw = int(c * 5.4)
        self.hold_rect = pygame.Rect(self.bx - pw - c, self.by, pw, int(c * 4.6))
        self.stat_rect = pygame.Rect(self.hold_rect.x, self.hold_rect.bottom + c // 2, pw, int(c * 7.6))
        self.next_rect = pygame.Rect(self.bx + COLS * c + c, self.by, pw, int(c * 10.4))
        self.f_big = pygame.font.SysFont("arial", int(c * 1.1), bold=True)
        self.f_mid = pygame.font.SysFont("arial", int(c * 0.7), bold=True)
        self.f_small = pygame.font.SysFont("arial", int(c * 0.5), bold=True)
        self.bg_surf = pygame.Surface((W, H))
        for y in range(0, H, 4):
            t = y / H
            pygame.draw.rect(self.bg_surf, (int(6 + 10 * t), int(14 + 22 * t), int(50 + 40 * t)), (0, y, W, 4))

    def text(self, msg, font, color, center):
        img = font.render(msg, True, color)
        self.screen.blit(img, img.get_rect(center=center))

    def block(self, x, y, s, col):
        scr = self.screen
        pygame.draw.rect(scr, col, (x, y, s, s))
        light = tuple(min(255, v + 70) for v in col)
        dark = tuple(int(v * 0.55) for v in col)
        b = max(2, s // 8)
        pygame.draw.polygon(scr, light, [(x, y), (x + s, y), (x + s - b, y + b), (x + b, y + b), (x + b, y + s - b), (x, y + s)])
        pygame.draw.polygon(scr, dark, [(x + s, y + s), (x, y + s), (x + b, y + s - b), (x + s - b, y + s - b), (x + s - b, y + b), (x + s, y)])

    def draw_panel(self, rect, title=None):
        pygame.draw.rect(self.screen, (10, 24, 80), rect)
        pygame.draw.rect(self.screen, (77, 141, 255), rect, 5)
        pygame.draw.rect(self.screen, (30, 70, 170), rect.inflate(-14, -14), 2)
        if title:
            self.text(title, self.f_mid, (255, 255, 255), (rect.centerx, rect.y + int(self.cell * 0.7)))

    def draw_mini(self, name, rect, gray=False):
        shape, color = SHAPES[name]
        s = int(self.cell * 0.8)
        x0 = rect.centerx - len(shape[0]) * s // 2
        y0 = rect.centery - len(shape) * s // 2
        for r, row in enumerate(shape):
            for c, cell in enumerate(row):
                if cell:
                    self.block(x0 + c * s, y0 + r * s, s, (90, 90, 110) if gray else color)

    def overlay(self, board, lines):
        shade = pygame.Surface(board.size, pygame.SRCALPHA)
        shade.fill((0, 0, 20, 185))
        self.screen.blit(shade, board.topleft)
        y = board.centery - int(self.cell * 1.6)
        for msg, font, color, gap in lines:
            self.text(msg, font, color, (board.centerx, y))
            y += gap

    def draw(self):
        s, g, c = self.screen, self.game, self.cell
        bx, by = self.bx, self.by
        s.blit(self.bg_surf, (0, 0))
        board = pygame.Rect(bx, by, COLS * c, ROWS * c)
        pygame.draw.rect(s, (5, 10, 34), board)
        for i in range(1, COLS):
            pygame.draw.line(s, (16, 30, 80), (bx + i * c, by), (bx + i * c, by + ROWS * c))
        for i in range(1, ROWS):
            pygame.draw.line(s, (16, 30, 80), (bx, by + i * c), (bx + COLS * c, by + i * c))
        for r in range(ROWS):
            for col in range(COLS):
                if g.board[r][col]:
                    self.block(bx + col * c, by + r * c, c, g.board[r][col])
        if g.active():
            gy = g.ghost_y()
            for r, row in enumerate(g.piece["shape"]):
                for col, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(s, g.piece["color"], (bx + (g.px + col) * c + 3, by + (gy + r) * c + 3, c - 6, c - 6), 2)
            for r, row in enumerate(g.piece["shape"]):
                for col, cell in enumerate(row):
                    if cell and g.py + r >= 0:
                        self.block(bx + (g.px + col) * c, by + (g.py + r) * c, c, g.piece["color"])
        if g.clearing:
            flash = (255, 255, 255) if int(g.clear_t // 70) % 2 == 0 else (120, 170, 255)
            for r in g.clearing:
                pygame.draw.rect(s, flash, (bx, by + r * c, COLS * c, c))
        pygame.draw.rect(s, (77, 141, 255), board.inflate(12, 12), 6)

        self.draw_panel(self.hold_rect, "HOLD")
        if g.hold:
            self.draw_mini(g.hold, self.hold_rect.inflate(0, -c), gray=not g.can_hold)
        self.draw_panel(self.next_rect, "NEXT")
        for i, name in enumerate(g.queue[:3]):
            slot = pygame.Rect(self.next_rect.x, self.next_rect.y + int(c * 1.4) + i * int(c * 2.9), self.next_rect.w, int(c * 2.9))
            self.draw_mini(name, slot)

        self.draw_panel(self.stat_rect)
        player = self.data["players"].get(self.data["nickname"], {})
        best = max(player.get("best", 0), g.score) if isinstance(player, dict) else g.score
        self.text(self.data["nickname"], self.f_mid, (255, 216, 77), (self.stat_rect.centerx, self.stat_rect.y + int(c * 0.8)))
        y = self.stat_rect.y + int(c * 1.9)
        for label, value in (("SCORE", g.score), ("LINES", g.lines), ("LEVEL", g.level), ("BEST", best)):
            self.text(label, self.f_small, (143, 184, 255), (self.stat_rect.centerx, y))
            self.text(str(value), self.f_mid, (255, 255, 255), (self.stat_rect.centerx, y + int(c * 0.6)))
            y += int(c * 1.4)

        if g.popup:
            self.text(g.popup[0], self.f_big, (255, 235, 120), (board.centerx, by + 3 * c))
        pause_key = pretty(self.data["keys"]["pause"])
        self.text(f"{pause_key}: PAUSE", self.f_small, (143, 184, 255), (board.centerx, by + ROWS * c + int(c * 0.75)))

        white, blue, gold = (255, 255, 255), (143, 184, 255), (255, 216, 77)
        if g.over:
            lines = [("GAME OVER", self.f_big, (255, 120, 110), int(c * 1.4)),
                     (f"SCORE  {g.score}", self.f_mid, white, int(c * 1.0))]
            if self.new_record:
                lines.append(("NEW HIGH SCORE!", self.f_mid, gold, int(c * 1.3)))
            lines += [("ENTER: PLAY AGAIN", self.f_small, blue, int(c * 0.8)), (f"{pause_key}: MAIN MENU", self.f_small, blue, 0)]
            self.overlay(board, lines)
        elif self.paused:
            self.overlay(board, [("PAUSED", self.f_big, white, int(c * 1.6)),
                                 (f"{pause_key}: RESUME", self.f_small, blue, int(c * 0.8)),
                                 ("Q: MAIN MENU", self.f_small, blue, 0)])
        pygame.display.flip()


if __name__ == "__main__":
    App().mainloop()