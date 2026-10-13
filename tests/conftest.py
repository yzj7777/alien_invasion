"""pytest 公共夹具。

关键点：**在 import pygame 之前**把视频驱动设为 dummy。
沙箱/CI 没有显示器，如果不设，`pygame.display.set_mode()` 会直接报错
`pygame.error: No available video device`。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# 让测试在「没有 uv sync / 没装成包」时也能直接跑：
# 把 src/ 加进 sys.path（等价于教材里「所有文件放同一个文件夹」的效果）
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame  # noqa: E402
import pytest  # noqa: E402

from alien_invasion import AlienInvasion  # noqa: E402


class FakeInput:
    """假输入：把想注入的事件排好队，让游戏以为是玩家操作。"""

    def __init__(self) -> None:
        self.queue: list[pygame.event.Event] = []

    def key_down(self, key: int) -> None:
        self.queue.append(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))

    def key_up(self, key: int) -> None:
        self.queue.append(pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode="", scancode=0))

    def click(self, pos: tuple[int, int]) -> None:
        self.queue.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))

    # 游戏每帧调用它拿事件
    def __call__(self) -> list[pygame.event.Event]:
        events, self.queue = self.queue, []
        return events


@pytest.fixture
def fake() -> FakeInput:
    return FakeInput()


@pytest.fixture
def game(fake: FakeInput):
    """一个已经初始化好、但还没开始玩的游戏实例。"""
    pygame.init()
    ai = AlienInvasion(event_source=fake)
    yield ai
    pygame.quit()


def step(game: AlienInvasion, frames: int = 1) -> None:
    """手动推进游戏若干帧（等价于主循环里去掉 tick 的那部分）。"""
    for _ in range(frames):
        game._check_events()
        if game.game_active:
            game.ship.update()
            game._update_bullets()
            game._update_aliens()
        game._update_screen()
