"""《外星人入侵》逻辑测试。

运行::

    uv run pytest -q

这些测试其实就是「每一步到底对不对」的机器化版本，和教程 docs/教程.md
里的自测清单一一对应：每讲完一节，就跑对应的一组测试。
"""

from __future__ import annotations

import pygame
import pytest

from alien_invasion import Alien, Bullet, Settings, Ship

from conftest import step


# ============================================================ 第 12 章：武装飞船
class TestChapter12:
    """窗口、飞船、移动、子弹。"""

    def test_settings_defaults(self):
        s = Settings()
        assert (s.screen_width, s.screen_height) == (1200, 800)
        assert s.bg_color == (230, 230, 230)
        assert s.ship_limit == 3
        assert s.bullets_allowed == 3

    def test_window_created_with_settings_size(self, game):
        assert game.screen.get_size() == (
            game.settings.screen_width,
            game.settings.screen_height,
        )
        assert pygame.display.get_caption()[0] == "Alien Invasion"

    def test_ship_starts_at_bottom_center(self, game):
        assert game.ship.rect.midbottom == game.screen.get_rect().midbottom
        assert game.ship.moving_left is False and game.ship.moving_right is False

    def test_ship_moves_right_and_left(self, game, fake):
        game._start_game()
        x0 = game.ship.rect.x

        fake.key_down(pygame.K_RIGHT)
        step(game, 10)
        assert game.ship.rect.x > x0

        x1 = game.ship.rect.x
        fake.key_up(pygame.K_RIGHT)
        fake.key_down(pygame.K_LEFT)
        step(game, 10)
        assert game.ship.rect.x < x1
        fake.key_up(pygame.K_LEFT)

    def test_ship_stops_at_screen_edges(self, game, fake):
        """练习 12.4 的要求：飞船不能移出屏幕。"""
        game._start_game()
        fake.key_down(pygame.K_RIGHT)
        step(game, 2000)
        assert game.ship.rect.right <= game.screen.get_rect().right

        fake.key_up(pygame.K_RIGHT)
        fake.key_down(pygame.K_LEFT)
        step(game, 2000)
        assert game.ship.rect.left >= 0
        fake.key_up(pygame.K_LEFT)

    def test_q_key_stops_main_loop(self, game, fake):
        game.running = True
        fake.key_down(pygame.K_q)
        game._check_events()
        assert game.running is False

    def test_fire_bullet_respects_limit(self, game, fake):
        game._start_game()
        for _ in range(10):                     # 疯狂按空格
            fake.key_down(pygame.K_SPACE)
            game._check_events()
        assert len(game.bullets) == game.settings.bullets_allowed

    def test_bullet_flies_up_and_is_removed(self, game):
        game._start_game()
        game._fire_bullet()
        bullet = game.bullets.sprites()[0]
        assert bullet.rect.midtop == game.ship.rect.midtop

        y0 = bullet.rect.y
        step(game, 30)
        assert game.bullets.sprites()[0].rect.y < y0

        step(game, 400)                          # 一直飞，飞出屏幕后应被删除
        assert len(game.bullets) == 0


# ============================================================ 第 13 章：外星人
class TestChapter13:
    """外星人、舰队、移动、碰撞、结束游戏。"""

    def test_fleet_is_created_in_grid(self, game):
        aliens = game.aliens.sprites()
        assert len(aliens) > 50
        rows = {a.rect.y for a in aliens}
        assert len(rows) > 3                     # 多行
        # 同一行里，相邻外星人之间留有一个外星人的宽度
        first_row = sorted([a.rect.x for a in aliens if a.rect.y == min(rows)])
        assert first_row[1] - first_row[0] == 2 * aliens[0].rect.width

    def test_alien_moves_with_fleet_direction(self, game):
        alien = game.aliens.sprites()[0]
        x0 = alien.rect.x
        game.settings.fleet_direction = 1
        game.aliens.update()
        assert game.aliens.sprites()[0].rect.x > x0

        game.settings.fleet_direction = -1
        x1 = game.aliens.sprites()[0].rect.x
        game.aliens.update()
        assert game.aliens.sprites()[0].rect.x < x1

    def test_fleet_drops_and_reverses_at_edge(self, game):
        game._start_game()
        game.settings.fleet_direction = 1
        # 把舰队整体顶到右边缘
        for alien in game.aliens.sprites():
            alien.rect.right = game.settings.screen_width
        y0 = {a.rect.y for a in game.aliens.sprites()}

        game._check_fleet_edges()

        assert game.settings.fleet_direction == -1
        assert {a.rect.y for a in game.aliens.sprites()} == {y + game.settings.fleet_drop_speed for y in y0}

    def test_bullet_kills_alien_and_scores(self, game):
        game._start_game()
        alien = game.aliens.sprites()[0]
        game._fire_bullet()
        bullet = game.bullets.sprites()[0]

        # 把子弹搬到外星人身上，模拟「打中」。
        # 注意 _update_bullets() 会先让子弹上移 bullet_speed 像素再判碰撞，
        # 所以要让两者真正重叠（对准中心），而不是刚好贴着边缘。
        bullet.rect.center = alien.rect.center
        bullet.y = float(bullet.rect.y)
        game._update_bullets()

        assert alien not in game.aliens
        assert game.stats.score == game.settings.alien_points

    def test_one_bullet_can_kill_several_aliens(self, game):
        """教材 13.5 的调试技巧：把子弹调宽，一发能打穿同一排的一串外星人。

        这也是「一次碰撞要按击落数量加分」那条逻辑的验证点：
        如果不遍历 collisions.values()，这里只会加 50 分而不是 150 分。
        """
        game._start_game()
        game.settings.bullet_width = 400          # 调试用「横条子弹」

        # 清空舰队，只精确布置同一排的三个外星人（y 相同、x 相邻）
        game.aliens.empty()
        for x in (500, 600, 700):
            game._create_alien(x, 100)
        targets = game.aliens.sprites()
        assert len(targets) == 3

        # 先记下当前分值：这一发会把舰队清空 → 立刻升级 → alien_points 变成 75，
        # 如果等碰撞之后再读 settings.alien_points，断言就会莫名其妙地失败
        points_before = game.settings.alien_points

        game._fire_bullet()
        bullet = game.bullets.sprites()[0]
        bullet.rect.centerx = 600                  # 横条覆盖 400~800
        bullet.rect.centery = targets[0].rect.centery
        bullet.y = float(bullet.rect.y)
        game._update_bullets()

        for alien in targets:
            assert alien not in game.aliens
        assert game.stats.score == points_before * len(targets)
        assert game.stats.level == 2               # 顺带验证：清空舰队即升级

    def test_clearing_fleet_starts_new_level(self, game):
        game._start_game()
        bullets_before = len(game.bullets)
        speed_before = game.settings.alien_speed

        game.aliens.empty()
        game._fire_bullet()
        game._update_bullets()                   # 触发「舰队空了」的分支

        assert len(game.bullets) == 0            # 子弹被清空
        assert len(game.aliens) > 0              # 新舰队已生成
        assert game.stats.level == 2
        assert game.settings.alien_speed == pytest.approx(speed_before * game.settings.speedup_scale)
        assert bullets_before <= 1

    def test_ship_hit_costs_a_ship_and_rebuilds_fleet(self, game):
        game._start_game()
        game.aliens.empty()
        game.ship.rect.midbottom = game.screen.get_rect().midbottom
        Alien_at_ship = game._create_alien(game.ship.rect.centerx, game.ship.rect.centery)

        game._update_aliens()

        assert game.stats.ships_left == game.settings.ship_limit - 1
        assert len(game.aliens) > 0              # 重建了舰队
        assert game.ship.rect.midbottom == game.screen.get_rect().midbottom

    def test_alien_reaching_bottom_costs_a_ship(self, game):
        game._start_game()
        alien = game.aliens.sprites()[0]
        alien.rect.bottom = game.settings.screen_height

        game._update_aliens()
        assert game.stats.ships_left == game.settings.ship_limit - 1

    def test_game_over_after_three_hits(self, game):
        game._start_game()
        for _ in range(game.settings.ship_limit):
            game._ship_hit()
        assert game.stats.ships_left == 0
        assert game.game_active is False
        # 结束后光标要回来，否则菜单里点不到 Play
        assert pygame.mouse.get_visible() is True

    def test_fleet_is_rebuilt_after_a_hit(self, game):
        """被撞之后舰队和飞船位置都要复位，否则下一局开局就在外星人堆里。"""
        game._start_game()
        game.ship.rect.x = 0
        game._ship_hit()

        assert game.game_active is True
        assert game.ship.rect.midbottom == game.screen.get_rect().midbottom
        assert len(game.bullets) == 0
        rows = {a.rect.y for a in game.aliens.sprites()}
        assert min(rows) == game.aliens.sprites()[0].rect.height


# ============================================================ 第 14 章：记分
class TestChapter14:
    """Play 按钮、难度递增、记分牌。"""

    def test_game_starts_inactive_with_button_centered(self, game):
        assert game.game_active is False
        assert game.play_button.rect.center == game.screen.get_rect().center

    def test_clicking_play_starts_game(self, game, fake):
        fake.click(game.play_button.rect.center)
        game._check_events()
        assert game.game_active is True
        assert pygame.mouse.get_visible() is False   # 开始游戏后隐藏光标

    def test_clicking_elsewhere_does_nothing(self, game, fake):
        """教材踩过的坑：点空白处也能重开游戏。"""
        fake.click((10, 10))
        game._check_events()
        assert game.game_active is False

    def test_p_key_starts_game(self, game, fake):
        """练习 14.1：把开始游戏抽成 _start_game()，P 键也能调用。"""
        fake.key_down(pygame.K_p)
        game._check_events()
        assert game.game_active is True

    def test_restart_resets_stats_and_difficulty(self, game, fake):
        game._start_game()
        game.settings.increase_speed()
        game.settings.increase_speed()
        game.stats.score = 12345
        game.stats.level = 7
        game.stats.ships_left = 1
        game.aliens.empty()

        game._ship_hit()                          # 先假装游戏结束
        game.game_active = False
        fake.click(game.play_button.rect.center)
        game._check_events()

        assert game.stats.score == 0
        assert game.stats.level == 1
        assert game.stats.ships_left == game.settings.ship_limit
        assert game.settings.alien_speed == 1.0   # 回到初始难度
        assert len(game.aliens) > 0               # 重新铺开舰队

    def test_score_is_rendered_rounded(self, game):
        game._start_game()
        game.stats.score = 1234
        game.sb.prep_score()
        assert game.sb.score_rect.right == game.screen.get_rect().right - 20

    def test_high_score_survives_reset(self, game):
        game._start_game()
        game.stats.score = 500
        game.sb.check_high_score()
        assert game.stats.high_score == 500

        game.stats.reset_stats()                  # 相当于重开一局
        assert game.stats.score == 0
        assert game.stats.high_score == 500       # 最高分不该被重置

    def test_difficulty_scales_with_level(self, game):
        game._start_game()
        base_points = game.settings.alien_points
        for _ in range(3):
            game.aliens.empty()
            game._update_bullets()

        assert game.stats.level == 4
        assert game.settings.alien_points > base_points
        assert game.settings.alien_speed > 1.0


# ============================================================ 素材与包结构
class TestAssets:
    def test_images_exist_and_match_background(self):
        """素材背景色必须和游戏背景色一致，否则看起来像贴了张纸。"""
        from alien_invasion.settings import IMAGES_DIR

        for name, expected_size in (("ship.bmp", (60, 48)), ("alien.bmp", (48, 40))):
            path = IMAGES_DIR / name
            assert path.exists(), f"缺少素材 {path}"
            surface = pygame.image.load(str(path))
            assert surface.get_size() == expected_size
            assert surface.get_at((0, 0))[:3] == Settings().bg_color

    def test_ship_and_alien_are_sprites(self, game):
        """教材第 14.3 节：飞船和记分牌上的小飞船必须是精灵（能进编组）。"""
        assert isinstance(game.ship, Ship)
        assert isinstance(game.aliens.sprites()[0], Alien)
        assert len(game.sb.ships) == game.settings.ship_limit
        assert isinstance(game._fire_bullet() or game.bullets.sprites()[0], Bullet)


# ============================================================ 窗口自适应
class TestWindowFit:
    """小屏幕上窗口放不下时的自动缩放（教材没有，但真实笔记本上很需要）。

    1280x800 的 MacBook、1366x768 的老笔记本上，1200x800 的窗口比可用区域还高，
    底部会被切掉——玩家看到的是「飞船和 Play 按钮不见了」，很容易以为游戏坏了。
    """

    def test_small_display_shrinks_window_but_keeps_everything_onscreen(self):
        from alien_invasion import AlienInvasion

        pygame.init()
        game = AlienInvasion(event_source=lambda: [], fit_window=True)
        try:
            info = pygame.display.Info()
            avail_w, avail_h = info.current_w, info.current_h
            if avail_w > 0 and avail_h > 0:          # 无头环境读不到就跳过断言
                assert game.settings.screen_width <= avail_w
                assert game.settings.screen_height <= avail_h
            w, h = game.screen.get_size()
            # 关键元素必须都在屏幕内
            assert 0 < game.ship.rect.bottom <= h
            assert game.screen.get_rect().contains(game.play_button.rect)
            assert len(game.aliens) > 0
        finally:
            pygame.quit()

    def test_explicit_size_is_untouched_when_disabled(self):
        from alien_invasion import AlienInvasion

        pygame.init()
        game = AlienInvasion(event_source=lambda: [], fit_window=False)
        try:
            assert game.screen.get_size() == (1200, 800)
            assert len(game.aliens) == 88
            assert game.ship.rect.bottom == 800
        finally:
            pygame.quit()

    def test_fleet_still_centered_on_a_custom_screen(self):
        """换分辨率之后，记分牌/按钮的位置也要跟着走（教材的定位都没写死坐标）。"""
        from alien_invasion import AlienInvasion

        pygame.init()
        game = AlienInvasion(event_source=lambda: [], fit_window=False)
        try:
            game.settings.screen_width, game.settings.screen_height = 900, 650
            game.screen = pygame.display.set_mode((900, 650))
            game.ship.screen_rect = game.screen.get_rect()
            game.play_button.__init__(game, "Play")      # 重新按新尺寸布局
            game.sb.screen_rect = game.screen.get_rect()

            game._start_game()
            game.sb.prep_score()
            game.sb.prep_high_score()
            assert game.play_button.rect.center == game.screen.get_rect().center
            assert game.sb.score_rect.right == game.screen.get_rect().right - 20
            assert game.ship.rect.midbottom == game.screen.get_rect().midbottom
        finally:
            pygame.quit()
