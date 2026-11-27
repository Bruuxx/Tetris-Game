# Tetris

A fullscreen Tetris game for Windows, made in Python. The window and menus use **customtkinter**, and the game itself is drawn by **pygame** inside that same window.

Made by Bruux.

## Features

- Blue, blocky Tetris-style main menu with a block-letter logo and falling blocks
- Nickname prompt on startup, with a saved high score list for every player
- Hold piece, ghost piece, and a next queue that shows the next 3 pieces
- Smooth left/right movement (hold the key and the piece slides quickly)
- Lock delay, so you can still slide or rotate a piece for a moment after it lands
- Line-clear animation with SINGLE / DOUBLE / TRIPLE / TETRIS! popups and sound effects
- Controls you can change, and a volume slider
- Pause screen and game over screen

## Requirements

- Windows
- Python 3.10 or newer
- `customtkinter` and `pygame-ce`

Install the libraries:

```
pip install customtkinter pygame-ce
```

> If `pip install pygame` fails on your Python version, use `pygame-ce` as shown above. The code is the same (`import pygame`).

## How to run

Open Command Prompt in the project folder and run:

```
python Tetris_v2.py
```

The game opens in fullscreen. Use the **Exit** button in the menu or press **Alt + F4** to close it.

## Menu

| Button | What it does |
|---|---|
| Start | Starts a new game |
| High Scores | Shows the top 10 players |
| Options | Change the volume and the controls |
| Change Player | Go back to the nickname screen |
| Exit | Closes the game |

## Default controls

| Key | Action |
|---|---|
| A | Move left |
| D | Move right |
| S | Soft drop |
| W | Rotate right |
| V | Rotate left |
| C | Hold piece |
| Space | Hard drop |
| Esc | Pause |

You can change any of these in **Options**: click a key, then press the new key. If the key is already used by another action, the two swap. **Reset keys** brings back the defaults.

While paused, press **Q** to go back to the main menu.
When the game is over, press **Enter** to play again or **Esc** to go back to the menu.

## Scoring

| Move | Points |
|---|---|
| Soft drop | 1 per row |
| Hard drop | 2 per row |
| 1 line | 100 x level |
| 2 lines | 300 x level |
| 3 lines | 500 x level |
| 4 lines (Tetris) | 800 x level |

You go up one level for every 10 lines, and the pieces fall faster each level.

## Saved data

Your nickname, volume, controls, and high scores are saved in `tetris_data.json`, in the same folder as the game. Delete that file to reset everything.

## Settings in the code

These values are at the top of `Tetris_v2.py` if you want to change how the game feels:

| Name | Meaning |
|---|---|
| `DAS_MS` | Delay before a held left/right key starts repeating |
| `ARR_MS` | Time between repeated moves |
| `SOFT_MS` | Time between rows while soft dropping |
| `LOCK_MS` | How long a landed piece waits before locking |
| `MAX_LOCK_RESETS` | How many times sliding or rotating can restart the lock timer |
| `CLEAR_MS` | How long the line-clear flash lasts |
| `COLS`, `ROWS` | Size of the board |

## Troubleshooting

- **Blank or small window:** run the game from Command Prompt (`python Tetris_v2.py`) and read the error message at the bottom.
- **`No module named 'pygame'`:** install it with `pip install pygame-ce`.
- **`No module named 'customtkinter'`:** install it with `pip install customtkinter`.
- **Keys stop working:** click the game window once, then try again.
- **No sound:** check that the Sound volume in Options is above 0, and that your computer has an audio device.
