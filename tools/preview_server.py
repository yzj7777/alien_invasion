"""把游戏画面推到浏览器里实时预览（沙箱/无显示器环境专用）。

为什么需要它：本沙箱没有显示器，`SDL_VIDEODRIVER=dummy` 只能让 Pygame 正常
「画」到内存里，看不到窗口。这个脚本做三件事：

1. 在主线程之外的线程里跑游戏主循环（视频驱动设为 dummy，所以不需要屏幕）；
2. 每两帧把 `screen` 这个 surface 缩放、编码成 JPEG，通过 MJPEG
   (multipart/x-mixed-replace) 推给浏览器 `<img>`，形成连续画面；
3. 浏览器里的键盘/鼠标事件 POST 到 `/input`，被翻译成 pygame 事件塞回游戏，
   所以**在浏览器里能真正地玩**。

用法::

    uv run python tools/preview_server.py             # 默认 8000 端口
    uv run python tools/preview_server.py --port 8080 --fps 30 --scale 0.6

按键：← → 移动，空格射击，P 开始新游戏，Q 退出（浏览器里按 Q 只是让游戏循环停止，
服务器仍在，刷新页面即可重开）。

注意：这是「开发者工具」，正式玩游戏请在有显示器的机器上运行
`uv run alien-invasion`。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import queue
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

# --------------------------------------------------------------------- 全局状态
_input_queue: "queue.Queue[pygame.event.Event]" = queue.Queue()
_latest_frame: bytes | None = None          # 最新一帧的 JPEG 字节
_frame_lock = threading.Lock()
_game: AlienInvasion | None = None
_frame_hooks: list = []                     # 录制用：每个帧回调
_stop = threading.Event()
_frame_count = 0

PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Alien Invasion · 实时预览</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #12151c; color: #e6e9ef;
         font: 14px/1.6 -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 18px; }
  h1 { font-size: 16px; font-weight: 600; margin: 0; letter-spacing: .04em; }
  .stage { position: relative; border-radius: 10px; overflow: hidden;
           box-shadow: 0 12px 40px rgba(0,0,0,.55); background: #e6e6e6; }
  img { display: block; width: min(92vw, 1000px); height: auto; image-rendering: auto; cursor: crosshair; }
  .hint { color: #98a2b3; font-size: 13px; text-align: center; max-width: 720px; }
  kbd { background: #222833; border: 1px solid #333c4a; border-bottom-width: 2px; border-radius: 5px;
        padding: 1px 6px; font-size: 12px; color: #d5dae5; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
  button { background: #222833; color: #e6e9ef; border: 1px solid #333c4a; border-radius: 8px;
           padding: 7px 14px; font-size: 13px; cursor: pointer; }
  button:hover { background: #2b3340; }
  #status { font-variant-numeric: tabular-nums; color: #7d879a; font-size: 12px; }
</style>
</head>
<body>
  <h1>ALIEN INVASION · 实时预览</h1>
  <div class="stage"><img id="view" alt="game view"></div>
  <div class="hint">
    <kbd>←</kbd> <kbd>→</kbd> 移动飞船 · <kbd>空格</kbd> 射击 · <kbd>P</kbd> 开始游戏 ·
    <kbd>Q</kbd> 结束游戏循环 · 也可以直接<b>点/按画面</b>上的绿色 Play 按钮
  </div>
  <div class="row">
    <button id="play">开始游戏 (P)</button>
    <button id="left">◀ 左</button>
    <button id="right">▶ 右</button>
    <button id="fire">射击 (空格)</button>
    <button id="quit">结束 (Q)</button>
  </div>
  <div id="status">连接中…</div>

<script>
const view = document.getElementById('view');
const statusEl = document.getElementById('status');
let mode = 'stream';
let lastFrameAt = Date.now();
let pollTimer = null;

function setStatus(t) { statusEl.textContent = t; }

// ---- 画面：优先用 MJPEG 流，超时或出错就退回到每秒抓图 ----
function useStream() {
  mode = 'stream';
  view.src = '/stream?t=' + Date.now();
}
view.addEventListener('load', () => { lastFrameAt = Date.now(); });

function usePolling() {
  if (mode === 'poll') return;
  mode = 'poll';
  setStatus('已切换到逐帧模式');
  const tick = () => {
    fetch('/frame.jpg?t=' + Date.now(), { cache: 'no-store' })
      .then(r => r.blob())
      .then(b => { view.src = URL.createObjectURL(b); lastFrameAt = Date.now(); })
      .catch(() => {});
    pollTimer = setTimeout(tick, 60);
  };
  tick();
}

setInterval(() => {
  if (mode === 'stream' && Date.now() - lastFrameAt > 3000) usePolling();
  else if (mode === 'stream') setStatus('实时流 · ' + Math.round((Date.now() - lastFrameAt) / 1000) + 's 前更新');
}, 1000);
useStream();

// ---- 输入：把浏览器事件翻译成游戏事件 ----
async function send(payload) {
  try {
    await fetch('/input', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (e) { /* 忽略：下一帧还会重试 */ }
}

const KEYMAP = {
  ArrowLeft: 'ArrowLeft', ArrowRight: 'ArrowRight', Space: 'Space', ' ': 'Space',
  KeyP: 'p', KeyQ: 'q', Escape: 'Escape', Enter: 'Enter',
};

function keyName(e) {
  if (KEYMAP[e.code]) return KEYMAP[e.code];
  if (KEYMAP[e.key]) return KEYMAP[e.key];
  return null;
}

document.addEventListener('keydown', (e) => {
  const k = keyName(e);
  if (!k) return;
  e.preventDefault();
  if (!e.repeat) send({ type: 'keydown', key: k });
});
document.addEventListener('keyup', (e) => {
  const k = keyName(e);
  if (!k) return;
  e.preventDefault();
  send({ type: 'keyup', key: k });
});

// 点画面 = 点游戏画面（Play 按钮靠这个）
view.addEventListener('mousedown', (e) => {
  const r = view.getBoundingClientRect();
  send({
    type: 'click',
    x: (e.clientX - r.left) / r.width,
    y: (e.clientY - r.top) / r.height,
  });
  view.focus();
});

// 屏幕按钮
document.getElementById('play').onclick  = () => { send({type: 'keydown', key: 'p'}); };
document.getElementById('fire').onclick  = () => { send({type: 'keydown', key: 'Space'}); };
document.getElementById('quit').onclick  = () => { send({type: 'keydown', key: 'q'}); };
const hold = (id, key) => {
  const el = document.getElementById(id);
  el.addEventListener('pointerdown', () => send({type: 'keydown', key}));
  el.addEventListener('pointerup', () => send({type: 'keyup', key}));
  el.addEventListener('pointerleave', () => send({type: 'keyup', key}));
};
hold('left', 'ArrowLeft');
hold('right', 'ArrowRight');
</script>
</body>
</html>
"""


# --------------------------------------------------------------------- 游戏线程
def _build_events() -> list:
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
#    全都不存在，结果就是按键毫无反应。老老实实写一张映射表。
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
        # 前端传的是 0~1 的相对坐标，这里换算成 1200x800 里的绝对像素
        stage_w, stage_h = Settings().screen_width, Settings().screen_height
        pos = (int(payload.get("x", 0.5) * stage_w), int(payload.get("y", 0.5) * stage_h))
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)
    if kind in ("keydown", "keyup"):
        event_type = pygame.KEYDOWN if kind == "keydown" else pygame.KEYUP
        key_const = _KEY_NAMES.get(payload.get("key", ""))
        if key_const is None:
            return None
        return pygame.event.Event(event_type, key=key_const, mod=0, unicode="", scancode=0)
    return None


def _game_state() -> dict:
    """把游戏的关键状态打包成 JSON（供 /state 调试接口使用）。"""
    if _game is None:
        return {"ready": False}
    return {
        "ready": True,
        "game_active": _game.game_active,
        "score": _game.stats.score,
        "level": _game.stats.level,
        "ships_left": _game.stats.ships_left,
        "high_score": _game.stats.high_score,
        "aliens": len(_game.aliens),
        "bullets": len(_game.bullets),
        "ship_x": _game.ship.rect.x,
        "fleet_direction": _game.settings.fleet_direction,
        "alien_speed": round(_game.settings.alien_speed, 3),
        "alien_points": _game.settings.alien_points,
    }


def _publish_frame(surface: pygame.Surface, scale: float, quality: int) -> None:
    """把当前 surface 编码成 JPEG，放进全局变量供 HTTP 线程读取。"""
    global _latest_frame
    w, h = surface.get_size()
    if scale and scale != 1.0:
        w, h = int(w * scale), int(h * scale)
    # pygame 的 surface → bytes → PIL Image（RGB），比逐像素转换快得多
    raw = pygame.image.tostring(surface, "RGB")
    img = Image.frombytes("RGB", surface.get_size(), raw)
    if (w, h) != surface.get_size():
        img = img.resize((w, h), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    with _frame_lock:
        _latest_frame = buf.getvalue()


def _game_thread(scale: float, quality: int, publish_every: int) -> None:
    """游戏主循环所在线程。"""
    global _game, _frame_count

    def on_frame(game) -> None:
        global _frame_count
        _frame_count += 1
        if _frame_count % publish_every == 0:
            _publish_frame(game.screen, scale, quality)
        for hook in list(_frame_hooks):
            hook(game)

    _game = AlienInvasion(event_source=_build_events, on_frame=on_frame)
    try:
        _game.run_game()
    except Exception as exc:  # pragma: no cover - 出错也要让服务器知道
        print(f"[game] 出错: {exc!r}", flush=True)
    finally:
        _stop.set()
        print("[game] 主循环结束", flush=True)


# --------------------------------------------------------------------- HTTP 服务
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AlienInvasionPreview/1.0"

    def log_message(self, fmt, *args):  # 静音访问日志，保留错误
        pass

    # GET /  → 页面
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/stream":
            self._stream()
        elif path == "/frame.jpg":
            self._one_frame()
        elif path == "/healthz":
            self._json({"ok": True, "frames": _frame_count, "running": not _stop.is_set()})
        elif path == "/state":
            # 调试用：返回游戏内部状态（可以用 curl 检查按键是否真的生效）
            self._json(_game_state())
        else:
            self.send_error(404)

    # POST /input → 注入事件
    def do_POST(self):
        if self.path.split("?")[0] != "/input":
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
        self._json({"ok": True})

    def _json(self, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _one_frame(self):
        jpeg = self._wait_for_frame(1.0)
        if jpeg is None:
            self.send_error(503, "no frame yet")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(jpeg)

    def _wait_for_frame(self, timeout: float):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with _frame_lock:
                if _latest_frame is not None:
                    return _latest_frame
            time.sleep(0.02)
        return None

    def _stream(self):
        """MJPEG：一条永不结束的 multipart 响应，浏览器 <img> 直接就能放。"""
        boundary = "alienframe"
        self.send_response(200)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary}")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        last = None
        try:
            while not _stop.is_set():
                with _frame_lock:
                    jpeg = _latest_frame
                if jpeg is not None and jpeg is not last:
                    last = jpeg
                    self.wfile.write(f"--{boundary}\r\n".encode())
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                time.sleep(0.01)
        except (BrokenPipeError, ConnectionResetError):
            pass  # 浏览器关掉页面了，正常现象


def main() -> None:
    parser = argparse.ArgumentParser(description="浏览器实时预览《外星人入侵》")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（0.0.0.0 才能被预览代理访问）")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--fps", type=int, default=30, help="推流帧率（游戏内部仍按 settings.fps 跑）")
    parser.add_argument("--scale", type=float, default=0.6, help="推流缩放比例")
    parser.add_argument("--quality", type=int, default=70, help="JPEG 质量")
    args = parser.parse_args()

    publish_every = max(1, round(60 / max(1, args.fps)))  # 游戏 60fps → 每 N 帧推一张
    threading.Thread(
        target=_game_thread, args=(args.scale, args.quality, publish_every), daemon=True
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
