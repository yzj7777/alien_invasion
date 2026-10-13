"""子弹类（教材 12.8.2）。"""

from __future__ import annotations

import pygame
from pygame.sprite import Sprite


class Bullet(Sprite):
    """管理飞船所发射子弹的类。"""

    def __init__(self, ai_game) -> None:
        """在飞船的当前位置创建一个子弹对象。"""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.color = self.settings.bullet_color

        # 在 (0, 0) 处创建一个表示子弹的矩形，再设置正确的位置。
        # 注意与飞船/外星人的区别：子弹没有图片，是从零开始造的矩形。
        self.rect = pygame.Rect(
            0, 0, self.settings.bullet_width, self.settings.bullet_height
        )
        self.rect.midtop = ai_game.ship.rect.midtop

        # 存储用浮点数表示的子弹位置（和飞船同样的思路）
        self.y = float(self.rect.y)

    def update(self) -> None:
        """向上移动子弹。"""
        # 更新子弹的准确位置
        self.y -= self.settings.bullet_speed
        # 更新表示子弹的 rect 的位置
        self.rect.y = self.y

    def draw_bullet(self) -> None:
        """在屏幕上绘制子弹。"""
        pygame.draw.rect(self.screen, self.color, self.rect)
