# 项目 1：外星人入侵（Alien Invasion）——学习整理

> 来源：《Python 编程从入门到实践》（第 3 版）第二部分 · 项目 1（第 12～14 章）
> 主题：使用 **Pygame** 开发 2D 射击游戏《外星人入侵》

---

## 目录

- [一、项目概览](#一项目概览)
- [二、项目结构与架构](#二项目结构与架构)
- [三、第 12 章　武装飞船](#三第-12-章武装飞船)
- [四、第 13 章　外星人](#四第-13-章外星人)
- [五、第 14 章　记分](#五第-14-章记分)
- [六、核心概念速查表](#六核心概念速查表)
- [七、游戏参数总表](#七游戏参数总表)
- [八、常见坑与调试提示](#八常见坑与调试提示)
- [九、练习清单](#九练习清单)
- [附录：项目最终完整代码](#附录项目最终完整代码)

---

## 一、项目概览

### 1.1 游戏玩法说明（开发计划）

在游戏《外星人入侵》中：

- 玩家控制一艘**最初出现在屏幕底部中央**的武装飞船；
- 使用**方向键（←/→）左右移动**飞船，使用**空格键射击**；
- 游戏开始时，一个**外星舰队**出现在天空中并向屏幕下方移动，玩家的任务是消灭这些外星人；
- 玩家将外星人消灭干净后，会出现一个**新的外星舰队，其移动速度更快**（等级提高，节奏加快）；
- 只要有外星人**撞到飞船**或**到达屏幕下边缘**，玩家就**损失一艘飞船**；
- 玩家损失**三艘飞船**后，**游戏结束**，通过 Play 按钮可重新开始。

### 1.2 技术要点

| 项目 | 说明 |
| --- | --- |
| 语言 | Python |
| 库 | Pygame（安装：`python -m pip install --user pygame`） |
| 图像 | 位图（.bmp）文件：`ship.bmp`、`alien.bmp`，放在 `images/` 文件夹 |
| 核心思想 | 面向对象（每个游戏元素一个类）+ 事件循环 + 不断重构 |
| 项目文件夹 | 必须所有文件放在同一个 `alien_invasion` 文件夹中，`import` 才能正确工作 |

### 1.3 开发节奏（三个阶段）

| 阶段 | 章节 | 成果 |
| --- | --- | --- |
| ① 武装飞船 | 第 12 章 | 窗口、设置、飞船类、移动控制、子弹与射击 |
| ② 外星人 | 第 13 章 | 外星人、外星舰队、舰队移动、碰撞检测、结束游戏 |
| ③ 记分 | 第 14 章 | Play 按钮、难度递增、记分牌（得分/最高分/等级/剩余飞船） |

---

## 二、项目结构与架构

### 2.1 文件清单（最终状态）

```
alien_invasion/
│
├── alien_invasion.py      # 主文件：AlienInvasion 类，游戏主循环与总调度
├── settings.py            # Settings 类：所有游戏设置（静态 + 动态）
├── ship.py                # Ship 类：飞船（移动、绘制、居中）
├── bullet.py              # Bullet 类：子弹（上升、绘制）
├── alien.py               # Alien 类：单个外星人（移动方向、边缘检测）
├── game_stats.py          # GameStats 类：游戏统计（剩余飞船、得分、等级、最高分）
├── button.py              # Button 类：Play 按钮
├── scoreboard.py          # Scoreboard 类：记分牌显示
│
└── images/
    ├── ship.bmp           # 飞船图像
    └── alien.bmp          # 外星人图像
```

### 2.2 类的职责划分

| 类 | 文件 | 职责 |
| --- | --- | --- |
| `AlienInvasion` | `alien_invasion.py` | 管理游戏资源和行为；持有 settings / screen / stats / sb / ship / bullets / aliens / play_button；主循环调度所有更新方法 |
| `Settings` | `settings.py` | 集中存储全部设置，区分静态设置与动态设置（后者每局重置） |
| `Ship` | `ship.py` | 加载飞船图像、根据移动标志更新位置、绘制、撞击后居中 |
| `Bullet` | `bullet.py` | 继承 `Sprite`；从飞船顶部生成、向上移动、绘制 |
| `Alien` | `alien.py` | 继承 `Sprite`；加载图像、按舰队方向移动、检测是否到达屏幕边缘 |
| `GameStats` | `game_stats.py` | 跟踪 `ships_left`、`score`、`level`、`high_score` |
| `Button` | `button.py` | 创建带标签的实心矩形按钮（Play），渲染文本、绘制 |
| `Scoreboard` | `scoreboard.py` | 将得分/最高分/等级渲染为图像并显示；绘制剩余飞船小图标 |

### 2.3 游戏主循环（最终版）

```python
def run_game(self):
    """开始游戏的主循环"""
    while True:
        self._check_events()
        if self.game_active:
            self.ship.update()
            self._update_bullets()
            self._update_aliens()
        self._update_screen()
        self.clock.tick(60)
```

**每次循环执行顺序（要点）：**

1. `_check_events()` —— **无论游戏是否活跃都要调用**（需响应 Q 键退出、关闭窗口、Play 按钮点击）；
2. 仅在 `game_active` 为 True 时：更新飞船 → 更新子弹（含碰撞检测）→ 更新外星人（含碰撞检测）；
3. `_update_screen()` —— 重绘背景、子弹、飞船、外星人、记分牌、（非活跃时）Play 按钮，然后 `pygame.display.flip()`；
4. `self.clock.tick(60)` —— 控制帧率为 60 帧/秒。

### 2.4 方法命名约定

- **辅助方法（helper method）**：只在类内部调用，名称以**单下划线**开头，如 `_check_events()`、`_fire_bullet()`；
- 可在类外调用的方法不加下划线，如 `update()`、`blitme()`、`center_ship()`、`draw_button()`、`show_score()`。

---

## 三、第 12 章　武装飞船

### 12.1 规划项目

先写清玩法说明再写代码，可确保开发不偏离轨道。第一阶段只做：**飞船能左右移动 + 能开火**。

### 12.2 安装 Pygame

```bash
$ python -m pip install --user pygame
# 若系统使用 python3：
$ python3 -m pip install --user pygame
```

### 12.3 开始游戏项目（搭建窗口骨架）

**12.3.1 创建 Pygame 窗口及响应用户输入**

```python
import sys
import pygame

class AlienInvasion:
    """管理游戏资源和行为的类"""

    def __init__(self):
        """初始化游戏并创建游戏资源"""
        pygame.init()                                            # 初始化背景
        self.screen = pygame.display.set_mode((1200, 800))       # 创建显示窗口
        pygame.display.set_caption("Alien Invasion")

    def run_game(self):
        """开始游戏的主循环"""
        while True:
            # 侦听键盘和鼠标事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
            # 让最近绘制的屏幕可见
            pygame.display.flip()

if __name__ == '__main__':
    # 创建游戏实例并运行游戏
    ai = AlienInvasion()
    ai.run_game()
```

关键概念：

- `pygame.init()`：初始化背景，让 Pygame 正确工作；
- `pygame.display.set_mode((宽, 高))`：创建显示窗口，返回的 surface 表示整个游戏窗口（赋给 `self.screen`）；
- **surface**：Pygame 中的"屏幕的一部分"，用于显示游戏元素；每个元素（飞船、外星人）都是一个 surface；
- **事件（event）**：用户玩游戏时执行的操作（按键、移动鼠标）；`pygame.event.get()` 返回上次调用后发生的所有事件列表；
- `pygame.display.flip()`：让最近绘制的屏幕可见，制造平滑移动效果。

**12.3.2 控制帧率**

```python
self.clock = pygame.time.Clock()   # 在 __init__() 中
...
self.clock.tick(60)                # 在 while 循环末尾，确保每秒运行 60 次
```

**12.3.3 设置背景色**

- Pygame 颜色用 RGB 值表示，每个分量取值 0～255（共 1600 万种以上颜色）；
- `(230, 230, 230)` 是浅灰色，赋给 `self.bg_color`；
- `self.screen.fill(self.bg_color)` 用背景色填充屏幕（`fill()` 只接受一个颜色实参）。

**12.3.4 创建 Settings 类**（把所有设置集中到一个地方，便于修改）

```python
class Settings:
    """存储游戏《外星人入侵》中所有设置的类"""

    def __init__(self):
        """初始化游戏的设置"""
        # 屏幕设置
        self.screen_width = 1200
        self.screen_height = 800
        self.bg_color = (230, 230, 230)
```

主文件中改为：`self.settings = Settings()`，屏幕尺寸与背景色均从 settings 读取。

### 12.4 添加飞船图像

**选图像注意事项：**

- 注意版权，优先使用 OpenGameArt 等网站的免费素材；
- 使用位图（.bmp）最简单（Pygame 默认加载位图）；jpg/png 可用 PS/GIMP/Paint 转换；
- **图像背景色最好与游戏背景色一致**，游戏看起来最漂亮；
- 在项目文件夹中新建 `images` 文件夹，保存 `ship.bmp`。

**12.4.1 创建 Ship 类**

```python
import pygame

class Ship:
    """管理飞船的类"""

    def __init__(self, ai_game):
        """初始化飞船并设置其初始位置"""
        self.screen = ai_game.screen
        self.screen_rect = ai_game.screen.get_rect()

        # 加载飞船图像并获取其外接矩形
        self.image = pygame.image.load('images/ship.bmp')
        self.rect = self.image.get_rect()

        # 每艘新飞船都放在屏幕底部的中央
        self.rect.midbottom = self.screen_rect.midbottom

    def blitme(self):
        """在指定位置绘制飞船"""
        self.screen.blit(self.image, self.rect)
```

**rect 对象的常用属性（重要！）：**

| 类别 | 属性 |
| --- | --- |
| 定位 | `x`、`y`（左上角坐标）、`center`、`centerx`、`centery` |
| 对齐屏幕边缘 | `top`、`bottom`、`left`、`right` |
| 组合属性 | `midbottom`、`midtop`、`midleft`、`midright` |

> 📌 坐标系：原点 (0, 0) 在屏幕**左上角**，向右下移动坐标值增大；1200×800 屏幕右下角为 (1200, 800)。

**12.4.2 在屏幕上绘制飞船**

在主文件的 `__init__()` 中：`self.ship = Ship(self)`（传入 AlienInvasion 实例，使 Ship 能访问游戏资源）；
在重绘屏幕时：`self.ship.blitme()`（在背景**之后**绘制，确保飞船在前面）。

### 12.5 重构：拆分 run_game()

> 重构（refactoring）：简化既有代码结构，使其更容易扩展。本项目遵循"先写出可行的代码，复杂后再重构"的现实开发流程。

**12.5.1 `_check_events()` 方法** —— 把事件管理代码从主循环中抽出，隔离事件循环；

**12.5.2 `_update_screen()` 方法** —— 把重绘背景、绘制飞船、切换屏幕的代码抽出：

```python
def run_game(self):
    """开始游戏的主循环"""
    while True:
        self._check_events()
        self._update_screen()
        self.clock.tick(60)
```

**动手试一试**

- 练习 12.1：蓝色的天空 —— 创建背景为蓝色的 Pygame 窗口。
- 练习 12.2：游戏角色 —— 找一幅游戏角色位图，创建类将其绘制到屏幕中央，并让图像/屏幕背景色一致。

### 12.6 驾驶飞船

**12.6.1 响应按键**

```python
elif event.type == pygame.KEYDOWN:
    if event.key == pygame.K_RIGHT:
        # 向右移动飞船
        self.ship.rect.x += 1
```

**12.6.2 允许持续移动（KEYDOWN + KEYUP + 移动标志）**

思路：标志 `moving_right` 为 `False` 时飞船不动；按下右键置 `True`，松开置 `False`。

Ship 类中：

```python
# 移动标志（飞船一开始不移动）
self.moving_right = False

def update(self):
    """根据移动标志调整飞船的位置"""
    if self.moving_right:
        self.rect.x += 1
```

`_check_events()` 中响应 `KEYDOWN`（置 True）与 `KEYUP`（置 False）；主循环中在**检测事件之后、更新屏幕之前**调用 `self.ship.update()`。

**12.6.3 左右移动**

- Ship 增加 `self.moving_left = False`；
- `update()` 中用**两个独立的 `if`**（而不是 `elif`）——这样同时按住左右键时先加后减，飞船保持不动，移动更准确；
- `_check_events()` 中响应 `K_LEFT` 的按下与松开（这里用 `elif` 没问题，因为每个事件只关联一个键）。

**12.6.4 调整飞船的速度**

```python
# settings.py
self.ship_speed = 1.5   # 用浮点数，便于更细致地控制速度
```

rect 只存储整数，所以 Ship 中额外用**浮点数属性 `self.x`** 记录准确位置：

```python
self.settings = ai_game.settings
self.x = float(self.rect.x)          # __init__ 中

def update(self):
    if self.moving_right:
        self.x += self.settings.ship_speed
    if self.moving_left:
        self.x -= self.settings.ship_speed
    self.rect.x = self.x              # 用 self.x 更新 rect
```

**12.6.5 限制飞船的活动范围**（到达边缘后像撞墙一样停止）

```python
if self.moving_right and self.rect.right < self.screen_rect.right:
    self.x += self.settings.ship_speed
if self.moving_left and self.rect.left > 0:
    self.x -= self.settings.ship_speed
```

**12.6.6 重构 `_check_events()`**：拆出 `_check_keydown_events(event)` 与 `_check_keyup_events(event)`；

**12.6.7 按 Q 键退出**：

```python
elif event.key == pygame.K_q:
    sys.exit()
```

**12.6.8 在全屏模式下运行游戏**

```python
self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
self.settings.screen_width = self.screen.get_rect().width
self.settings.screen_height = self.screen.get_rect().height
```

> ⚠️ 全屏前请确认 Q 键退出可用——Pygame 不提供全屏模式下的默认退出方式。

### 12.7 简单回顾（此时的项目组织）

| 文件 | 内容 |
| --- | --- |
| `alien_invasion.py` | `AlienInvasion` 类：settings、screen、ship；主循环调用 `_check_events()`、`ship.update()`、`_update_screen()`；还有 `_check_keydown_events()`、`_check_keyup_events()` |
| `settings.py` | `Settings` 类：只含 `__init__()`，初始化控制外观与飞船速度的属性 |
| `ship.py` | `Ship` 类：`__init__()`、`update()`、`blitme()`；图像 `ship.bmp` 放在 `images/` 中 |

> 运行游戏只需运行 `alien_invasion.py`；其他文件被导入。

**动手试一试**

- 练习 12.3：Pygame 文档 —— 浏览官方文档；
- 练习 12.4：火箭 —— 屏幕中央显示火箭，用上下左右键移动，且不能移出屏幕；
- 练习 12.5：按键 —— 每检测到 `KEYDOWN` 就 `print(event.key)`，了解按键响应。

### 12.8 射击

**12.8.1 添加子弹设置**

```python
# 子弹设置
self.bullet_speed = 2.0
self.bullet_width = 3
self.bullet_height = 15
self.bullet_color = (60, 60, 60)
```

**12.8.2 创建 Bullet 类**（继承 `Sprite`，用 `pygame.Rect()` 从头创建矩形，不是基于图像）

```python
import pygame
from pygame.sprite import Sprite

class Bullet(Sprite):
    """管理飞船所发射子弹的类"""

    def __init__(self, ai_game):
        """在飞船的当前位置创建一个子弹对象"""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.color = self.settings.bullet_color

        # 在 (0, 0) 处创建一个表示子弹的矩形，再设置正确的位置
        self.rect = pygame.Rect(0, 0, self.settings.bullet_width,
                                self.settings.bullet_height)
        self.rect.midtop = ai_game.ship.rect.midtop

        # 存储用浮点数表示的子弹位置
        self.y = float(self.rect.y)

    def update(self):
        """向上移动子弹"""
        self.y -= self.settings.bullet_speed   # 向上移动，y 坐标减小
        self.rect.y = self.y

    def draw_bullet(self):
        """在屏幕上绘制子弹"""
        pygame.draw.rect(self.screen, self.color, self.rect)
```

子弹发射后 x 坐标不变，因此沿**直线垂直上升**。

**12.8.3 将子弹存储到编组中**

```python
self.bullets = pygame.sprite.Group()   # __init__() 中
...
self.bullets.update()                  # 主循环中：自动为编组中每颗子弹调用 update()
```

> `Group` 类类似列表，但提供游戏开发所需的额外功能。

**12.8.4 开火**

```python
elif event.key == pygame.K_SPACE:      # _check_keydown_events()
    self._fire_bullet()

def _fire_bullet(self):
    """创建一颗子弹，并将其加入编组 bullets"""
    new_bullet = Bullet(self)
    self.bullets.add(new_bullet)
```

`_update_screen()` 中在绘制飞船**之前**遍历并绘制子弹（防子弹出现在飞船上）：

```python
for bullet in self.bullets.sprites():
    bullet.draw_bullet()
```

**12.8.5 删除已消失的子弹**（避免无谓地消耗内存和处理能力）

```python
for bullet in self.bullets.copy():     # 必须遍历副本！
    if bullet.rect.bottom <= 0:
        self.bullets.remove(bullet)
```

> ⚠️ 在 for 循环中遍历列表/编组时，**不能删除**其中的元素，必须遍历 `copy()` 得到的副本。
> 调试时可用 `print(len(self.bullets))` 核实删除效果；**确认后务必删除 print**，否则游戏会大大变慢。

**12.8.6 限制子弹数量**

```python
self.bullets_allowed = 3               # settings.py

def _fire_bullet(self):
    if len(self.bullets) < self.settings.bullets_allowed:
        new_bullet = Bullet(self)
        self.bullets.add(new_bullet)
```

**12.8.7 创建 `_update_bullets()` 方法**，保持主循环简洁：

```python
def _update_bullets(self):
    """更新子弹的位置并删除已消失的子弹"""
    self.bullets.update()
    for bullet in self.bullets.copy():
        if bullet.rect.bottom <= 0:
            self.bullets.remove(bullet)
```

**动手试一试**

- 练习 12.6：《横向射击》—— 飞船在屏幕左侧，可上下移动，按空格发射向右飞行的子弹，子弹消失后删除。

### 12.9 本章小结

游戏开发计划与 Pygame 游戏的基本结构 → 背景色与设置类 → 绘制图像 → 控制元素移动 → 自动移动元素（子弹）与删除不再需要的对象 → **经常性重构**为后续开发提供便利。

---

## 四、第 13 章　外星人

### 13.1 项目回顾（本章开发计划）

1. 在屏幕左上角添加一个外星人，并指定合适的边距；
2. 沿屏幕上边缘添加一行外星人，再不断添加成行外星人，直到填满屏幕上半部分；
3. 让外星人向两侧和向下移动，直到舰队被全部击落、有外星人撞到飞船或抵达屏幕下边缘；
4. 舰队被击落 → 创建新舰队；撞到飞船/到达下边缘 → 销毁飞船并创建新舰队；
5. 限制玩家可用飞船数量，用完后游戏结束。

### 13.2 创建第一个外星人

**Alien 类**（`alien.py`，同样继承 `Sprite`）：

```python
import pygame
from pygame.sprite import Sprite

class Alien(Sprite):
    """表示单个外星人的类"""

    def __init__(self, ai_game):
        """初始化外星人并设置其起始位置"""
        super().__init__()
        self.screen = ai_game.screen

        # 加载外星人图像并设置其 rect 属性
        self.image = pygame.image.load('images/alien.bmp')
        self.rect = self.image.get_rect()

        # 每个外星人最初都在屏幕的左上角附近
        self.rect.x = self.rect.width
        self.rect.y = self.rect.height

        # 存储外星人的精确水平位置
        self.x = float(self.rect.x)
```

要点：

- 左边距设为外星人宽度、上边距设为高度，视觉上更美观；
- 只精确记录**水平位置** `self.x`（移动主要在乎水平速度）；
- Alien **不需要**自己的绘制方法——使用编组的 `draw()` 自动绘制全部元素。

**创建 Alien 实例**：在 `__init__()` 中新增 `self.aliens = pygame.sprite.Group()` 并调用 `_create_fleet()`；在 `_update_screen()` 中添加 `self.aliens.draw(self.screen)`。

```python
def _create_fleet(self):
    """创建一个外星舰队"""
    # 创建一个外星人
    alien = Alien(self)
    self.aliens.add(alien)
```

### 13.3 创建外星舰队

**13.3.1 创建一行外星人**（间距为外星人宽度）

```python
alien = Alien(self)
alien_width = alien.rect.width
current_x = alien_width
while current_x < (self.settings.screen_width - 2 * alien_width):
    new_alien = Alien(self)
    new_alien.x = current_x
    new_alien.rect.x = current_x
    self.aliens.add(new_alien)
    current_x += 2 * alien_width
```

- `current_x` 表示下一个外星人的水平位置，初值为一个外星人宽度（避免紧贴左边缘）；
- 循环条件在右边缘预留空间：只要余下空间超过外星人宽度的两倍，就继续添加。

**13.3.2 重构 `_create_fleet()`** —— 抽出 `_create_alien(x_position)` 辅助方法，便于添加多行。

**13.3.3 添加多行外星人**（嵌套 while 循环：内层管 x，外层管 y）

```python
def _create_fleet(self):
    """创建一个外星舰队"""
    alien = Alien(self)
    alien_width, alien_height = alien.rect.size
    current_x, current_y = alien_width, alien_height
    while current_y < (self.settings.screen_height - 3 * alien_height):
        while current_x < (self.settings.screen_width - 2 * alien_width):
            self._create_alien(current_x, current_y)
            current_x += 2 * alien_width
        # 添加一行外星人后，重置 x 值并递增 y 值
        current_x = alien_width
        current_y += 2 * alien_height

def _create_alien(self, x_position, y_position):
    """创建一个外星人，并将其加入外星舰队"""
    new_alien = Alien(self)
    new_alien.x = x_position
    new_alien.rect.x = x_position
    new_alien.rect.y = y_position
    self.aliens.add(new_alien)
```

> ⚠️ 最后两行属于**外层循环**（每创建一行执行一次）；缩进非常重要，舰队出问题先检查嵌套循环缩进。

**动手试一试**

- 练习 13.1：星星 —— 找星星图像，在屏幕上排列显示一系列整齐的星星；
- 练习 13.2：更逼真的星星 —— 用 `randint()` 随机调整每颗星星的位置。

### 13.4 让外星舰队移动

移动规则：**向右 → 触边后下移一段 → 向左 → 再触边后下移**，如此往复。

**13.4.1 向右移动外星舰队**

```python
# settings.py
self.alien_speed = 1.0

# alien.py
def __init__(self, ai_game):
    ...
    self.settings = ai_game.settings

def update(self):
    """向右移动外星人"""
    self.x += self.settings.alien_speed
    self.rect.x = self.x
```

主循环中新增 `self._update_aliens()`（放在 `_update_bullets()` 之后，稍后要检查子弹击中外星人）：

```python
def _update_aliens(self):
    """更新外星舰队中所有外星人的位置"""
    self.aliens.update()
```

**13.4.2 创建表示舰队移动方向的设置**

```python
self.fleet_drop_speed = 10
# fleet_direction 为 1 表示向右移动，为 -1 表示向左移动
self.fleet_direction = 1
```

> 用 `1 / -1` 而非 `'right' / 'left'`：既可直接参与 x 坐标的加减运算，又避免 if-elif 判断。

**13.4.3 检查外星人是否到达了屏幕边缘**（Alien 类）

```python
def check_edges(self):
    """如果外星人位于屏幕边缘，就返回 True"""
    screen_rect = self.screen.get_rect()
    return (self.rect.right >= screen_rect.right) or (self.rect.left <= 0)

def update(self):
    """向左或向右移动外星人"""
    self.x += self.settings.alien_speed * self.settings.fleet_direction
    self.rect.x = self.x
```

**13.4.4 向下移动外星舰队并改变移动方向**

```python
def _check_fleet_edges(self):
    """在有外星人到达边缘时采取相应的措施"""
    for alien in self.aliens.sprites():
        if alien.check_edges():
            self._change_fleet_direction()
            break

def _change_fleet_direction(self):
    """将整个外星舰队向下移动，并改变它们的方向"""
    for alien in self.aliens.sprites():
        alien.rect.y += self.settings.fleet_drop_speed
    self.settings.fleet_direction *= -1
```

> 改变方向的语句**不在 for 循环中**——每个外星人都要下移，但方向只需翻转一次。

**动手试一试**

- 练习 13.3：雨滴 —— 创建整齐排列的雨滴并向下降落，到达下边缘后消失；
- 练习 13.4：连绵细雨 —— 一行雨滴消失后，在上边缘再出现一行新雨滴。

### 13.5 击落外星人

**碰撞**：游戏元素有重叠。用 `sprite.groupcollide()` 检测两个编组之间的碰撞。

**13.5.1 检测子弹和外星人的碰撞**

```python
collisions = pygame.sprite.groupcollide(
        self.bullets, self.aliens, True, True)
```

- 比较两个编组中每个元素的 rect；返回**字典**：键为发生碰撞的子弹，值为被该子弹击中的外星人（列表）；
- 两个 `True` 实参：碰撞时**同时删除**子弹和外星人；
- 若把第一个布尔实参设为 `False`，可模拟"高能子弹"：击中外星人后子弹仍继续飞行。

**13.5.2 为测试创建大子弹**

- 测试"外星人编组为空"等情形可用时很长，可临时改设置专注测试：缩小屏幕、加快子弹速度，或把 `bullet_width` 设为 300（甚至 3000）并让它击中外星人后依然有效；
- **测试完成后务必把设置恢复正常**。

**13.5.3 生成新的外星舰队**

```python
if not self.aliens:              # 空编组相当于 False
    # 删除现有的子弹并创建一个新的外星舰队
    self.bullets.empty()
    self._create_fleet()
```

**13.5.4 加快子弹的速度**：调整 `settings.bullet_speed`（书中作者调至 2.5），最佳值取决于实际手感。

**13.5.5 重构 `_update_bullets()`**：把碰撞处理移到 `_check_bullet_alien_collisions()`：

```python
def _check_bullet_alien_collisions(self):
    """响应子弹和外星人的碰撞"""
    # 删除发生碰撞的子弹和外星人
    collisions = pygame.sprite.groupcollide(
            self.bullets, self.aliens, True, True)

    if not self.aliens:
        # 删除现有的所有子弹，并创建一个新的外星舰队
        self.bullets.empty()
        self._create_fleet()
```

**动手试一试**

- 练习 13.5：改进版《横向射击》—— 添加外星舰队（或让外星人随机出现）并让其移动，子弹击中后消失。

### 13.6 结束游戏

**13.6.1 检测外星人和飞船的碰撞**

```python
if pygame.sprite.spritecollideany(self.ship, self.aliens):
    print("Ship hit!!!")
```

- `spritecollideany(精灵, 编组)`：检查编组中是否有成员与精灵碰撞，**找到第一个后即停止遍历**；
- 无碰撞返回 `None`（if 块不执行）；
- 测试时可将 `fleet_drop_speed` 设为 50 或 100，让外星人更快撞到飞船。

**13.6.2 响应碰撞**——用统计信息跟踪飞船被撞次数（而不是销毁再重建 Ship 实例）

`game_stats.py`：

```python
class GameStats:
    """跟踪游戏的统计信息"""

    def __init__(self, ai_game):
        """初始化统计信息"""
        self.settings = ai_game.settings
        self.reset_stats()

    def reset_stats(self):
        """初始化在游戏运行期间可能变化的统计信息"""
        self.ships_left = self.settings.ship_limit
```

```python
# settings.py
self.ship_limit = 3
```

> 设计要点：**只创建一个 GameStats 实例**，但每次开始新游戏都要重置统计信息——所以统计信息在 `reset_stats()` 中初始化，并由 `__init__()` 调用一次；开始新游戏时再调用一次。

`_ship_hit()` 响应碰撞（从标准库 `time` 导入 `sleep`）：

```python
def _ship_hit(self):
    """响应飞船和外星人的碰撞"""
    # 将 ships_left 减 1
    self.stats.ships_left -= 1
    # 清空外星人列表和子弹列表
    self.bullets.empty()
    self.aliens.empty()
    # 创建一个新的外星舰队，并将飞船放在屏幕底部的中央
    self._create_fleet()
    self.ship.center_ship()
    # 暂停
    sleep(0.5)
```

Ship 类中新增：

```python
def center_ship(self):
    """将飞船放在屏幕底部的中央"""
    self.rect.midbottom = self.screen_rect.midbottom
    self.x = float(self.rect.x)
```

> 📌 整个游戏运行期间**只创建一个飞船实例**，被撞到时只是把它重新居中；`ships_left` 指出玩家是否用完了所有飞船。

**13.6.3 有外星人到达屏幕下边缘**（同样视为损失一艘飞船）

```python
def _check_aliens_bottom(self):
    """检查是否有外星人到达了屏幕的下边缘"""
    for alien in self.aliens.sprites():
        if alien.rect.bottom >= self.settings.screen_height:
            # 像飞船被撞到一样进行处理
            self._ship_hit()
            break
```

并在 `_update_aliens()` 末尾调用它：

```python
def _update_aliens(self):
    """检查是否有外星人位于屏幕边缘，并更新整个外星舰队的位置"""
    self._check_fleet_edges()
    self.aliens.update()

    # 检测外星人和飞船之间的碰撞
    if pygame.sprite.spritecollideany(self.ship, self.aliens):
        self._ship_hit()

    # 检查是否有外星人到达了屏幕的下边缘
    self._check_aliens_bottom()
```

**13.6.4 游戏结束**——用标志 `game_active`：

```python
# __init__() 中
self.game_active = True

def _ship_hit(self):
    """响应飞船和外星人的碰撞"""
    if self.stats.ships_left > 0:
        self.stats.ships_left -= 1
        ...
        sleep(0.5)
    else:
        self.game_active = False
```

**13.7 确定应运行游戏的哪些部分**

```python
while True:
    self._check_events()            # 任何情况都要运行（Q 退出、关闭窗口等）
    if self.game_active:
        self.ship.update()
        self._update_bullets()
        self._update_aliens()
    self._update_screen()           # 非活跃时也要更新屏幕（等待玩家的界面）
    self.clock.tick(60)
```

**动手试一试**

- 练习 13.6：游戏结束 —— 在《横向射击》中记录被撞次数与击落数，设定结束条件。

### 13.8 本章小结

在游戏中添加大量相同元素（编组 + 嵌套循环）→ 控制对象移动方向与边缘响应 → 检测并响应碰撞 → 跟踪统计信息、用 `game_active` 判断游戏是否结束。

---

## 五、第 14 章　记分

本章完成游戏的**最后一块拼图**：Play 按钮、随等级加快节奏、记分系统。

### 14.1 添加 Play 按钮

让游戏一开始处于**非活动状态**，玩家单击 Play 按钮才开始：

```python
# 让游戏在一开始处于非活动状态
self.game_active = False
```

**14.1.1 创建 Button 类**（`button.py`）——Pygame 没有内置按钮，自己写一个"带标签的实心矩形"

```python
import pygame.font

class Button:
    """为游戏创建按钮的类"""

    def __init__(self, ai_game, msg):
        """初始化按钮的属性"""
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()

        # 设置按钮的尺寸和其他属性
        self.width, self.height = 200, 50
        self.button_color = (0, 135, 0)
        self.text_color = (255, 255, 255)
        self.font = pygame.font.SysFont(None, 48)

        # 创建按钮的 rect 对象，并使其居中
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = self.screen_rect.center

        # 按钮的标签只需创建一次
        self._prep_msg(msg)

    def _prep_msg(self, msg):
        """将 msg 渲染为图像，并使其在按钮上居中"""
        self.msg_image = self.font.render(msg, True, self.text_color,
                                          self.button_color)
        self.msg_image_rect = self.msg_image.get_rect()
        self.msg_image_rect.center = self.rect.center

    def draw_button(self):
        """绘制一个用颜色填充的按钮，再绘制文本"""
        self.screen.fill(self.button_color, self.rect)
        self.screen.blit(self.msg_image, self.msg_image_rect)
```

要点：

- 导入 `pygame.font`，让 Pygame 能把文本渲染到屏幕；
- `pygame.font.SysFont(None, 48)`：`None` 表示使用默认字体，`48` 为字号；
- **Pygame 处理文本 = 把字符串渲染成图像**，再用 `blit()` 绘制；
- `font.render(msg, 反锯齿?, 文本色, 背景色)`——开启反锯齿让边缘更平滑；不指定背景色时文本背景透明。

**14.1.2 在屏幕上绘制按钮**

```python
# __init__() 末尾
self.play_button = Button(self, "Play")

# _update_screen() 中（绘制在其他所有元素之后，保证在最上层）
if not self.game_active:
    self.play_button.draw_button()
```

**14.1.3 开始游戏（检测鼠标点击）**

```python
elif event.type == pygame.MOUSEBUTTONDOWN:
    mouse_pos = pygame.mouse.get_pos()
    self._check_play_button(mouse_pos)

def _check_play_button(self, mouse_pos):
    """在玩家单击 Play 按钮时开始新游戏"""
    if self.play_button.rect.collidepoint(mouse_pos):
        self.game_active = True
```

**14.1.4 重置游戏**（处理游戏结束后的重玩）

```python
def _check_play_button(self, mouse_pos):
    """在玩家单击 Play 按钮时开始新游戏"""
    if self.play_button.rect.collidepoint(mouse_pos):
        # 重置游戏的统计信息
        self.stats.reset_stats()
        self.game_active = True
        # 清空外星人列表和子弹列表
        self.bullets.empty()
        self.aliens.empty()
        # 创建一个新的外星舰队，并将飞船放在屏幕底部的中央
        self._create_fleet()
        self.ship.center_ship()
```

**14.1.5 将 Play 按钮切换到非活动状态**——避免按钮不可见时误触即重新开始：

```python
button_clicked = self.play_button.rect.collidepoint(mouse_pos)
if button_clicked and not self.game_active:
    ...
```

**14.1.6 隐藏光标**——游戏进行时隐藏鼠标光标，结束后恢复：

```python
# 开始游戏时（_check_play_button 的 if 块内）
pygame.mouse.set_visible(False)

# 游戏结束时（_ship_hit 的 else 块内）
self.game_active = False
pygame.mouse.set_visible(True)
```

> 关注这类细节能让游戏显得更专业。

**动手试一试**

- 练习 14.1：按 P 键开始新游戏 —— 把 `_check_play_button()` 的部分代码提取到 `_start_game()`，在 `_check_play_button()` 和 `_check_keydown_events()` 中调用；
- 练习 14.2：射击练习 —— 屏幕右边缘上下移动的矩形标靶 + 左侧可上下移动的飞船，Play 按钮开始，三次未击中结束。

### 14.2 提高难度

**14.2.1 修改速度设置**——把设置分为**静态**（`__init__()` 中）与**动态**（`initialize_dynamic_settings()` 中）：

```python
def __init__(self):
    """初始化游戏的静态设置"""
    # 屏幕设置
    self.screen_width = 1200
    self.screen_height = 800
    self.bg_color = (230, 230, 230)

    # 飞船设置
    self.ship_limit = 3

    # 子弹设置
    self.bullet_width = 3
    self.bullet_height = 15
    self.bullet_color = (60, 60, 60)
    self.bullets_allowed = 3

    # 外星人设置
    self.fleet_drop_speed = 10

    # 以什么速度加快游戏的节奏
    self.speedup_scale = 1.1

    self.initialize_dynamic_settings()

def initialize_dynamic_settings(self):
    """初始化随游戏进行而变化的设置"""
    self.ship_speed = 1.5
    self.bullet_speed = 2.5
    self.alien_speed = 1.0

    # fleet_direction 为 1 表示向右，为 -1 表示向左
    self.fleet_direction = 1

def increase_speed(self):
    """提高速度设置的值"""
    self.ship_speed *= self.speedup_scale
    self.bullet_speed *= self.speedup_scale
    self.alien_speed *= self.speedup_scale
```

- `speedup_scale`：2 表示每提高一个等级节奏翻倍；1 表示节奏不变；**1.1 既能持续加快又不会过快**；
- 不必增大 `fleet_drop_speed`：外星人移动越快，到达屏幕下边缘所需时间自然越短。

舰队被全部击落后调用：

```python
if not self.aliens:
    # 删除现有的子弹并创建一个新的外星舰队
    self.bullets.empty()
    self._create_fleet()
    self.settings.increase_speed()
```

**14.2.2 重置速度**——开始新游戏时恢复动态设置为初始值（否则沿用上一轮已加快的速度）：

```python
def _check_play_button(self, mouse_pos):
    button_clicked = self.play_button.rect.collidepoint(mouse_pos)
    if button_clicked and not self.game_active:
        # 还原游戏设置
        self.settings.initialize_dynamic_settings()
        ...
```

> 调参建议：太难→减小 `speedup_scale`；太易→增大。理想节奏是：前几群外星舰队容易击落，随后有难度但可行，之后几乎不可能全清。

**动手试一试**

- 练习 14.3：有一定难度的射击练习 —— 标靶速度随游戏加快，单击 Play 时重置；
- 练习 14.4：难度等级 —— 创建一组按钮让玩家选择起始难度等级。

### 14.3 记分

**在 GameStats 中添加统计项：**

```python
def reset_stats(self):
    """初始化随游戏进行可能变化的统计信息"""
    self.ships_left = self.settings.ship_limit
    self.score = 0
    self.level = 1

# __init__() 中（最高分在任何情况下都不应重置）
self.high_score = 0
```

**14.3.1 显示得分**——新建 `Scoreboard` 类（`scoreboard.py`）：

```python
import pygame.font

class Scoreboard:
    """显示得分信息的类"""

    def __init__(self, ai_game):
        """初始化显示得分涉及的属性"""
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()
        self.settings = ai_game.settings
        self.stats = ai_game.stats

        # 显示得分信息时使用的字体设置
        self.text_color = (30, 30, 30)
        self.font = pygame.font.SysFont(None, 48)

        # 准备初始得分图像
        self.prep_score()

    def prep_score(self):
        """将得分渲染为图像"""
        score_str = str(self.stats.score)
        self.score_image = self.font.render(score_str, True,
                self.text_color, self.settings.bg_color)

        # 在屏幕右上角显示得分
        self.score_rect = self.score_image.get_rect()
        self.score_rect.right = self.screen_rect.right - 20
        self.score_rect.top = 20

    def show_score(self):
        """在屏幕上显示得分"""
        self.screen.blit(self.score_image, self.score_rect)
```

> 定位技巧：让得分的**右边缘**与屏幕右边缘相距 20 像素，位数增加时向左扩展而始终锚定右上角。

**14.3.2 创建记分牌**：主文件中 `self.sb = Scoreboard(self)`（在 `GameStats` 之后创建），并在 `_update_screen()` 中调用 `self.sb.show_score()`。

**14.3.3 在外星人被击落时更新得分**

```python
# settings.py：指定每个外星人的分数（动态设置，随新游戏重置）
self.alien_points = 50

# alien_invasion.py
if collisions:
    self.stats.score += self.settings.alien_points
    self.sb.prep_score()
```

**14.3.4 重置得分**：开始新游戏时重置统计信息后调用 `prep_score()`，让记分牌显示 0。

**14.3.5 将每个被击落的外星人都计入得分**

> 问题：若一次循环中两颗子弹各击中一个外星人，或一颗超宽子弹同时击中多个外星人，旧写法只会算一次分。

```python
if collisions:
    for aliens in collisions.values():
        self.stats.score += self.settings.alien_points * len(aliens)
    self.sb.prep_score()
```

> `collisions` 的**每个值都是列表**，包含被同一颗子弹击中的所有外星人；按数量计分才不遗漏。

**14.3.6 提高分数**——等级越高，外星人分数越高：

```python
# settings.py
self.score_scale = 1.5      # 外星人分数的提高速度

def increase_speed(self):
    """提高速度设置的值和外星人分数"""
    self.ship_speed *= self.speedup_scale
    self.bullet_speed *= self.speedup_scale
    self.alien_speed *= self.speedup_scale
    self.alien_points = int(self.alien_points * self.score_scale)
```

> 节奏加快用 1.1 即可，但分数想有明显变化需要更大的倍率（1.5）。
> 调试可用 `print(self.alien_points)` 确认分数增长，确认后记得删除（影响性能）。

**14.3.7 对得分进行舍入**（街机风格：显示为 10 的整数倍，并用逗号作千位分隔符）

```python
def prep_score(self):
    """将得分渲染为图像"""
    rounded_score = round(self.stats.score, -1)
    score_str = f"{rounded_score:,}"
    self.score_image = self.font.render(score_str, True,
            self.text_color, self.settings.bg_color)
    ...
```

> `round(x, -1)`：第二个实参为负数时，舍入到最近的 10 的整数倍；f 字符串中的 `:,` 格式说明符插入千位分隔符（如 `1,000,000`）。

**14.3.8 最高分**

```python
def prep_high_score(self):
    """将最高分渲染为图像"""
    high_score = round(self.stats.high_score, -1)
    high_score_str = f"{high_score:,}"
    self.high_score_image = self.font.render(high_score_str, True,
            self.text_color, self.settings.bg_color)

    # 将最高分放在屏幕顶部的中央
    self.high_score_rect = self.high_score_image.get_rect()
    self.high_score_rect.centerx = self.screen_rect.centerx
    self.high_score_rect.top = self.score_rect.top

def check_high_score(self):
    """检查是否诞生了新的最高分"""
    if self.stats.score > self.stats.high_score:
        self.stats.high_score = self.stats.score
        self.prep_high_score()
```

在 `_check_bullet_alien_collisions()` 中，更新得分后检查最高分：

```python
if collisions:
    for aliens in collisions.values():
        self.stats.score += self.settings.alien_points * len(aliens)
    self.sb.prep_score()
    self.sb.check_high_score()
```

**14.3.9 显示等级**（当前得分正下方）

```python
# GameStats.reset_stats()
self.level = 1

# Scoreboard
def prep_level(self):
    """将等级渲染为图像"""
    level_str = str(self.stats.level)
    self.level_image = self.font.render(level_str, True,
            self.text_color, self.settings.bg_color)

    # 将等级放在得分下方
    self.level_rect = self.level_image.get_rect()
    self.level_rect.right = self.score_rect.right
    self.level_rect.top = self.score_rect.bottom + 10
```

提升等级的位置（舰队被全部击落后）：

```python
if not self.aliens:
    self.bullets.empty()
    self._create_fleet()
    self.settings.increase_speed()
    # 提高等级
    self.stats.level += 1
    self.sb.prep_level()
```

> 提示：经典游戏会给数值加标签（Score / High Score / Level）。本书未加，因为游戏开始后数字含义一目了然；如需标签，在调用 `font.render()` 前把标签拼进字符串即可。

**14.3.10 显示余下的飞船数**（用图形而非数字，屏幕左上角绘制飞船小图标）

第一步：让 `Ship` 继承 `Sprite`，以便创建飞船编组：

```python
import pygame
from pygame.sprite import Sprite

class Ship(Sprite):
    """管理飞船的类"""

    def __init__(self, ai_game):
        """初始化飞船并设置其起始位置"""
        super().__init__()
        ...
```

第二步：Scoreboard 中增加 `prep_ships()`：

```python
import pygame.font
from pygame.sprite import Group
from ship import Ship

def prep_ships(self):
    """显示还余下多少艘飞船"""
    self.ships = Group()
    for ship_number in range(self.stats.ships_left):
        ship = Ship(self.ai_game)
        ship.rect.x = 10 + ship_number * ship.rect.width
        ship.rect.y = 10
        self.ships.add(ship)

def show_score(self):
    """在屏幕上绘制得分、等级和余下的飞船数"""
    self.screen.blit(self.score_image, self.score_rect)
    self.screen.blit(self.high_score_image, self.high_score_rect)
    self.screen.blit(self.level_image, self.level_rect)
    self.ships.draw(self.screen)
```

> 需要把 `ai_game` 存为属性（`self.ai_game = ai_game`），因为创建飞船时要用它。

第三步：在两个时机调用 `prep_ships()`：
- 单击 Play 开始新游戏时（让玩家知道初始有多少艘飞船）；
- 飞船被撞到时（`_ship_hit()` 中把 `ships_left` 减 1 之后）。

**记分系统各部分位置一览：**

| 显示内容 | 位置 |
| --- | --- |
| 当前得分 | 屏幕右上角（右边缘距屏 20px、上边缘距屏 20px） |
| 最高分 | 屏幕顶部中央 |
| 等级 | 当前得分正下方 10px |
| 剩余飞船 | 屏幕左上角（第 1 艘距左边 10px，依次右排；距上边 10px） |

**动手试一试**

- 练习 14.5：历史最高分 —— 退出前把最高分写入文件，`GameStats` 初始化时从文件读取；
- 练习 14.6：重构 —— 把"开始新等级"的代码移入 `start_new_level()`；把 `Scoreboard.__init__()` 中四个 `prep_*` 调用移入 `prep_images()`；
- 练习 14.7：扩展游戏 —— 让外星人也能射击、给飞船加盾牌、用 `pygame.mixer` 添加音效等；
- 练习 14.8：终极版《横向射击》—— 综合前几章重写《横向射击》。

### 14.4 本章小结

Play 按钮与鼠标事件检测 → 活动状态下隐藏光标 → 随游戏进行调整节奏 → 实现记分系统 → 以文本和非文本方式显示信息。

---

## 六、核心概念速查表

### 6.1 Pygame 核心对象与方法

| 名称 | 作用 | 首次出现 |
| --- | --- | --- |
| `pygame.init()` | 初始化背景，让 Pygame 正确工作 | 12.3.1 |
| `pygame.display.set_mode((w, h))` | 创建显示窗口，返回主 surface | 12.3.1 |
| `pygame.display.set_caption()` | 设置窗口标题 | 12.3.1 |
| `pygame.display.flip()` | 让最近绘制的屏幕可见 | 12.3.1 |
| `pygame.time.Clock()` / `clock.tick(60)` | 创建时钟 / 控制帧率 | 12.3.2 |
| `screen.fill(color)` | 用颜色填充 surface | 12.3.3 |
| `pygame.image.load(path)` | 加载图像，返回 surface | 12.4.1 |
| `surface.get_rect()` | 获取 surface 的外接矩形 | 12.4.1 |
| `screen.blit(image, rect)` | 在指定位置绘制图像 | 12.4.1 |
| `pygame.event.get()` | 获取事件列表 | 12.3.1 |
| `pygame.QUIT / KEYDOWN / KEYUP / MOUSEBUTTONDOWN` | 事件类型 | 12.3.1 / 12.6.1 / 14.1.3 |
| `pygame.K_RIGHT / K_LEFT / K_q / K_SPACE` | 按键常量 | 12.6.1 起 |
| `pygame.Rect(x, y, w, h)` | 从头创建矩形（子弹用） | 12.8.2 |
| `pygame.draw.rect(screen, color, rect)` | 绘制实心矩形 | 12.8.2 |
| `pygame.sprite.Sprite` | 精灵基类（子弹、外星人、飞船继承） | 12.8.2 |
| `pygame.sprite.Group()` | 编组，批量管理同类精灵 | 12.8.3 |
| `group.add() / remove() / empty() / copy() / sprites()` | 编组的增删改查 | 12.8.3 起 |
| `group.update()` | 对编组中每个精灵调用 `update()` | 12.8.3 |
| `group.draw(screen)` | 把编组中每个精灵绘制到屏幕 | 13.2.2 |
| `pygame.sprite.groupcollide(g1, g2, dokill1, dokill2)` | 两个编组间的碰撞检测，返回字典 | 13.5.1 |
| `pygame.sprite.spritecollideany(sprite, group)` | 一个精灵与一个编组的碰撞检测 | 13.6.1 |
| `rect.collidepoint(pos)` | 判断点是否在矩形内（按钮点击） | 14.1.3 |
| `pygame.mouse.get_pos()` | 获取鼠标位置 | 14.1.3 |
| `pygame.mouse.set_visible(bool)` | 显示/隐藏光标 | 14.1.6 |
| `pygame.font.SysFont(None, size)` / `font.render()` | 创建字体 / 将文本渲染为图像 | 14.1.1 |
| `pygame.FULLSCREEN` | 全屏模式参数 | 12.6.8 |
| `time.sleep(s)` | 暂停（碰撞后停顿用） | 13.6.2 |

### 6.2 编程知识点

| 知识点 | 应用场景 |
| --- | --- |
| 面向对象、类间引用（`ai_game` 参数） | 每个游戏元素一个类，通过主实例访问共享资源 |
| 重构 / 辅助方法（单下划线命名） | `_check_events()`、`_update_screen()`、`_update_bullets()` 等 |
| 浮点数与整数（`self.x` + rect.x） | 平滑移动需要浮点精度，rect 只存整数 |
| 事件驱动 + 主循环 | KEYDOWN/KEYUP + 移动标志实现持续移动 |
| 遍历副本再删除 | 删子弹用 `self.bullets.copy()` |
| 空编组/空列表的布尔值 | `if not self.aliens:` 判断舰队被清空 |
| 标志位管理状态 | `moving_right`、`game_active`、`button_clicked` |
| 字典遍历与值统计 | `collisions.values()` 统计击落数量 |
| 字符串格式化 | `round(x, -1)` 舍入 + `f"{x:,}"` 千位分隔符 |

---

## 七、游戏参数总表

| 参数 | 值 | 类型 | 说明 |
| --- | --- | --- | --- |
| `screen_width` | 1200 | 静态 | 窗口宽（全屏模式下运行时覆盖） |
| `screen_height` | 800 | 静态 | 窗口高 |
| `bg_color` | (230, 230, 230) | 静态 | 浅灰背景色 |
| `ship_limit` | 3 | 静态 | 玩家拥有的飞船总数 |
| `bullet_width` | 3 | 静态 | 子弹宽（测试时可改为 300+） |
| `bullet_height` | 15 | 静态 | 子弹高 |
| `bullet_color` | (60, 60, 60) | 静态 | 深灰子弹 |
| `bullets_allowed` | 3 | 静态 | 屏幕上同时存在的子弹上限 |
| `fleet_drop_speed` | 10 | 静态 | 触边后舰队下移距离 |
| `speedup_scale` | 1.1 | 静态 | 每升一级速度倍率 |
| `score_scale` | 1.5 | 静态 | 每升一级分数倍率 |
| `ship_speed` | 1.5 | 动态 | 飞船速度（每级 ×1.1） |
| `bullet_speed` | 2.5 | 动态 | 子弹速度（每级 ×1.1） |
| `alien_speed` | 1.0 | 动态 | 外星人水平速度（每级 ×1.1） |
| `fleet_direction` | 1 | 动态 | 1 向右 / -1 向左 |
| `alien_points` | 50 | 动态 | 每个外星人分数（每级 ×1.5） |

其他常量：帧率 60；按钮 200×50、颜色 `(0,135,0)`、文字白色、字号 48；记分牌文字色 `(30,30,30)`、字号 48。

---

## 八、常见坑与调试提示

| 问题 | 原因 / 解法 |
| --- | --- |
| 外星舰队排列错乱 | 嵌套 while 循环的**缩进**问题——重置 x、递增 y 的两行必须属于外层循环 |
| 游戏越玩越卡 | 忘了删除消失的子弹；或忘了删除调试用 `print()`（写终端比绘图还慢） |
| 遍历时删除元素报错 | for 循环中不能删除被遍历的编组/列表元素，必须遍历 `copy()` |
| 飞船移出屏幕消失 | `update()` 中要加边界条件（`rect.right < screen_rect.right` 等） |
| 子弹出现在飞船上 | `_update_screen()` 中先画子弹、后画飞船 |
| 单击空白处也能重开游戏 | `_check_play_button()` 中要同时判断 `button_clicked and not self.game_active` |
| 重开一局后难度没复位 | 开始新游戏要调用 `settings.initialize_dynamic_settings()` |
| 新一局开始时显示上局分数 | 开始新游戏时调用 `sb.prep_score()` / `prep_level()` / `prep_ships()` |
| 最高分被重置 | `high_score` 在 `__init__()` 中初始化（不放进 `reset_stats()`） |
| 一次击中多个外星人只加一次分 | 遍历 `collisions.values()`，按 `len(aliens)` 计分 |
| 全屏后无法退出 | 先确认 Q 键退出可用，Pygame 无默认全屏退出方式 |
| `import` 报错 / 图片加载失败 | 所有文件必须放在同一项目文件夹；图像放 `images/`，路径写 `'images/ship.bmp'` |
| 两键同按飞船不动 | 属正常现象（左右 if 相互抵消） |

---

## 九、练习清单

### 第 12 章

| 练习 | 内容 |
| --- | --- |
| 12.1 | 蓝色的天空：背景为蓝色的 Pygame 窗口 |
| 12.2 | 游戏角色：角色位图绘制在屏幕中央，背景色一致 |
| 12.3 | Pygame 文档：浏览官方文档 |
| 12.4 | 火箭：四方向键移动火箭，不许移出屏幕 |
| 12.5 | 按键：`print(event.key)` 观察按键响应 |
| 12.6 | 《横向射击》：飞船在左侧可上下移动，空格向右发射子弹并删除消失的子弹 |

### 第 13 章

| 练习 | 内容 |
| --- | --- |
| 13.1 | 星星：排列整齐的星星 |
| 13.2 | 更逼真的星星：用 `randint()` 随机放置 |
| 13.3 | 雨滴：整齐列阵的雨滴下落，到底部消失 |
| 13.4 | 连绵细雨：一行消失后在顶部生成新的一行 |
| 13.5 | 改进版《横向射击》：添加外星舰队、移动、被击中消失 |
| 13.6 | 游戏结束：统计被撞次数与击落数，设定结束条件 |

### 第 14 章

| 练习 | 内容 |
| --- | --- |
| 14.1 | 按 P 键开始新游戏（提取 `_start_game()` 方法） |
| 14.2 | 射击练习：移动标靶 + Play 按钮 + 三次未击中结束 |
| 14.3 | 有一定难度的射击练习：标靶速度递增且可重置 |
| 14.4 | 难度等级：一组按钮选择起始难度 |
| 14.5 | 历史最高分：最高分持久化到文件 |
| 14.6 | 重构：`start_new_level()`、`prep_images()` |
| 14.7 | 扩展游戏：外星人射击、飞船盾牌、音效等 |
| 14.8 | 终极版《横向射击》 |

---

## 附录：项目最终完整代码

> 以下为按书中流程逐步开发完成后的最终版本，各文件均位于 `alien_invasion/` 文件夹中，`images/` 内含 `ship.bmp` 与 `alien.bmp`。

### `alien_invasion.py`

```python
import sys
from time import sleep

import pygame

from settings import Settings
from game_stats import GameStats
from scoreboard import Scoreboard
from button import Button
from ship import Ship
from bullet import Bullet
from alien import Alien


class AlienInvasion:
    """管理游戏资源和行为的类"""

    def __init__(self):
        """初始化游戏并创建游戏资源"""
        pygame.init()
        self.clock = pygame.time.Clock()
        self.settings = Settings()

        self.screen = pygame.display.set_mode(
            (self.settings.screen_width, self.settings.screen_height))
        pygame.display.set_caption("Alien Invasion")

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

    def run_game(self):
        """开始游戏的主循环"""
        while True:
            self._check_events()
            if self.game_active:
                self.ship.update()
                self._update_bullets()
                self._update_aliens()
            self._update_screen()
            self.clock.tick(60)

    def _check_events(self):
        """响应按键和鼠标事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_play_button(mouse_pos)

    def _check_play_button(self, mouse_pos):
        """在玩家单击 Play 按钮时开始新游戏"""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.game_active:
            # 还原游戏设置
            self.settings.initialize_dynamic_settings()

            # 重置游戏的统计信息
            self.stats.reset_stats()
            self.sb.prep_score()
            self.sb.prep_level()
            self.sb.prep_ships()
            self.game_active = True

            # 清空外星人列表和子弹列表
            self.bullets.empty()
            self.aliens.empty()

            # 创建一个新的外星舰队，并将飞船放在屏幕底部的中央
            self._create_fleet()
            self.ship.center_ship()

            # 隐藏光标
            pygame.mouse.set_visible(False)

    def _check_keydown_events(self, event):
        """响应按下"""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_q:
            sys.exit()
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()

    def _check_keyup_events(self, event):
        """响应释放"""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = False

    def _fire_bullet(self):
        """创建一颗子弹，并将其加入编组 bullets"""
        if len(self.bullets) < self.settings.bullets_allowed:
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)

    def _update_bullets(self):
        """更新子弹的位置并删除已消失的子弹"""
        # 更新子弹的位置
        self.bullets.update()

        # 删除已消失的子弹
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        """响应子弹和外星人的碰撞"""
        # 删除发生碰撞的子弹和外星人
        collisions = pygame.sprite.groupcollide(
            self.bullets, self.aliens, True, True)

        if collisions:
            for aliens in collisions.values():
                self.stats.score += self.settings.alien_points * len(aliens)
            self.sb.prep_score()
            self.sb.check_high_score()

        if not self.aliens:
            # 删除现有的所有子弹，并创建一个新的外星舰队
            self.bullets.empty()
            self._create_fleet()
            self.settings.increase_speed()

            # 提高等级
            self.stats.level += 1
            self.sb.prep_level()

    def _update_aliens(self):
        """检查是否有外星人位于屏幕边缘，并更新整个外星舰队的位置"""
        self._check_fleet_edges()
        self.aliens.update()

        # 检测外星人和飞船之间的碰撞
        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        # 检查是否有外星人到达了屏幕的下边缘
        self._check_aliens_bottom()

    def _check_fleet_edges(self):
        """在有外星人到达边缘时采取相应的措施"""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """将整个外星舰队向下移动，并改变它们的方向"""
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def _check_aliens_bottom(self):
        """检查是否有外星人到达了屏幕的下边缘"""
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= self.settings.screen_height:
                # 像飞船被撞到一样进行处理
                self._ship_hit()
                break

    def _ship_hit(self):
        """响应飞船和外星人的碰撞"""
        if self.stats.ships_left > 0:
            # 将 ships_left 减 1 并更新记分牌
            self.stats.ships_left -= 1
            self.sb.prep_ships()

            # 清空外星人列表和子弹列表
            self.bullets.empty()
            self.aliens.empty()

            # 创建一个新的外星舰队，并将飞船放在屏幕底部的中央
            self._create_fleet()
            self.ship.center_ship()

            # 暂停
            sleep(0.5)
        else:
            self.game_active = False
            pygame.mouse.set_visible(True)

    def _create_fleet(self):
        """创建一个外星舰队"""
        # 创建一个外星人，再不断添加，直到没有空间添加外星人为止
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size

        current_x, current_y = alien_width, alien_height
        while current_y < (self.settings.screen_height - 3 * alien_height):
            while current_x < (self.settings.screen_width - 2 * alien_width):
                self._create_alien(current_x, current_y)
                current_x += 2 * alien_width

            # 添加一行外星人后，重置 x 值并递增 y 值
            current_x = alien_width
            current_y += 2 * alien_height

    def _create_alien(self, x_position, y_position):
        """创建一个外星人，并将其加入外星舰队"""
        new_alien = Alien(self)
        new_alien.x = x_position
        new_alien.rect.x = x_position
        new_alien.rect.y = y_position
        self.aliens.add(new_alien)

    def _update_screen(self):
        """更新屏幕上的图像，并切换到新屏幕"""
        self.screen.fill(self.settings.bg_color)
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()
        self.ship.blitme()
        self.aliens.draw(self.screen)

        # 显示得分
        self.sb.show_score()

        # 如果游戏处于非活动状态，就绘制 Play 按钮
        if not self.game_active:
            self.play_button.draw_button()

        pygame.display.flip()


if __name__ == '__main__':
    # 创建游戏实例并运行游戏
    ai = AlienInvasion()
    ai.run_game()
```

### `settings.py`

```python
class Settings:
    """存储游戏《外星人入侵》中所有设置的类"""

    def __init__(self):
        """初始化游戏的静态设置"""
        # 屏幕设置
        self.screen_width = 1200
        self.screen_height = 800
        self.bg_color = (230, 230, 230)

        # 飞船设置
        self.ship_limit = 3

        # 子弹设置
        self.bullet_width = 3
        self.bullet_height = 15
        self.bullet_color = (60, 60, 60)
        self.bullets_allowed = 3

        # 外星人设置
        self.fleet_drop_speed = 10

        # 以什么速度加快游戏的节奏
        self.speedup_scale = 1.1
        # 外星人分数的提高速度
        self.score_scale = 1.5

        self.initialize_dynamic_settings()

    def initialize_dynamic_settings(self):
        """初始化随游戏进行而变化的设置"""
        self.ship_speed = 1.5
        self.bullet_speed = 2.5
        self.alien_speed = 1.0

        # fleet_direction 为 1 表示向右，为 -1 表示向左
        self.fleet_direction = 1

        # 记分设置
        self.alien_points = 50

    def increase_speed(self):
        """提高速度设置的值和外星人分数"""
        self.ship_speed *= self.speedup_scale
        self.bullet_speed *= self.speedup_scale
        self.alien_speed *= self.speedup_scale

        self.alien_points = int(self.alien_points * self.score_scale)
```

### `ship.py`

```python
import pygame
from pygame.sprite import Sprite


class Ship(Sprite):
    """管理飞船的类"""

    def __init__(self, ai_game):
        """初始化飞船并设置其起始位置"""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.screen_rect = ai_game.screen.get_rect()

        # 加载飞船图像并获取其外接矩形
        self.image = pygame.image.load('images/ship.bmp')
        self.rect = self.image.get_rect()

        # 每艘新飞船都放在屏幕底部的中央
        self.rect.midbottom = self.screen_rect.midbottom

        # 在飞船的属性 x 中存储一个浮点数
        self.x = float(self.rect.x)

        # 移动标志（飞船一开始不移动）
        self.moving_right = False
        self.moving_left = False

    def update(self):
        """根据移动标志调整飞船的位置"""
        # 更新飞船的属性 x 的值，而不是其外接矩形的属性 x 的值
        if self.moving_right and self.rect.right < self.screen_rect.right:
            self.x += self.settings.ship_speed
        if self.moving_left and self.rect.left > 0:
            self.x -= self.settings.ship_speed

        # 根据 self.x 更新 rect 对象
        self.rect.x = self.x

    def blitme(self):
        """在指定位置绘制飞船"""
        self.screen.blit(self.image, self.rect)

    def center_ship(self):
        """将飞船放在屏幕底部的中央"""
        self.rect.midbottom = self.screen_rect.midbottom
        self.x = float(self.rect.x)
```

### `bullet.py`

```python
import pygame
from pygame.sprite import Sprite


class Bullet(Sprite):
    """管理飞船所发射子弹的类"""

    def __init__(self, ai_game):
        """在飞船的当前位置创建一个子弹对象"""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.color = self.settings.bullet_color

        # 在 (0, 0) 处创建一个表示子弹的矩形，再设置正确的位置
        self.rect = pygame.Rect(0, 0, self.settings.bullet_width,
                                self.settings.bullet_height)
        self.rect.midtop = ai_game.ship.rect.midtop

        # 存储用浮点数表示的子弹位置
        self.y = float(self.rect.y)

    def update(self):
        """向上移动子弹"""
        # 更新子弹的准确位置
        self.y -= self.settings.bullet_speed
        # 更新表示子弹的 rect 的位置
        self.rect.y = self.y

    def draw_bullet(self):
        """在屏幕上绘制子弹"""
        pygame.draw.rect(self.screen, self.color, self.rect)
```

### `alien.py`

```python
import pygame
from pygame.sprite import Sprite


class Alien(Sprite):
    """表示单个外星人的类"""

    def __init__(self, ai_game):
        """初始化外星人并设置其起始位置"""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings

        # 加载外星人图像并设置其 rect 属性
        self.image = pygame.image.load('images/alien.bmp')
        self.rect = self.image.get_rect()

        # 每个外星人最初都在屏幕的左上角附近
        self.rect.x = self.rect.width
        self.rect.y = self.rect.height

        # 存储外星人的精确水平位置
        self.x = float(self.rect.x)

    def update(self):
        """向左或向右移动外星人"""
        self.x += self.settings.alien_speed * self.settings.fleet_direction
        self.rect.x = self.x

    def check_edges(self):
        """如果外星人位于屏幕边缘，就返回 True"""
        screen_rect = self.screen.get_rect()
        return (self.rect.right >= screen_rect.right) or (self.rect.left <= 0)
```

### `game_stats.py`

```python
class GameStats:
    """跟踪游戏的统计信息"""

    def __init__(self, ai_game):
        """初始化统计信息"""
        self.settings = ai_game.settings
        self.reset_stats()
        # 在任何情况下都不应重置最高分
        self.high_score = 0

    def reset_stats(self):
        """初始化在游戏运行期间可能变化的统计信息"""
        self.ships_left = self.settings.ship_limit
        self.score = 0
        self.level = 1
```

### `button.py`

```python
import pygame.font


class Button:
    """为游戏创建按钮的类"""

    def __init__(self, ai_game, msg):
        """初始化按钮的属性"""
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()

        # 设置按钮的尺寸和其他属性
        self.width, self.height = 200, 50
        self.button_color = (0, 135, 0)
        self.text_color = (255, 255, 255)
        self.font = pygame.font.SysFont(None, 48)

        # 创建按钮的 rect 对象，并使其居中
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = self.screen_rect.center

        # 按钮的标签只需创建一次
        self._prep_msg(msg)

    def _prep_msg(self, msg):
        """将 msg 渲染为图像，并使其在按钮上居中"""
        self.msg_image = self.font.render(msg, True, self.text_color,
                                          self.button_color)
        self.msg_image_rect = self.msg_image.get_rect()
        self.msg_image_rect.center = self.rect.center

    def draw_button(self):
        """绘制一个用颜色填充的按钮，再绘制文本"""
        self.screen.fill(self.button_color, self.rect)
        self.screen.blit(self.msg_image, self.msg_image_rect)
```

### `scoreboard.py`

```python
import pygame.font
from pygame.sprite import Group

from ship import Ship


class Scoreboard:
    """显示得分信息的类"""

    def __init__(self, ai_game):
        """初始化显示得分涉及的属性"""
        self.ai_game = ai_game
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()
        self.settings = ai_game.settings
        self.stats = ai_game.stats

        # 显示得分信息时使用的字体设置
        self.text_color = (30, 30, 30)
        self.font = pygame.font.SysFont(None, 48)

        # 准备初始得分图像
        self.prep_score()
        self.prep_high_score()
        self.prep_level()
        self.prep_ships()

    def prep_score(self):
        """将得分渲染为图像"""
        rounded_score = round(self.stats.score, -1)
        score_str = f"{rounded_score:,}"
        self.score_image = self.font.render(score_str, True,
                self.text_color, self.settings.bg_color)

        # 在屏幕右上角显示得分
        self.score_rect = self.score_image.get_rect()
        self.score_rect.right = self.screen_rect.right - 20
        self.score_rect.top = 20

    def prep_high_score(self):
        """将最高分渲染为图像"""
        high_score = round(self.stats.high_score, -1)
        high_score_str = f"{high_score:,}"
        self.high_score_image = self.font.render(high_score_str, True,
                self.text_color, self.settings.bg_color)

        # 将最高分放在屏幕顶部的中央
        self.high_score_rect = self.high_score_image.get_rect()
        self.high_score_rect.centerx = self.screen_rect.centerx
        self.high_score_rect.top = self.score_rect.top

    def prep_level(self):
        """将等级渲染为图像"""
        level_str = str(self.stats.level)
        self.level_image = self.font.render(level_str, True,
                self.text_color, self.settings.bg_color)

        # 将等级放在得分下方
        self.level_rect = self.level_image.get_rect()
        self.level_rect.right = self.score_rect.right
        self.level_rect.top = self.score_rect.bottom + 10

    def prep_ships(self):
        """显示还余下多少艘飞船"""
        self.ships = Group()
        for ship_number in range(self.stats.ships_left):
            ship = Ship(self.ai_game)
            ship.rect.x = 10 + ship_number * ship.rect.width
            ship.rect.y = 10
            self.ships.add(ship)

    def show_score(self):
        """在屏幕上显示得分、等级和余下的飞船数"""
        self.screen.blit(self.score_image, self.score_rect)
        self.screen.blit(self.high_score_image, self.high_score_rect)
        self.screen.blit(self.level_image, self.level_rect)
        self.ships.draw(self.screen)

    def check_high_score(self):
        """检查是否诞生了新的最高分"""
        if self.stats.score > self.stats.high_score:
            self.stats.high_score = self.stats.score
            self.prep_high_score()
```

---

*整理完毕 · 全文覆盖《Python 编程从入门到实践》（第 3 版）第 12～14 章 与全部"动手试一试"练习*
