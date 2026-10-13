"""《外星人入侵》—— 教材《Python 编程从入门到实践》（第 3 版）项目 1。

包结构（对应书里的平铺文件）::

    src/alien_invasion/
    ├── game.py         ← 书里的 alien_invasion.py（AlienInvasion 类 + 主循环）
    ├── settings.py     ← Settings
    ├── ship.py         ← Ship
    ├── bullet.py       ← Bullet
    ├── alien.py        ← Alien
    ├── game_stats.py   ← GameStats
    ├── button.py       ← Button
    ├── scoreboard.py   ← Scoreboard
    └── images/
        ├── ship.bmp
        └── alien.bmp

命令行运行::

    uv run alien-invasion        # 安装后由 pyproject.toml 的 [project.scripts] 提供
    uv run python -m alien_invasion
"""

from __future__ import annotations

from .alien import Alien
from .bullet import Bullet
from .button import Button
from .game import AlienInvasion, main
from .game_stats import GameStats
from .scoreboard import Scoreboard
from .settings import Settings
from .ship import Ship

__all__ = [
    "AlienInvasion",
    "Alien",
    "Bullet",
    "Button",
    "GameStats",
    "Scoreboard",
    "Settings",
    "Ship",
    "main",
]

__version__ = "0.1.0"
