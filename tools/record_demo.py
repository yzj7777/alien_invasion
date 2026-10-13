"""自动驾驶式录屏：让程序自己玩一局，把关键画面截下来。

用途有两个：
1. 给教程 docs/教程.md 生成插图（Play 按钮、舰队、开火、击落、升级、被撞、结束）；
2. 做一次「端到端冒烟测试」——如果游戏有逻辑漏洞，自动驾驶会先卡住，
  脚本会打印它跑到哪一步就停了。

原理：利用 `AlienInvasion(on_frame=...)` 这个钩子，每一帧都回调一次我们的
自动驾驶函数；它根据画面状态生成「按键事件」，塞回游戏的事件队列。
同时为了录屏够快，把两个「等时间」的地方关掉：

* `clock.tick(60)` → 不限制帧率（否则跑 5 分钟游戏时间要真等 5 分钟）；
* `sleep(0.5)`（被撞后的停顿）→ 直接跳过。

用法::

    uv run python tools/record_demo.py                  # 截图 + GIF
    uv run python tools/record_demo.py --no-gif         # 只要截图
    uv run python tools/record_demo.py --out docs/images
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import alien_invasion.game as game_module  # noqa: E402
from alien_invasion import AlienInvasion  # noqa: E402


class FastClock:
    """顶替 pygame.time.Clock 的假时钟：tick() 什么都不做，于是游戏全速跑。

    为什么不能直接 `game.clock.tick = lambda fps: 0`？
    因为 pygame.time.Clock 是 C 扩展类型，它的 tick 是只读属性，赋值会报
    `AttributeError: 'pygame.time.Clock' object attribute 'tick' is read-only`。
    换成自己写的对象就绕过去了。
    """

    def tick(self, fps: int = 0) -> int:
        return 0


def no_frame_limit(game) -> None:
    """把帧率限制和碰撞停顿都关掉，让录屏工具能飞快地把整局跑完。"""
    game.clock = FastClock()
    game_module.sleep = lambda seconds: None


class Autopilot:
    """一个很简单的自动玩家：瞄准最下面那一排的外星人，对准了就开火。"""

    def __init__(self, recorder: "Recorder") -> None:
        self.rec = recorder
        self.pending: list[pygame.event.Event] = []
        self.held = {"left": False, "right": False}
        self.started = False

    # ---------------------------------------------------------- 输入
    def _press(self, key: int) -> None:
        self.pending.append(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))

    def _release(self, key: int) -> None:
        self.pending.append(pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode="", scancode=0))

    def _set_dir(self, direction: str) -> None:
        """direction 取 'left' / 'right' / 'none'，只在状态变化时发事件。"""
        for name, key in (("left", pygame.K_LEFT), ("right", pygame.K_RIGHT)):
            want = name == direction
            if want and not self.held[name]:
                self._press(key)
                self.held[name] = True
            elif not want and self.held[name]:
                self._release(key)
                self.held[name] = False

    def events(self) -> list[pygame.event.Event]:
        """游戏每帧调用：交出这一帧要注入的事件。"""
        out, self.pending = self.pending, []
        return out

    # ---------------------------------------------------------- 决策
    def __call__(self, game: AlienInvasion) -> None:
        self.rec.tick(game)

        if not game.game_active:
            if not self.started:
                # 停在标题界面，先让录屏截一张「Play 按钮」的图，再点它
                self.rec.want("00-play-button", after=4)
                if self.rec.frame > 8:
                    self.pending.append(
                        pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, pos=game.play_button.rect.center, button=1
                        )
                    )
                    self.started = True
            else:
                # 游戏结束：记录最终画面后收工
                self.rec.want("06-game-over", after=2)
                if self.rec.frame > self.rec.death_frame + 30:
                    game.quit()
            self._set_dir("none")
            return

        self._play(game)

    def _play(self, game: AlienInvasion) -> None:
        aliens = game.aliens.sprites()
        if not aliens:
            return

        # 目标：位置最低（最危险）的外星人；同样低时选离飞船最近的
        target = min(
            aliens,
            key=lambda a: (-a.rect.bottom, abs(a.rect.centerx - game.ship.rect.centerx)),
        )
        dx = target.rect.centerx - game.ship.rect.centerx

        if dx < -6:
            self._set_dir("left")
        elif dx > 6:
            self._set_dir("right")
        else:
            self._set_dir("none")
            if len(game.bullets) < game.settings.bullets_allowed:
                self._press(pygame.K_SPACE)


class Recorder:
    """记录帧数、判断何时截图、收集 GIF 帧。"""

    def __init__(
        self,
        out_dir: Path,
        gif: bool,
        gif_frames: int,
        scale: float,
        colors: int,
        gif_stride: int = 6,
    ) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.frame = 0
        self.death_frame = 10**9
        self.saved: list[str] = []
        self.shots: list[tuple[int, str]] = []      # 待办的截图：(目标帧, 名字)
        # 每 stride 个游戏帧取一个画面；游戏 60fps，所以播放时长 = stride/60 秒
        self.frame_duration_ms = int(gif_stride / 60 * 1000)

        # 里程碑状态机
        self.was_active = False
        self.saw_bullet = False
        self.saw_score = False
        self.saw_level2 = False
        self.saw_ship_hit = False

        # GIF 相关
        self.want_gif = gif
        self.gif_limit = gif_frames
        self.scale = scale
        self.colors = colors
        self.gif_stride = gif_stride
        self.gif_frames_data: list[Image.Image] = []

    # ---------------------------------------------------------- 工具
    def want(self, name: str, after: int = 0, at_frame: int | None = None) -> None:
        """预约一张截图：在「当前帧 + after」时保存。

        注意不能写成「想截图就立刻判断 frame >= target」——那样第一次调用时
        target 还在未来，函数直接返回，以后再也没有机会触发，图就丢了。
        所以这里用一个待办队列（schedule）来记着这件事。
        """
        target = self.frame + after if at_frame is None else at_frame
        scheduled = [n for _, n in self.shots]
        if name in self.saved or name in scheduled:
            return
        self.shots.append((target, name))

    def _save(self, name: str) -> None:
        if name in self.saved:
            return
        path = self.out_dir / f"{name}.png"
        pygame.image.save(self._screen, str(path))
        self.saved.append(name)
        print(f"  ✓ 截图 {path.relative_to(ROOT)}  (第 {self.frame} 帧)", flush=True)

    # ---------------------------------------------------------- 每帧回调
    def tick(self, game: AlienInvasion) -> None:
        self.frame += 1
        self._screen = game.screen

        # 到点的截图任务：全部执行掉
        due = [name for target, name in self.shots if self.frame >= target]
        for name in due:
            self._save(name)
        self.shots = [(t, n) for t, n in self.shots if n not in due]

        # --- 收集 GIF 帧（只录开局那一段，够展示玩法了）---
        if (
            self.want_gif
            and len(self.gif_frames_data) < self.gif_limit
            and self.frame % self.gif_stride == 0
        ):
            raw = pygame.image.tostring(game.screen, "RGB")
            img = Image.frombytes("RGB", game.screen.get_size(), raw)
            w, h = int(img.width * self.scale), int(img.height * self.scale)
            self.gif_frames_data.append(img.resize((w, h), Image.BILINEAR))

        # --- 里程碑判断 ---
        if game.game_active and not self.was_active:
            self.was_active = True
            self.want("01-fleet-and-hud", after=25)

        if game.game_active:
            if game.bullets and not self.saw_bullet:
                self.saw_bullet = True
                self.want("02-firing", after=6)
            if game.stats.score > 0 and not self.saw_score:
                self.saw_score = True
                self.want("03-aliens-shot-score", after=1)
            if game.stats.level >= 2 and not self.saw_level2:
                self.saw_level2 = True
                self.want("04-level-up", after=6)
            if game.stats.ships_left < game.settings.ship_limit and not self.saw_ship_hit:
                self.saw_ship_hit = True
                self.want("05-ship-hit", after=3)

            if game.stats.level >= 2 and self.saw_score and self.saw_ship_hit and self.saw_level2:
                self.milestones_done = True

        if not game.game_active and self.was_active:
            self.death_frame = min(self.death_frame, self.frame)

    # ---------------------------------------------------------- 收尾
    def write_gif(self, path: Path) -> None:
        """写 GIF。体积优化的关键：所有帧共用一张调色板。

        如果每帧各自 `convert("P", ADAPTIVE)`，每帧都换一套颜色表，帧与帧之间
        几乎没有可复用的信息，体积会大一倍以上（实测 3.0MB → 1MB 左右）。
        共用调色板 + 不抖动（dither=NONE）后，GIF 才能只记录「改了哪些像素」。
        对《外星人入侵》这种大面积纯色、只有少量元素移动的画面效果特别好。
        """
        if not self.gif_frames_data:
            return
        path.parent.mkdir(parents=True, exist_ok=True)

        # 用第一帧的调色板当「公共调色板」，其余帧统一映射到它上面
        palette = self.gif_frames_data[0].quantize(colors=self.colors, method=Image.MEDIANCUT)
        frames = [palette] + [
            img.quantize(palette=palette, dither=Image.Dither.NONE)
            for img in self.gif_frames_data[1:]
        ]

        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=self.frame_duration_ms,
            loop=0,
            optimize=True,
            disposal=1,
        )
        print(f"  ✓ GIF {path.relative_to(ROOT)}  ({len(frames)} 帧, "
              f"{path.stat().st_size / 1024:.0f} KB)")


def capture_wide_bullet_debug(out_dir: Path) -> None:
    """单独截一张「教材 13.5 调试技巧：把子弹调宽」的图。"""
    rec = Recorder(out_dir, gif=False, gif_frames=0, scale=1.0, colors=64)

    def on_frame(game: AlienInvasion) -> None:
        rec.tick(game)
        if rec.frame == 3:
            game.settings.bullet_width = 300        # 调试用「横条子弹」
            game._start_game()
            game.settings.bullet_width = 300        # _start_game 不会动静态设置，这里再保险一次
        elif rec.frame == 12:
            game.ship.rect.midbottom = (game.settings.screen_width // 2, game.settings.screen_height)
            game.ship.x = float(game.ship.rect.x)
            game._fire_bullet()
        elif rec.frame == 40:
            game._fire_bullet()
        elif rec.frame == 46:
            rec.want("07-wide-bullet-debug")
        elif rec.frame > 60:
            game.quit()

    game = AlienInvasion(event_source=lambda: [], on_frame=on_frame, fit_window=False)
    no_frame_limit(game)
    game.run_game()


def main() -> None:
    parser = argparse.ArgumentParser(description="自动驾驶录屏 + 截图")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "images")
    parser.add_argument("--gif", dest="gif", action="store_true", default=True)
    parser.add_argument("--no-gif", dest="gif", action="store_false")
    parser.add_argument("--gif-frames", type=int, default=120, help="GIF 最多收录多少个画面")
    parser.add_argument("--gif-stride", type=int, default=6, help="每几个游戏帧取一个画面（60/6=10fps）")
    parser.add_argument("--gif-scale", type=float, default=0.38)
    parser.add_argument("--gif-colors", type=int, default=48)
    parser.add_argument("--max-frames", type=int, default=400000, help="安全上限，防止跑飞")
    args = parser.parse_args()

    print("开始自动驾驶（不限制帧率，所以比真实游玩快很多）…")
    rec = Recorder(
        args.out, args.gif, args.gif_frames, args.gif_scale, args.gif_colors, args.gif_stride
    )
    autopilot = Autopilot(rec)

    game = AlienInvasion(event_source=autopilot.events, on_frame=autopilot, fit_window=False)
    no_frame_limit(game)

    # 安全网：帧数超上限就强制结束
    original_tick = rec.tick

    def guarded_tick(g: AlienInvasion) -> None:
        original_tick(g)
        if rec.frame > args.max_frames:
            g.quit()

    rec.tick = guarded_tick

    game.run_game()

    print(f"\n自动驾驶结束：共 {rec.frame} 帧（约 {rec.frame / 60:.0f} 秒游戏时间）")
    print(f"  最高等级 {game.stats.level} / 得分 {game.stats.score} / 剩余飞船 {game.stats.ships_left}")
    print(f"  游戏是否结束：{'是' if not game.game_active else '否（达到帧数上限）'}")

    # 补一张「结束画面」：如果游戏是自己打完的，上面已经截过了
    if not game.game_active and "06-game-over" not in rec.saved:
        rec._save("06-game-over")   # 收尾补一张：Play 按钮 + 最高分同框

    capture_wide_bullet_debug(args.out)
    if args.gif:
        rec.write_gif(args.out / "demo.gif")

    print("\n已生成：")
    for name in sorted(rec.saved):
        print("  -", (args.out / f"{name}.png").relative_to(ROOT))
    pygame.quit()


if __name__ == "__main__":
    main()
