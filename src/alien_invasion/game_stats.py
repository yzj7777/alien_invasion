"""游戏统计信息（教材 14.1.2 引入，14.3.3 加入最高分）。"""

from __future__ import annotations

from pathlib import Path


class GameStats:
    """跟踪游戏的统计信息。"""

    def __init__(self, ai_game) -> None:
        """初始化统计信息。"""
        self.settings = ai_game.settings
        self.reset_stats()

        # 在任何情况下都不应重置最高分，所以它不能放进 reset_stats() 里
        # （放进去的话「重开一局最高分就归零」，教材第 14.3.3 节特别提醒过）
        self.high_score = self._load_high_score()

    def reset_stats(self) -> None:
        """初始化在游戏运行期间可能变化的统计信息。"""
        self.ships_left = self.settings.ship_limit
        self.score = 0
        self.level = 1

    # ---------------------------------------------------------- 练习 14.5 参考实现
    # 教材的练习 14.5 要求「把最高分保存到文件里」。这里做成可选功能：
    # Settings.high_score_file 保持 None 时行为与教材完全一致（只在内存里记最高分）；
    # 想启用就把它改成 Path("high_score.txt")。
    def _load_high_score(self) -> int:
        """从文件读取历史最高分；没启用或文件不存在/损坏时返回 0。"""
        path = self.settings.high_score_file
        if path is None:
            return 0
        try:
            return int(Path(path).read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return 0

    def save_high_score(self) -> None:
        """把当前最高分写入文件（未启用持久化时什么都不做）。"""
        path = self.settings.high_score_file
        if path is None:
            return
        try:
            Path(path).write_text(str(self.high_score), encoding="utf-8")
        except OSError:
            pass  # 磁盘写不进去也不该让游戏崩掉
