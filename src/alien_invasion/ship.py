"""飞船类（教材 12.4.1 引入，12.6 节加入移动，13.6 节加入 center_ship）。

对应书里的 ship.py，只有两处工程化的小改动：
1. 图片路径改成基于 __file__ 的绝对路径（见 settings.IMAGES_DIR）；
2. `pygame.image.load(...)` 之后可选地调用 `.convert()` 提速（放在这里用惰性方式做，
   因为 convert() 必须在 set_mode() 之后调用，而 Ship 一定是在窗口建好之后才创建的）。
"""

from __future__ import annotations

import pygame
from pygame.sprite import Sprite

from .settings import IMAGES_DIR


class Ship(Sprite):
    """管理飞船的类。"""

    def __init__(self, ai_game) -> None:
        """初始化飞船并设置其起始位置。"""
        super().__init__()                     # 教材 14.3 节：为加入编组做准备
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.screen_rect = ai_game.screen.get_rect()

        # 加载飞船图像并获取其外接矩形
        self.image = pygame.image.load(str(IMAGES_DIR / "ship.bmp"))
        self.image = self.image.convert()      # 转换像素格式，blit 更快（可选优化）
        self.rect = self.image.get_rect()

        # 每艘新飞船都放在屏幕底部的中央
        self.rect.midbottom = self.screen_rect.midbottom

        # 在飞船的属性 x 中存储一个浮点数（rect 只存整数，无法表达 1.5 像素）
        self.x = float(self.rect.x)

        # 移动标志（飞船一开始不移动）
        self.moving_right = False
        self.moving_left = False

    def update(self) -> None:
        """根据移动标志调整飞船的位置。"""
        # 更新飞船的属性 x 的值，而不是其外接矩形的属性 x 的值
        if self.moving_right and self.rect.right < self.screen_rect.right:
            self.x += self.settings.ship_speed
        if self.moving_left and self.rect.left > 0:
            self.x -= self.settings.ship_speed

        # 根据 self.x 更新 rect 对象
        self.rect.x = self.x

    def blitme(self) -> None:
        """在指定位置绘制飞船。"""
        self.screen.blit(self.image, self.rect)

    def center_ship(self) -> None:
        """将飞船放在屏幕底部的中央（被撞之后调用）。"""
        self.rect.midbottom = self.screen_rect.midbottom
        self.x = float(self.rect.x)
