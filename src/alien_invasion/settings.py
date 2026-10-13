"""游戏《外星人入侵》的全部设置（教材 12.3.4 节引入，14.2 节补充动态设置）。

设计要点（教材反复强调的一点）：**把所有「数字」集中到一个类里**。
这样调平衡（速度、子弹数量、加分幅度）时只需要改这个文件，
不用去主程序里到处找散落的字面量。
"""

from __future__ import annotations

from pathlib import Path

# 素材目录：基于本文件位置计算，而不是「当前工作目录」。
# 教材写的是相对路径 'images/ship.bmp'，那样只有在项目文件夹里运行才找得到图片；
# 用 __file__ 定位则无论从哪里运行都没问题。
IMAGES_DIR = Path(__file__).resolve().parent / "images"


class Settings:
    """存储游戏《外星人入侵》中所有设置的类。"""

    def __init__(self) -> None:
        """初始化游戏的静态设置（这些值在游戏过程中不会变）。"""
        # --- 屏幕设置 ---
        self.screen_width = 1200
        self.screen_height = 800
        self.bg_color = (230, 230, 230)  # 浅灰，和图片背景色一致
        self.fps = 60                    # 主循环帧率（教材 12.3.2）

        # 窗口自适应：教材固定 1200x800。但如果用户的屏幕比它小（13 寸笔记本、
        # 1280x800 的老 MacBook、带缩放的外接屏……），窗口会超出屏幕，
        # 结果就是「飞船和 Play 按钮在屏幕外面，根本没法玩」。
        # 打开这个开关后，窗口会自动缩到屏幕的 max_screen_ratio 倍以内。
        self.fit_to_display = True
        self.max_screen_ratio = 0.9

        # --- 飞船设置 ---
        self.ship_limit = 3              # 允许损失 3 艘飞船（教材 13.6）

        # --- 子弹设置 ---
        self.bullet_width = 3
        self.bullet_height = 15
        self.bullet_color = (60, 60, 60)
        self.bullets_allowed = 3         # 屏幕上同时存在的子弹数上限
        # 调试小技巧（教材 13.5 提示）：把 bullet_width 调成 300 再来玩，
        # 子弹变成「一根横条」，一打一片，方便快速验证计分/升级逻辑。

        # --- 外星人设置 ---
        self.fleet_drop_speed = 10       # 撞到边缘后整队下移的距离

        # --- 游戏节奏（第 14 章）---
        self.speedup_scale = 1.1         # 每升一级，速度乘这个倍率
        self.score_scale = 1.5           # 每升一级，外星人分值乘这个倍率

        # --- 练习 14.5：最高分持久化（默认关闭；想启用就改成 Path("high_score.txt")）---
        self.high_score_file: Path | None = None

        # 动态设置必须在最后调用，它负责初始化「随游戏变化」的那一组值
        self.initialize_dynamic_settings()

    def initialize_dynamic_settings(self) -> None:
        """初始化随游戏进行而变化的设置（每次开始新游戏都要调用一次）。"""
        self.ship_speed = 1.5
        self.bullet_speed = 2.5
        self.alien_speed = 1.0

        # fleet_direction 为 1 表示向右，为 -1 表示向左
        self.fleet_direction = 1

        # 记分设置
        self.alien_points = 50

    def increase_speed(self) -> None:
        """提高速度设置的值和外星人的分值（每消灭一个舰队调用一次）。"""
        self.ship_speed *= self.speedup_scale
        self.bullet_speed *= self.speedup_scale
        self.alien_speed *= self.speedup_scale

        self.alien_points = int(self.alien_points * self.score_scale)
