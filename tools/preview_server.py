"""把游戏画面推到浏览器里实时预览（沙箱/无显示器环境专用）。

为什么需要它：本沙箱没有显示器，`SDL_VIDEODRIVER=dummy` 只能让 Pygame 正常
「画」到内存里，看不到窗口。这个脚本做三件事：

1. 在后台线程里跑游戏主循环（视频驱动设为 dummy，所以不需要屏幕）；
2. 把画面编码成 JPEG 推给浏览器，三种通道逐级降级：
     ① WebSocket 二进制帧（首选，延迟最低、不受代理缓冲影响）
     ② MJPEG 流 `/stream`（浏览器 <img> 直读，兼容性最好）
     ③ 轮询 `/frame.jpg`（最兜底，任何环境都能出画面）
3. 浏览器里的键盘/鼠标事件 POST 到 `/input` 被翻译成 pygame 事件塞回游戏，
   所以在浏览器里能真正地玩。

## 可用性上的几个关键设计（都是踩过坑之后加的）

* **游戏循环永不退出**：游戏线程是个 `while` 循环，一局结束/被 Q 打断就自动重开
  一局。早期版本按 Q 会让游戏线程直接结束，结果预览变成一张永久冻结的静态图，
  而且因为没有任何报错，看起来「就像坏了一样」。
* **编码与游戏循环解耦**：游戏线程只做一次廉价的 RGB 快照，JPEG 编码放到编码
  线程。否则一次编码要 10ms 左右，会把游戏从 60fps 拖慢到 30fps 左右——而本游戏
  所有速度都是「每帧多少像素」，帧率掉一半，飞船和舰队就都变成慢动作。
* **像无人观看时自动降档**：没有观众时游戏自动重开并把帧率降到 10fps 省 CPU；
  有人连上来立刻恢复 60fps 和全新一局。

用法::

    uv run python tools/preview_server.py             # 默认 8000 端口
    uv run python tools/preview_server.py --port 8080 --fps 30 --scale 0.6

按键：← → 移动，空格射击，P 开始新游戏（也可以在页面上点按钮玩，键盘没反应时
点一下画面即可获得焦点）。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import queue
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# 必须在 import pygame 之前设置，否则 Pygame 会尝试连接显示器并报错
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alien_invasion import AlienInvasion  # noqa: E402
from alien_invasion.settings import Settings  # noqa: E402

# --------------------------------------------------------------------- 共享状态
_lock = threading.Lock()
_input_queue: "queue.Queue[pygame.event.Event]" = queue.Queue()
_raw_frame: bytes | None = None            # 游戏线程写的原始 RGB 快照
_raw_size: tuple[int, int] = (0, 0)
_raw_seq = 0                               # 每帧 +1：编码线程用它判断有没有新画面
_latest_jpeg: bytes | None = None
_jpeg_seq = 0
_state: dict = {"ready": False}            # 给 /state 的只读快照
_game: AlienInvasion | None = None
_restart_request = threading.Event()
_autostart = threading.Event()      # /restart 之后要顺手把新一局「开始」掉
_stop = threading.Event()
_last_client_ts = time.time()
_last_input_ts = time.time()
_input_count = 0
_ws_clients: set["WSClient"] = set()
_encode_count = 0
_game_frames = 0          # 游戏实际渲染了多少帧（用来验证是不是跑在 60fps）
_errors: list[str] = []

GAME_FPS = 60          # 游戏内部帧率（所有速度都是按这个帧率校准的）
IDLE_FPS = 10          # 无人观看时的降档帧率

PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Alien Invasion · 实时预览</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #12151c; color: #e6e9ef;
         font: 14px/1.6 -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 16px; }
  h1 { font-size: 15px; font-weight: 600; margin: 0; letter-spacing: .06em; color: #cfd6e4; }
  .stage { position: relative; border-radius: 10px; overflow: hidden; line-height: 0;
           box-shadow: 0 12px 40px rgba(0,0,0,.55); background: #e6e6e6; outline: none;
           width: min(94vw, 1000px); }
  .stage:focus-visible { box-shadow: 0 0 0 3px #3b82f6, 0 12px 40px rgba(0,0,0,.55); }
  canvas { display: block; width: 100%; height: auto; cursor: crosshair; }
  .hint { color: #98a2b3; font-size: 13px; text-align: center; max-width: 780px; }
  kbd { background: #222833; border: 1px solid #333c4a; border-bottom-width: 2px; border-radius: 5px;
        padding: 1px 6px; font-size: 12px; color: #d5dae5; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
  button { background: #222833; color: #e6e9ef; border: 1px solid #333c4a; border-radius: 9px;
           padding: 9px 16px; font-size: 14px; cursor: pointer; user-select: none;
           touch-action: none; -webkit-user-select: none; }
  button:hover { background: #2b3340; }
  button.active { background: #2f6f3f; border-color: #3f8f52; }
  #big { padding: 11px 22px; background: #0f7a33; border-color: #10a344; font-weight: 600; }
  #big:hover { background: #128a3c; }
  #status { color: #7d879a; font-size: 12px; font-variant-numeric: tabular-nums; text-align: center; }
  #banner { display: none; max-width: 760px; padding: 10px 14px; border-radius: 9px;
            background: #4a1f22; border: 1px solid #7f2b30; color: #ffd9dc; font-size: 13px; }
  .kbd-note { color: #ffcf7a; display: none; }
</style>
</head>
<body>
  <h1>ALIEN INVASION · 实时预览</h1>
  <div id="banner"></div>
  <canvas id="view" class="stage" tabindex="0"></canvas>
  <div class="hint">
    <kbd>←</kbd> <kbd>→</kbd> 移动飞船 · <kbd>空格</kbd> 射击 · <kbd>P</kbd> 开始游戏
    <span class="kbd-note" id="kbdnote">（键盘没反应？先点一下画面，或者直接用下面的按钮）</span>
  </div>
  <div class="row">
    <button id="big">开始 / 重新开始</button>
    <button id="left">◀ 左移</button>
    <button id="right">右移 ▶</button>
    <button id="fire">射击</button>
  </div>
  <div id="status">连接中…</div>

<script>
const canvas = document.getElementById('view');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
const bannerEl = document.getElementById('banner');
const kbdNote = document.getElementById('kbdnote');

let mode = 'ws';            // ws | mjpeg | poll
let lastFrameAt = 0;
let frames = 0;
let fps = 0;
let lastStatsAt = performance.now();
let ws = null;
let drawing = false;
let pendingBlob = null;
let screenSize = [1200, 800];   // 游戏逻辑分辨率（从 /state 拿）
let keyEventsSent = 0;

function setStatus(t) { statusEl.textContent = t; }
function showBanner(html) { bannerEl.innerHTML = html; bannerEl.style.display = 'block'; }
function hideBanner() { bannerEl.style.display = 'none'; }

// ------------------------------------------------------------ 画面渲染
// 统一画到 canvas 上：三种通道（WebSocket / MJPEG / 轮询）都走同一条绘制路径
async function drawBlob(blob) {
  if (drawing) { pendingBlob = blob; return; }   // 解码跟不上就丢帧，别排队
  drawing = true;
  try {
    const bmp = await createImageBitmap(blob);
    if (canvas.width !== bmp.width || canvas.height !== bmp.height) {
      canvas.width = bmp.width;
      canvas.height = bmp.height;
    }
    ctx.drawImage(bmp, 0, 0);
    bmp.close();
    lastFrameAt = performance.now();
    frames++;
  } catch (e) {
    // 偶尔半张图解码失败很正常，忽略即可
  } finally {
    drawing = false;
    if (pendingBlob) { const b = pendingBlob; pendingBlob = null; drawBlob(b); }
  }
}

function markFrame() { lastFrameAt = performance.now(); frames++; }

// ① WebSocket：首选通道
function startWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  try { ws = new WebSocket(proto + '//' + location.host + '/ws'); }
  catch (e) { return startMjpeg(); }
  ws.binaryType = 'blob';
  ws.onopen = () => { mode = 'ws'; hideBanner(); setStatus('实时（WebSocket）· 连接已建立'); };
  ws.onmessage = (ev) => { if (ev.data instanceof Blob) drawBlob(ev.data); };
  ws.onerror = () => { /* 交给 onclose 处理 */ };
  ws.onclose = () => { if (mode === 'ws') startMjpeg(); };
}

// ② MJPEG：兼容性最好
function startMjpeg() {
  mode = 'mjpeg';
  const img = new Image();
  img.onload = () => {
    if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
    }
    ctx.drawImage(img, 0, 0);
    markFrame();
    if (mode === 'mjpeg') hideBanner();
  };
  img.onerror = () => { if (mode === 'mjpeg') startPoll(); };
  img.src = '/stream?t=' + Date.now();
  setStatus('实时（MJPEG 流）…');
  // 3 秒还没画面就当作这条通道不可用
  const t0 = performance.now();
  const guard = setInterval(() => {
    if (mode !== 'mjpeg') { clearInterval(guard); return; }
    if (performance.now() - t0 > 3000 && frames === 0) { clearInterval(guard); startPoll(); }
  }, 500);
}

// ③ 轮询：最兜底，任何环境都能出画面
function startPoll() {
  if (mode === 'poll') return;
  mode = 'poll';
  setStatus('逐帧模式（无流式通道可用）');
  let busy = false;
  const tick = async () => {
    if (mode !== 'poll') return;
    if (!busy) {
      busy = true;
      try {
        const r = await fetch('/frame.jpg?t=' + Date.now(), { cache: 'no-store' });
        if (r.ok) await drawBlob(await r.blob());
      } catch (e) { /* 下一轮再试 */ }
      busy = false;
    }
    setTimeout(tick, 55);
  };
  tick();
}

// ------------------------------------------------------------ 状态栏
setInterval(() => {
  const now = performance.now();
  const dt = (now - lastStatsAt) / 1000;
  if (dt >= 1) { fps = Math.round(frames / dt); frames = 0; lastStatsAt = now; }
  const age = lastFrameAt ? Math.round((now - lastFrameAt) / 1000) : -1;
  const modeText = { ws: 'WebSocket', mjpeg: 'MJPEG 流', poll: '逐帧' }[mode];
  setStatus(`通道 ${modeText} · 画面 ${fps} fps · 延迟 ${age < 0 ? '—' : age + 's'} · 已发送输入 ${keyEventsSent} 次`);
  if (age > 3) {
    showBanner('⚠️ 已经 ' + age + ' 秒没有新画面了。可以试试：①刷新页面 ②确认服务还在运行 ' +
               '（终端里应有「预览服务已启动」），如果服务重启过，请刷新本页面。');
    if (mode === 'ws') { try { ws.close(); } catch (e) {} }
  }
  // 键盘焦点提示：只有真的一直收不到按键才提示
  if (keyEventsSent === 0) kbdNote.style.display = 'inline';
}, 1000);

// ------------------------------------------------------------ 输入
async function send(payload) {
  keyEventsSent++;
  try {
    await fetch('/input', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    });
  } catch (e) { /* 忽略：下一帧还会重试 */ }
}

// 浏览器按键 → 游戏按键。注意：这里故意不支持 Q（Q 会结束游戏循环）
const KEYMAP = {
  ArrowLeft: 'ArrowLeft', ArrowRight: 'ArrowRight',
  Space: 'Space', ' ': 'Space', KeyP: 'p', KeyQ: 'q',
};

function keyName(e) {
  if (KEYMAP[e.code]) return KEYMAP[e.code];
  if (KEYMAP[e.key]) return KEYMAP[e.key];
  return null;
}

// 记录「当前按住不放的键」，用于在窗口失焦等意外情况下补发 keyup
const held = new Set();

function pressKey(name) {
  if (held.has(name)) return;
  held.add(name);
  send({ type: 'keydown', key: name });
}
function releaseKey(name) {
  if (!held.has(name)) return;
  held.delete(name);
  send({ type: 'keyup', key: name });
}
function releaseAll() { for (const n of Array.from(held)) releaseKey(n); }

addEventListener('keydown', (e) => {
  const name = keyName(e);
  if (!name) return;
  if (e.code === 'KeyQ') { e.preventDefault(); return; }   // 禁用 Q，别把预览玩坏
  e.preventDefault();
  if (!e.repeat) pressKey(name);
}, true);

addEventListener('keyup', (e) => {
  const name = keyName(e);
  if (!name) return;
  e.preventDefault();
  releaseKey(name);
}, true);

// 失焦/切标签页时补发 keyup，否则飞船会一直往一个方向飘
addEventListener('blur', releaseAll);
document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAll(); });
// 鼠标在任何地方松开都要释放（只在按钮上监听会漏掉「按住后拖出去松手」）
addEventListener('pointerup', releaseAll);
addEventListener('pointercancel', releaseAll);

// 点画面 = 点游戏画面（比如点 Play 按钮），同时把焦点抢过来好接收键盘
canvas.addEventListener('mousedown', (e) => {
  canvas.focus();
  const r = canvas.getBoundingClientRect();
  if (r.width <= 0 || r.height <= 0) return;      // 画面还没出来时别算坐标
  send({
    type: 'click',
    x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
    y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
    screen_w: screenSize[0],
    screen_h: screenSize[1],
  });
});

// 屏幕按钮：按住不放 = 一直按住该键（pointer capture 保证拖出去也能收到 up）
function bindHold(id, key) {
  const el = document.getElementById(id);
  el.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    try { el.setPointerCapture(e.pointerId); } catch (err) {}
    el.classList.add('active');
    pressKey(key);
  });
  const up = () => { el.classList.remove('active'); releaseKey(key); };
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
  el.addEventListener('lostpointercapture', up);
}
bindHold('left', 'ArrowLeft');
bindHold('right', 'ArrowRight');
bindHold('fire', 'Space');

document.getElementById('big').addEventListener('click', async () => {
  canvas.focus();
  releaseAll();                            // 先把可能按住的方向键放开
  releaseKey('Space');
  setStatus('正在重新开局…');
  try {
    const r = await fetch('/restart', { method: 'POST' });
    const j = await r.json();
    if (j && j.ok) setStatus('新的一局已开始');
  } catch (e) {
    setStatus('重开失败，请刷新页面');
  }
});

// ------------------------------------------------------------ 启动
fetch('/state').then(r => r.json()).then(s => {
  if (s && s.screen) screenSize = s.screen;
}).catch(() => {});
canvas.focus();
startWS();
</script>
</body>
</html>
"""


# ===================================================================== 游戏线程
def _drain_events() -> list:
    """游戏主循环每帧调用它，把浏览器传来的事件一次性交给 Pygame。"""
    out = []
    while True:
        try:
            out.append(_input_queue.get_nowait())
        except queue.Empty:
            return out


# 浏览器里的按键名 → pygame 常量。
# ⚠️ 不能用 getattr(pygame, "K_" + name.lower()) 这种「拼名字」的偷懒写法：
#    pygame 的常量是 K_LEFT / K_SPACE / K_RETURN，而浏览器给的 key 是
#    "ArrowLeft" / "Space" / "Enter"，拼出来的 K_arrowleft、K_space、K_enter
#    全都不存在，结果就是按键毫无反应。
_KEY_NAMES = {
    "ArrowLeft": pygame.K_LEFT,
    "ArrowRight": pygame.K_RIGHT,
    "ArrowUp": pygame.K_UP,
    "ArrowDown": pygame.K_DOWN,
    "Space": pygame.K_SPACE,
    " ": pygame.K_SPACE,
    "Escape": pygame.K_ESCAPE,
    "Enter": pygame.K_RETURN,
    "p": pygame.K_p,
    "P": pygame.K_p,
    "q": pygame.K_q,
    "Q": pygame.K_q,
}


def _make_event(payload: dict):
    """把一条 JSON 输入翻译成 pygame 事件对象。"""
    kind = payload.get("type")
    if kind == "click":
        # 前端传的是 0~1 的相对坐标 + 游戏逻辑分辨率，这里换算成绝对像素
        w = int(payload.get("screen_w") or Settings().screen_width)
        h = int(payload.get("screen_h") or Settings().screen_height)
        pos = (int(payload.get("x", 0.5) * w), int(payload.get("y", 0.5) * h))
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)
    if kind in ("keydown", "keyup"):
        event_type = pygame.KEYDOWN if kind == "keydown" else pygame.KEYUP
        key_const = _KEY_NAMES.get(payload.get("key", ""))
        if key_const is None:
            return None
        return pygame.event.Event(event_type, key=key_const, mod=0, unicode="", scancode=0)
    return None


def _watched() -> bool:
    """现在有人在看画面吗？（决定要不要编码、要不要跑满帧率）

    三条通道都要算进来：WebSocket 连接、MJPEG 流、/frame.jpg 轮询。
    早期版本只看了 WS 和 /frame.jpg，结果「只用 MJPEG 流看」的时候服务器认为
    没人观看、干脆不编码，画面掉到 1fps（花屏一样的卡）。
    """
    with _lock:
        if _ws_clients:
            return True
    return time.time() - _last_client_ts < 3


def _game_thread(scale: float, quality: int, publish_every: int) -> None:
    """游戏主循环所在的线程。

    关键点：**这个循环永远不会真正结束**。一局打完（或者收到重开请求）就新建一个
    游戏实例继续跑。早期版本让线程跟着游戏一起结束，结果按一下 Q 就永久冻结。
    """
    global _game, _raw_frame, _raw_size, _raw_seq, _state, _encode_count

    def on_frame(game: AlienInvasion) -> None:
        # ⚠️ 注意 _state 也必须写进 global：漏掉它的话，下面那行 `_state = {...}`
        #    只会创建一个局部变量，模块级的 _state 永远是「正在重开」的占位符，
        #    /state 接口就会一直返回空状态（这个坑真的踩过一次）。
        global _raw_frame, _raw_size, _raw_seq, _game_frames, _state
        # 只做最便宜的「拍快照」（约 2ms），耗时的 JPEG 编码交给编码线程
        with _lock:
            _game_frames += 1
            _raw_frame = pygame.image.tostring(game.screen, "RGB")
            _raw_size = game.screen.get_size()
            _raw_seq += 1
            _state = {
                "ready": True,
                "game_active": game.game_active,
                "score": game.stats.score,
                "level": game.stats.level,
                "ships_left": game.stats.ships_left,
                "high_score": game.stats.high_score,
                "aliens": len(game.aliens),
                "bullets": len(game.bullets),
                "ship_x": game.ship.rect.x,
                "fleet_direction": game.settings.fleet_direction,
                "alien_speed": round(game.settings.alien_speed, 3),
                "alien_points": game.settings.alien_points,
                "screen": list(game.screen.get_size()),
                "fps_setting": game.settings.fps,
            }

        # 无人观看：自动重开一局并把帧率降下来省 CPU
        if not _watched():
            game.settings.fps = IDLE_FPS
            if game.game_active and time.time() - _last_client_ts > 15:
                game._start_game()          # 工具脚本直接调用，省得再造事件
        else:
            game.settings.fps = GAME_FPS
            _maybe_demo_restart(game)

    while not _stop.is_set():
        with _lock:
            _state = {"ready": False, "restarting": True}
        game = AlienInvasion(
            event_source=_drain_events, on_frame=on_frame, fit_window=False
        )
        with _lock:
            _game = game
        if _autostart.is_set():
            # 「开始 / 重新开始」按钮点过之后，直接把新一局开起来：
            # 只发一个「点击 Play」事件是同步且确定的做法，不依赖前端再补一次按键
            _autostart.clear()
            _input_queue.put(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, pos=game.play_button.rect.center, button=1
                )
            )
            _last_input_ts_now()
        try:
            game.run_game()                 # 只有 quit()/关窗口/重开请求才会返回
        except Exception as exc:            # 出任何意外都不能让预览彻底死掉
            _errors.append(f"{type(exc).__name__}: {exc}")
            print(f"[game] 出错，1 秒后重开新局: {exc!r}", flush=True)
            time.sleep(1.0)
        else:
            # 正常返回（Q / 重开请求 / 无人观看超时）：稍等一下就开新局
            _restart_request.clear()
            time.sleep(0.3)


def _maybe_demo_restart(game: AlienInvasion) -> None:
    """演示模式：游戏结束后如果一直没人操作，就自动重开，别让画面停在那里。"""
    if game.game_active:
        return
    if time.time() - _last_input_ts < 10:
        return
    # 走「假装玩家点了 Play」的路子，比直接调私有方法更贴近真实流程
    pos = game.play_button.rect.center
    _input_queue.put(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    _last_input_ts_now()


def _last_input_ts_now() -> None:
    global _last_input_ts
    _last_input_ts = time.time()


# ===================================================================== 编码线程
def _encode(raw: bytes, size: tuple[int, int], scale: float, quality: int) -> bytes:
    """RGB 原始数据 → JPEG 字节。"""
    img = Image.frombytes("RGB", size, raw)
    w, h = int(size[0] * scale), int(size[1] * scale)
    if (w, h) != size:
        img = img.resize((w, h), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def _encoder_thread(scale: float, quality: int, max_fps: float) -> None:
    """独立线程做 JPEG 编码 + 分发。

    为什么要单独开线程：编码一张 720x480 的 JPEG 大约 10ms。如果放在游戏循环里，
    60fps 的预算（16.7ms）会被吃掉一大半，游戏就掉到 30fps 左右；而本游戏所有
    速度都是「每帧多少像素」，帧率一掉，飞船和舰队就全变慢动作。
    """
    global _latest_jpeg, _jpeg_seq, _encode_count
    last_seq = -1
    interval = 1.0 / max(1.0, max_fps)
    while not _stop.is_set():
        t0 = time.perf_counter()
        with _lock:
            seq, raw, size = _raw_seq, _raw_frame, _raw_size
        if raw is None or seq == last_seq or not _watched():
            time.sleep(0.005)
            continue
        last_seq = seq
        try:
            jpeg = _encode(raw, size, scale, quality)
        except Exception as exc:
            _errors.append(f"encode: {exc!r}")
            time.sleep(0.2)
            continue
        with _lock:
            _latest_jpeg = jpeg
            _jpeg_seq += 1
            _encode_count += 1
            clients = list(_ws_clients)
        for client in clients:
            client.send_binary(jpeg)          # 出错时由 client 自己摘掉
        dt = time.perf_counter() - t0
        if dt < interval:
            time.sleep(interval - dt)


# ===================================================================== WebSocket
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WSClient:
    """一条 WebSocket 连接（服务端 → 客户端推 JPEG 帧，反向帧只用来收 close/ping）。"""

    def __init__(self, conn, addr) -> None:
        self.conn = conn
        self.addr = addr
        self.write_lock = threading.Lock()
        self.alive = True

    # ---- 发送 ----
    def send_binary(self, payload: bytes) -> None:
        n = len(payload)
        header = bytearray([0x80 | 0x2])            # FIN + binary
        if n < 126:
            header.append(n)
        elif n < 65536:
            header.append(126)
            header += struct.pack(">H", n)
        else:
            header.append(127)
            header += struct.pack(">Q", n)
        try:
            with self.write_lock:
                self.conn.sendall(bytes(header) + payload)
        except OSError:
            self.close()

    def close(self) -> None:
        if not self.alive:
            return
        self.alive = False
        with _lock:
            _ws_clients.discard(self)
        try:
            self.conn.close()
        except OSError:
            pass

    # ---- 接收（必须读，否则客户端的 close 帧会一直堆在缓冲区里）----
    def reader_loop(self) -> None:
        try:
            while self.alive and not _stop.is_set():
                header = self._recv_exact(2)
                if header is None:
                    break
                opcode = header[0] & 0x0F
                masked = bool(header[1] & 0x80)
                length = header[1] & 0x7F
                if length == 126:
                    length = struct.unpack(">H", self._recv_exact(2))[0]
                elif length == 127:
                    length = struct.unpack(">Q", self._recv_exact(8))[0]
                mask = self._recv_exact(4) if masked else None
                payload = self._recv_exact(length) if length else b""
                if payload is None:
                    break
                if mask:
                    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                if opcode == 0x8:                # close
                    break
                if opcode == 0x9:                # ping → pong
                    with self.write_lock:
                        self.conn.sendall(b"\x8a" + bytes([len(payload)]) + payload)
        except (OSError, struct.error, TypeError):
            pass
        finally:
            self.close()

    def _recv_exact(self, n: int):
        buf = b""
        while len(buf) < n:
            chunk = self.conn.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf


# ===================================================================== HTTP 服务
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AlienInvasionPreview/2.0"

    def log_message(self, fmt, *args):  # 静音访问日志，保留错误
        pass

    # -------------------------------------------------------------- GET
    def do_GET(self):
        global _last_client_ts
        path = self.path.split("?")[0]
        if path == "/":
            self._bytes(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/ws":
            self._websocket()
        elif path == "/stream":
            self._stream()
        elif path == "/frame.jpg":
            _last_client_ts = time.time()
            self._one_frame()
        elif path == "/healthz":
            self._json({
                "ok": True,
                "running": not _stop.is_set(),
                "game_frames": _game_frames,
                "encoded_frames": _encode_count,
                "ws_clients": len(_ws_clients),
                "errors": _errors[-5:],
            })
        elif path == "/state":
            with _lock:
                self._json(_state)
        else:
            self.send_error(404)

    # -------------------------------------------------------------- POST
    def do_POST(self):
        global _input_count
        path = self.path.split("?")[0]
        if path == "/restart":
            _restart_request.set()
            _autostart.set()
            with _lock:
                game = _game
            if game is not None:
                game.quit()                      # 游戏线程会立刻开新的一局
            self._json({"ok": True, "restarting": True})
            return
        if path != "/input":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self.send_error(400, "bad json")
            return
        event = _make_event(payload)
        if event is not None:
            _input_queue.put(event)
            with _lock:
                _input_count += 1
            _last_input_ts_now()
        self._json({"ok": True})

    # -------------------------------------------------------------- 工具
    def _bytes(self, body: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict):
        self._bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json")

    def _one_frame(self):
        jpeg = self._wait_for_new_frame(-1, 1.0)
        if jpeg is None:
            self.send_error(503, "no frame yet")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(jpeg)

    def _wait_for_new_frame(self, after_seq: int, timeout: float):
        """等一张比 after_seq 更新的 JPEG；超时返回当前最新的一张（可能为 None）。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with _lock:
                if _latest_jpeg is not None and _jpeg_seq > after_seq:
                    return _latest_jpeg
            time.sleep(0.005)
        with _lock:
            return _latest_jpeg

    def _stream(self):
        """MJPEG：一条永不结束的 multipart 响应，浏览器 <img> 直接就能放。"""
        global _last_client_ts
        boundary = "alienframe"
        self.send_response(200)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary}")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        _last_client_ts = time.time()
        last_seq = -1
        try:
            while not _stop.is_set():
                jpeg = self._wait_for_new_frame(last_seq, 1.0)
                if jpeg is None:
                    continue
                with _lock:
                    last_seq = _jpeg_seq
                _last_client_ts = time.time()
                self.wfile.write(f"--{boundary}\r\n".encode())
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # 浏览器关掉页面了，正常现象

    def _websocket(self):
        """WebSocket 握手 + 注册为帧接收方（RFC 6455，服务端只推二进制帧）。"""
        global _last_client_ts
        key = self.headers.get("Sec-WebSocket-Key")
        upgrade = (self.headers.get("Upgrade") or "").lower()
        if not key or "websocket" not in upgrade:
            self.send_error(400, "expecting websocket upgrade")
            return
        accept = base64.b64encode(
            hashlib.sha1((key + WS_GUID).encode()).digest()
        ).decode()
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        if hasattr(self.wfile, "flush"):
            self.wfile.flush()

        client = WSClient(self.connection, self.client_address)
        with _lock:
            _ws_clients.add(client)
        _last_client_ts = time.time()
        self.close_connection = True
        client.reader_loop()             # 阻塞在这里直到对端关闭


def main() -> None:
    parser = argparse.ArgumentParser(description="浏览器实时预览《外星人入侵》")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（0.0.0.0 才能被预览代理访问）")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--fps", type=float, default=45, help="推流帧率上限（游戏内部固定 60fps）")
    parser.add_argument("--scale", type=float, default=0.6, help="推流缩放比例")
    parser.add_argument("--quality", type=int, default=65, help="JPEG 质量")
    parser.add_argument("--publish-every", type=int, default=1, help="每几帧推一张（1=每帧）")
    args = parser.parse_args()

    threading.Thread(
        target=_game_thread, args=(args.scale, args.quality, args.publish_every), daemon=True
    ).start()
    threading.Thread(
        target=_encoder_thread, args=(args.scale, args.quality, args.fps), daemon=True
    ).start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"预览服务已启动： http://{args.host}:{args.port}/  （Ctrl+C 退出）", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
