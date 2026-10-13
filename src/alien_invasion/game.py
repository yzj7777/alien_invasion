"""《外星人入侵》主程序：AlienInvasion 类（教材第 12～14 章的最终版本）。

对应书里的 alien_invasion.py，结构与方法名几乎完全一致，另有 5 处**有意的**
工程化改动，每处都在代码里写了注释，教程 `docs/教程.md` 也专门讲了一节：

1. 事件来源可注入（`event_source`）：默认就是 `pygame.event.get`，
   但自动化测试、浏览器预览可以「喂」假事件进来；
2. 每绘制完一帧回调 `on_frame(self)`：用来录屏、截图、跑自动驾驶；
3. 退出方式改成协作式的 `self.running = False`，而不是在事件处理里直接
   `sys.exit()`（这样游戏可以被别的程序驱动、可以优雅收尾）；
4. 鼠标点击用 `event.pos` 而不是 `pygame.mouse.get_pos()`；
5. 帧率、图片路径都来自 settings，不写死、不依赖当前工作目录。
"""

from __future__ import annotations

import sys
from time import sleep

import pygame

from .alien import Alien
from .bullet import Bullet
from .button import Button
from .game_stats import GameStats
from .scoreboard import Scoreboard
from .settings import Settings
from .ship import Ship


class AlienInvasion:
    """管理游戏资源和行为的类。"""

    def __init__(self, event_source=None, on_frame=None) -> None:
        """初始化游戏并创建游戏资源。

        参数（不传就是教材里的行为）：
            event_source: 可调用对象，返回事件列表；默认 pygame.event.get
            on_frame:     每绘制完一帧后被调用，参数是游戏实例本身
        """
        pygame.init()
        self.clock = pygame.time.Clock()
        self.settings = Settings()

        self.screen = pygame.display.set_mode(
            (self.settings.screen_width, self.settings.screen_height)
        )
        pygame.display.set_caption("Alien Invasion")

        # 事件来源、帧回调、主循环开关（教材里没有这三个属性）
        self.event_source = event_source or pygame.event.get
        self.on_frame = on_frame
        self.running = True

        # 创建存储游戏统计信息的实例，并创建记分牌
        self.stats = GameStats(self)
        self.sb = Scoreboard(self)

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()

        self._create_fleet()

        # 让游戏在一开始处于非活动状态
        self.game_active = False

        # 创建 Play 按钮
        self.play_button = Button(self, "Play")

    # ------------------------------------------------------------- 主循环
    def run_game(self) -> None:
        """开始游戏的主循环。"""
        while self.running:
            self._check_events()

            if self.game_active:
                self.ship.update()
                self._update_bullets()
                self._update_aliens()

            self._update_screen()

            # 教材没有这一步：给外部程序一个「围观」每一帧的机会
            if self.on_frame is not None:
                self.on_frame(self)

            self.clock.tick(self.settings.fps)

    def quit(self) -> None:
        """结束主循环（按 Q、关闭窗口，或外部调用）。"""
        self.running = False

    # ------------------------------------------------------------- 事件
    def _check_events(self) -> None:
        """响应按键和鼠标事件。"""
        for event in self.event_source():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 教材写的是 pygame.mouse.get_pos()：那读的是鼠标「当前」位置，
                # 如果事件是外部注入的（测试、浏览器控制）就会对不上，
                # 所以这里改成用事件自带的位置 event.pos。
                self._check_play_button(event.pos)

    def _check_keydown_events(self, event) -> None:
        """响应按下。"""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()
        elif event.key == pygame.K_p:            # 练习 14.1：按 P 开始新游戏
            if not self.game_active:
                self._start_game()
        elif event.key == pygame.K_q:
            self.quit()

    def _check_keyup_events(self, event) -> None:
        """响应释放。"""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = False

    # ------------------------------------------------------------- 开始 / 重开
    def _check_play_button(self, mouse_pos) -> None:
        """在玩家单击 Play 按钮时开始新游戏。"""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        # 必须同时判断 not self.game_active，否则「点屏幕空白处也能重开」，
        # 而且游戏进行中乱点会把战绩清零（教材第 14.1.4 节踩过的坑）
        if button_clicked and not self.game_active:
            self._start_game()

    def _start_game(self) -> None:
        """重置一切，开始新的一局（教材练习 14.1 要求把这段抽成方法）。"""
        # 还原游戏设置（不还原的话第二局一开局就是上局的高速度、高难度）
        self.settings.initialize_dynamic_settings()

        # 重置游戏的统计信息
        self.stats.reset_stats()
        self.sb.prep_score()
        self.sb.prep_level()
        self.sb.prep_ships()

        # 清空外星人列表和子弹列表
        self.bullets.empty()
        self.aliens.empty()

        # 创建一个新的外星舰队，并将飞船放在屏幕底部的中央
        self._create_fleet()
        self.ship.center_ship()

        self.game_active = True

        # 隐藏光标（教材 14.1.6）
        pygame.mouse.set_visible(False)

    # ------------------------------------------------------------- 子弹
    def _fire_bullet(self) -> None:
        """创建一颗子弹，并将其加入编组 bullets。"""
        if len(self.bullets) < self.settings.bullets_allowed:
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)

    def _update_bullets(self) -> None:
        """更新子弹的位置并删除已消失的子弹。"""
        # 更新子弹的位置（Group.update() 会对每颗子弹调用 Bullet.update()）
        self.bullets.update()

        # 删除已消失的子弹：必须遍历 copy()，否则等于「边遍历边删元素」
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self) -> None:
        """响应子弹和外星人的碰撞。"""
        # 删除发生碰撞的子弹和外星人；返回的字典形如 {子弹: [被它击中的外星人, ...]}
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)

        if collisions:
            for aliens in collisions.values():
                self.stats.score += self.settings.alien_points * len(aliens)
            self.sb.prep_score()
            self.sb.check_high_score()

        if not self.aliens:
            # 整个舰队被消灭：进入新等级
            self._start_new_level()

    def _start_new_level(self) -> None:
        """清空子弹、生成新舰队、提高难度与等级（教材练习 14.6）。"""
        self.bullets.empty()
        self._create_fleet()
        self.settings.increase_speed()

        # 提高等级
        self.stats.level += 1
        self.sb.prep_level()

    # ------------------------------------------------------------- 外星人
    def _update_aliens(self) -> None:
        """检查是否有外星人位于屏幕边缘，并更新整个外星舰队的位置。"""
        self._check_fleet_edges()
        self.aliens.update()

        # 检测外星人和飞船之间的碰撞
        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        # 检查是否有外星人到达了屏幕的下边缘
        self._check_aliens_bottom()

    def _check_fleet_edges(self) -> None:
        """在有外星人到达边缘时采取相应的措施。"""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self) -> None:
        """将整个外星舰队向下移动，并改变它们的方向。"""
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def _check_aliens_bottom(self) -> None:
        """检查是否有外星人到达了屏幕的下边缘。"""
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= self.settings.screen_height:
                # 像飞船被撞到一样进行处理
                self._ship_hit()
                break

    def _create_fleet(self) -> None:
        """创建一个外星舰队。"""
        # 创建一个外星人，再不断添加，直到没有空间添加外星人为止
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size

        current_x, current_y = alien_width, alien_height
        while current_y < (self.settings.screen_height - 3 * alien_height):
            while current_x < (self.settings.screen_width - 2 * alien_width):
                self._create_alien(current_x, current_y)
                current_x += 2 * alien_width

            # 添加一行外星人后，重置 x 值并递增 y 值
            # （这两行属于外层 while：缩进错了就会出现教材提到的「舰队排列错乱」）
            current_x = alien_width
            current_y += 2 * alien_height

    def _create_alien(self, x_position, y_position) -> None:
        """创建一个外星人，并将其加入外星舰队。"""
        new_alien = Alien(self)
        new_alien.x = x_position
        new_alien.rect.x = x_position
        new_alien.rect.y = y_position
        self.aliens.add(new_alien)

    # ------------------------------------------------------------- 被撞 / 结束
    def _ship_hit(self) -> None:
        """响应飞船和外星人的碰撞。

        ⚠️ 与教材的一处**有意差异**：书里写的是

            if self.stats.ships_left > 0:
                self.stats.ships_left -= 1
                ...
            else:
                self.game_active = False

        先判断再减 1，会有一个 off-by-one：第 3 次被撞后 ships_left 变成 0，
        但游戏还没结束，要**第 4 次**被撞才 game over（等于白送一条命，
        而且记分牌上飞船数已经显示 0 了）。
        这里改成「先减 1，再判断是否还有船」，3 艘船用完即结束，
        行为与 README 的玩法说明一致。
        """
        # 先扣一条命，并同步记分牌上的小船图标
        self.stats.ships_left -= 1
        self.sb.prep_ships()

        if self.stats.ships_left > 0:
            # 清空外星人列表和子弹列表
            self.bullets.empty()
            self.aliens.empty()

            # 创建一个新的外星舰队，并将飞船放在屏幕底部的中央
            self._create_fleet()
            self.ship.center_ship()

            # 暂停（让玩家反应过来发生了什么）
            sleep(0.5)
        else:
            self.game_active = False
            self.stats.save_high_score()      # 练习 14.5：把最高分写进文件
            pygame.mouse.set_visible(True)

    # ------------------------------------------------------------- 绘制
    def _update_screen(self) -> None:
        """更新屏幕上的图像，并切换到新屏幕。"""
        self.screen.fill(self.settings.bg_color)

        for bullet in self.bullets.sprites():
            bullet.draw_bullet()

        self.ship.blitme()          # 先子弹后飞船 → 子弹像是从船里射出来的
        self.aliens.draw(self.screen)

        # 显示得分
        self.sb.show_score()

        # 如果游戏处于非活动状态，就绘制 Play 按钮
        if not self.game_active:
            self.play_button.draw_button()

        pygame.display.flip()


def main() -> None:
    """创建游戏实例并运行游戏（命令行入口 `alien-invasion` / `python -m alien_invasion`）。"""
    ai = AlienInvasion()
    try:
        ai.run_game()
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
