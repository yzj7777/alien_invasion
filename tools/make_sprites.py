"""生成游戏所需的两个位图素材：images/ship.bmp 与 images/alien.bmp。

教材第 12.4 / 13.2 节只说明「去找一张 .bmp 图片」，没有给素材文件。
本脚本用 Pillow「画」出素材，好处是：

1. 不涉及任何版权问题，可以随便改；
2. 背景色与 Settings.bg_color 完全一致（230, 230, 230），所以飞船/外星人
   看起来是「无缝」贴在屏幕上的——这正是教材选图时的要求；
3. 想换配色只要改下面的常量，重跑一次即可。

用法::

    uv run python tools/make_sprites.py            # 生成到 src/alien_invasion/images/
    uv run python tools/make_sprites.py --scale 6  # 只影响 docs 里的预览图放大倍数

实现要点：先用 4 倍超采样画图（超采样 = supersampling），再用 LANCZOS 缩小，
这样边缘会有细腻的抗锯齿，比手工一个像素一个像素点出来的效果更平滑。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

# ---------------------------------------------------------------- 颜色与尺寸
BG_COLOR = (230, 230, 230)          # 必须与 Settings.bg_color 相同
OUTLINE = (60, 74, 92)              # 描边：深蓝灰

SHIP_SIZE = (60, 48)                # 与教材里的 ship.bmp 尺寸一致
SHIP_BODY = (176, 186, 200)
SHIP_LIGHT = (232, 238, 245)
SHIP_DARK = (126, 138, 156)
CANOPY = (78, 140, 220)
CANOPY_LIGHT = (170, 210, 255)
FLAME_OUTER = (240, 150, 60)
FLAME_INNER = (255, 220, 120)

ALIEN_SIZE = (48, 40)               # 与教材里的 alien.bmp 尺寸一致
ALIEN_BODY = (110, 200, 120)
ALIEN_DARK = (66, 152, 84)
ALIEN_LIGHT = (186, 232, 176)
ALIEN_EYE = (38, 46, 56)

SS = 4                              # 超采样倍数


def _canvas(size: tuple[int, int], scale: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """创建一个带透明通道的超采样画布。"""
    img = Image.new("RGBA", (size[0] * scale, size[1] * scale), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _flatten(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """缩小到目标尺寸，并合成到纯色背景上（模拟 .bmp 没有透明通道的事实）。"""
    small = img.resize(size, Image.LANCZOS)
    bg = Image.new("RGB", size, BG_COLOR)
    bg.paste(small, (0, 0), small)
    return bg


# ------------------------------------------------------------------- 飞船
def draw_ship(size: tuple[int, int] = SHIP_SIZE) -> Image.Image:
    """画一艘朝上的武装飞船（教材 12.4.1 的 ship.bmp）。"""
    w, h = size[0] * SS, size[1] * SS
    img, d = _canvas(size, SS)

    cx = w // 2
    # 机身：从机首 (cx, 3) 向下张开的锥形
    hull = [
        (cx, 0.06 * h),
        (cx + 0.16 * w, 0.42 * h),
        (cx + 0.16 * w, 0.80 * h),
        (cx - 0.16 * w, 0.80 * h),
        (cx - 0.16 * w, 0.42 * h),
    ]
    d.polygon(hull, fill=SHIP_BODY, outline=OUTLINE, width=SS)

    # 机翼：左右各一片三角，向下外侧展开
    left_wing = [
        (cx - 0.16 * w, 0.50 * h),
        (cx - 0.44 * w, 0.86 * h),
        (cx - 0.16 * w, 0.86 * h),
    ]
    right_wing = [(2 * cx - x, y) for (x, y) in left_wing]
    d.polygon(left_wing, fill=SHIP_DARK, outline=OUTLINE, width=SS)
    d.polygon(right_wing, fill=SHIP_DARK, outline=OUTLINE, width=SS)

    # 机身中线高光，让船身有立体感
    d.polygon(
        [(cx, 0.10 * h), (cx + 0.05 * w, 0.40 * h), (cx + 0.05 * w, 0.78 * h), (cx - 0.05 * w, 0.78 * h)],
        fill=SHIP_LIGHT,
    )

    # 驾驶舱：一个蓝色椭圆
    d.ellipse(
        [cx - 0.10 * w, 0.30 * h, cx + 0.10 * w, 0.50 * h],
        fill=CANOPY,
        outline=OUTLINE,
        width=SS,
    )
    d.ellipse(
        [cx - 0.05 * w, 0.33 * h, cx + 0.02 * w, 0.42 * h],
        fill=CANOPY_LIGHT,
    )

    # 尾部两台发动机喷口
    for dx in (-0.10, 0.10):
        x0, y0 = cx + dx * w - 0.035 * w, 0.78 * h
        x1, y1 = cx + dx * w + 0.035 * w, 0.90 * h
        d.rectangle([x0, y0, x1, y1], fill=SHIP_DARK, outline=OUTLINE, width=SS)

    # 尾焰（外焰 + 内焰）
    for dx in (-0.10, 0.10):
        x = cx + dx * w
        d.polygon([(x - 0.04 * w, 0.90 * h), (x + 0.04 * w, 0.90 * h), (x, 1.0 * h)], fill=FLAME_OUTER)
        d.polygon([(x - 0.02 * w, 0.90 * h), (x + 0.02 * w, 0.90 * h), (x, 0.97 * h)], fill=FLAME_INNER)

    return _flatten(img, size)


# ----------------------------------------------------------------- 外星人
def draw_alien(size: tuple[int, int] = ALIEN_SIZE) -> Image.Image:
    """画一只小外星人（教材 13.2.1 的 alien.bmp）。"""
    w, h = size[0] * SS, size[1] * SS
    img, d = _canvas(size, SS)

    # 触角
    d.line([(0.30 * w, 0.26 * h), (0.22 * w, 0.02 * h)], fill=ALIEN_DARK, width=SS * 2)
    d.line([(0.70 * w, 0.26 * h), (0.78 * w, 0.02 * h)], fill=ALIEN_DARK, width=SS * 2)

    # 身体：上半圆顶 + 矩形肚子拼成一个「小怪物」
    d.pieslice([0.14 * w, 0.10 * h, 0.86 * w, 0.66 * h], 180, 360, fill=ALIEN_BODY, outline=OUTLINE, width=SS)
    d.rectangle([0.14 * w, 0.38 * h, 0.86 * w, 0.72 * h], fill=ALIEN_BODY)
    d.line([(0.14 * w, 0.38 * h), (0.14 * w, 0.72 * h)], fill=OUTLINE, width=SS)
    d.line([(0.86 * w, 0.38 * h), (0.86 * w, 0.72 * h)], fill=OUTLINE, width=SS)

    # 高光（上半部）与阴影（下半部），做出球体的感觉
    d.pieslice([0.18 * w, 0.13 * h, 0.82 * w, 0.55 * h], 200, 340, fill=ALIEN_LIGHT)
    d.rectangle([0.15 * w, 0.60 * h, 0.85 * w, 0.72 * h], fill=ALIEN_DARK)

    # 两只大眼睛
    for dx in (-0.16, 0.16):
        cx = w / 2 + dx * w
        d.ellipse([cx - 0.10 * w, 0.30 * h, cx + 0.10 * w, 0.54 * h], fill=ALIEN_EYE)
        d.ellipse([cx - 0.04 * w, 0.33 * h, cx + 0.00 * w, 0.40 * h], fill=(255, 255, 255))

    # 四条小腿，让轮廓更像「入侵者」
    for i, dx in enumerate((-0.26, -0.10, 0.10, 0.26)):
        x = w / 2 + dx * w
        y1 = 0.86 * h if i in (0, 3) else 0.80 * h
        d.rectangle([x - 0.05 * w, 0.70 * h, x + 0.05 * w, y1], fill=ALIEN_DARK, outline=OUTLINE, width=SS)

    return _flatten(img, size)


# ------------------------------------------------------------------- 入口
def main() -> None:
    parser = argparse.ArgumentParser(description="生成 ship.bmp / alien.bmp")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src" / "alien_invasion" / "images",
        help="输出目录（默认 src/alien_invasion/images/）",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=None,
        help="额外输出一张放大预览图（PNG），方便在编辑器/文档里看清楚",
    )
    parser.add_argument("--scale", type=int, default=5, help="预览图放大倍数（默认 5）")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    ship = draw_ship()
    alien = draw_alien()

    ship_path = args.out / "ship.bmp"
    alien_path = args.out / "alien.bmp"
    ship.save(ship_path, "BMP")
    alien.save(alien_path, "BMP")
    print(f"已生成 {ship_path}  ({ship.width}x{ship.height}, {ship_path.stat().st_size} 字节)")
    print(f"已生成 {alien_path} ({alien.width}x{alien.height}, {alien_path.stat().st_size} 字节)")

    if args.preview:
        s = args.scale
        big_ship = ship.resize((ship.width * s, ship.height * s), Image.NEAREST)
        big_alien = alien.resize((alien.width * s, alien.height * s), Image.NEAREST)
        gap = 20
        canvas = Image.new(
            "RGB",
            (big_ship.width + big_alien.width + gap * 3, max(big_ship.height, big_alien.height) + gap * 2),
            BG_COLOR,
        )
        canvas.paste(big_ship, (gap, gap))
        canvas.paste(big_alien, (gap * 2 + big_ship.width, gap))
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.preview)
        print(f"已生成预览图 {args.preview}（放大 {s} 倍）")


if __name__ == "__main__":
    main()
