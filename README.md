# Tetris (Python)

A classic Tetris game built with Python using `customtkinter` for the modern dark-mode UI and `pygame` for smooth 60 FPS rendering and synthesized retro sound effects.

## Features
- **Classic Tetris Mechanics:** 7-bag piece randomizer, SRS-style wall kicks, soft drop, hard drop, and ghost piece preview.
- **Progressive Difficulty:** Automatic level progression every 10 cleared lines with increasing drop speed.
- **Synthesized Sound Effects:** Built-in retro audio effects for movement, rotation, locking, line clears, and game over (with a toggle switch).
- **Modern UI:** Live tracking of Score, Lines, Level, and Next Piece preview.

## Controls
| Key | Action |
| :--- | :--- |
| `←` / `→` | Move Left / Right |
| `↑` | Rotate Piece |
| `↓` | Soft Drop |
| `Space` | Hard Drop |
| `P` | Pause / Resume |

## Requirements
- Python 3.8+
- `customtkinter`
- `pygame`

## How to Run
1. Install the required libraries:
   ```bash
   pip install customtkinter pygame
