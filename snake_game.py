#!/usr/bin/env python3
"""
Snake game in the browser.

Run:  python3 snake_game.py
Then the game opens at http://localhost:8000 (stop with Ctrl+C).
Uses only Python's standard library - nothing to install.
"""

import http.server
import socketserver
import sys
import threading
import webbrowser

PORT = 8000

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Snake</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body { height: 100%; }
  body { margin: 0; height: 100vh; height: 100dvh; overflow: hidden;
         box-sizing: border-box; padding: 12px; display: flex; flex-direction: column;
         align-items: center; justify-content: center; gap: 12px;
         background: #1b1f24; color: #e6e6e6; font-family: system-ui, sans-serif; }
  h1 { margin: 0; font-size: 28px; letter-spacing: 2px; }
  #info { display: flex; gap: 24px; font-size: 18px; align-items: center; }
  #sound { background: #3a4250; border: none; border-radius: 6px; font-size: 16px;
           padding: 4px 10px; cursor: pointer; }
  canvas { background: #0f1317; border: 3px solid #3a4250; border-radius: 6px;
           display: block; touch-action: none; }
  #msg { font-size: 15px; color: #9aa4b2; min-height: 20px; text-align: center; }
  #pad { display: none; gap: 6px; flex-direction: column; align-items: center; }
  #pad button { width: 56px; height: 56px; font-size: 22px; border-radius: 10px;
                border: none; background: #3a4250; color: #fff; }
  @media (pointer: coarse) { #pad { display: flex; } }
  @media (max-height: 520px) {            /* short screens, e.g. phone in landscape */
    h1 { font-size: 20px; }
    #info { font-size: 15px; }
    #msg { font-size: 13px; }
    #pad button { width: 44px; height: 44px; font-size: 18px; }
  }
  /* phone held sideways: drop the title and move the arrow pad beside the board */
  @media (pointer: coarse) and (orientation: landscape) {
    h1 { display: none; }
    #pad { position: fixed; right: 16px; bottom: 16px; }
  }
</style>
</head>
<body>
  <h1>🐍 SNAKE</h1>
  <div id="info"><span>Score: <b id="score">0</b></span><span>Best: <b id="best">0</b></span>
       <button id="sound" title="Sound on/off (M)">🔊</button></div>
  <canvas id="board"></canvas>
  <div id="msg">Press an arrow key (or WASD) to start · Space to pause · M to mute</div>
  <div id="pad">
    <button data-d="up">▲</button>
    <div style="display:flex;gap:6px">
      <button data-d="left">◀</button><button data-d="down">▼</button><button data-d="right">▶</button>
    </div>
  </div>
<script>
const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");
const GRID = 20;                 // board is always 20 x 20 squares
let CELL = 20, BOARD = 400;      // square size / board size in CSS pixels (set by fitBoard)

// ---------- Fit the board to the screen ----------
function fitBoard() {
  const body = document.body, cs = getComputedStyle(body);
  const gap = parseFloat(cs.rowGap) || 0;
  const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const border = 6;                                   // 3px border on each side
  // height used by everything except the board
  let used = 0, visible = 0;
  for (const el of body.children) {
    if (el === canvas || el.tagName === "SCRIPT") continue;
    const st = getComputedStyle(el);
    if (st.display === "none" || st.position === "fixed") continue;
    used += el.getBoundingClientRect().height; visible++;
  }
  used += gap * visible;                              // gaps between items and the board
  const availH = window.innerHeight - padY - used - border;
  const availW = window.innerWidth - padX - border;
  // largest size that fits, rounded down to whole squares so the grid stays crisp
  CELL = Math.max(8, Math.floor(Math.min(availW, availH, 1000) / GRID));
  BOARD = CELL * GRID;
  const dpr = window.devicePixelRatio || 1;           // sharp on Retina screens
  canvas.style.width = canvas.style.height = BOARD + "px";
  canvas.width = canvas.height = Math.round(BOARD * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (snake) draw();
}
let resizeTimer;
window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(fitBoard, 80); });
window.addEventListener("orientationchange", () => setTimeout(fitBoard, 200));
// ---------------------------------------------------
const DIRS = { up: [0,-1], down: [0,1], left: [-1,0], right: [1,0] };
const KEYS = { ArrowUp:"up", ArrowDown:"down", ArrowLeft:"left", ArrowRight:"right",
               w:"up", s:"down", a:"left", d:"right", W:"up", S:"down", A:"left", D:"right" };
let snake, dir, nextDir, food, score, speed, timer, running, paused, over;
let best = 0;
try { best = +localStorage.getItem("snakeBest") || 0; } catch (e) {}
document.getElementById("best").textContent = best;

function reset() {
  snake = [{x:10,y:10},{x:9,y:10},{x:8,y:10}];
  dir = "right"; nextDir = "right";
  score = 0; speed = 130; running = false; paused = false; over = false;
  document.getElementById("score").textContent = 0;
  placeFood(); draw();
}

function placeFood() {
  do { food = { x: Math.floor(Math.random()*GRID), y: Math.floor(Math.random()*GRID) }; }
  while (snake.some(s => s.x === food.x && s.y === food.y));
}

// ---------- Sounds (generated by the browser, no audio files needed) ----------
let audioCtx = null, muted = false;
try { muted = localStorage.getItem("snakeMuted") === "1"; } catch (e) {}

function tone(freq, start, dur, type = "square", vol = 0.08, endFreq = null) {
  if (muted) return;
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  const t = audioCtx.currentTime + start;
  const osc = audioCtx.createOscillator(), gain = audioCtx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);
  if (endFreq) osc.frequency.exponentialRampToValueAtTime(endFreq, t + dur);
  gain.gain.setValueAtTime(vol, t);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  osc.connect(gain).connect(audioCtx.destination);
  osc.start(t); osc.stop(t + dur + 0.02);
}

const sfx = {
  start()  { tone(440, 0, 0.08); tone(660, 0.08, 0.08); tone(880, 0.16, 0.12); },
  turn()   { tone(220, 0, 0.03, "triangle", 0.04); },
  eat()    { tone(600, 0, 0.09, "square", 0.08, 1200); },
  best()   { [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.09, 0.12, "triangle", 0.09)); },
  over()   { tone(400, 0, 0.5, "sawtooth", 0.08, 70); tone(200, 0.15, 0.45, "square", 0.05, 50); },
  pause()  { tone(330, 0, 0.07, "triangle", 0.06); },
};

function updateSoundBtn() { document.getElementById("sound").textContent = muted ? "🔇" : "🔊"; }
function toggleSound() {
  muted = !muted;
  try { localStorage.setItem("snakeMuted", muted ? "1" : "0"); } catch (e) {}
  updateSoundBtn();
  if (!muted) tone(660, 0, 0.08, "triangle", 0.06);
}
document.getElementById("sound").addEventListener("click", e => { toggleSound(); e.currentTarget.blur(); });
updateSoundBtn();
// ------------------------------------------------------------------------------

function setDir(d) {
  if (over) { reset(); }
  const [dx, dy] = DIRS[d], [cx, cy] = DIRS[dir];
  if (dx === -cx && dy === -cy) return;          // no reversing into yourself
  if (running && d !== nextDir) sfx.turn();
  nextDir = d;
  if (!running) { running = true; msg(""); sfx.start(); loop(); }
}

function loop() {
  clearTimeout(timer);
  if (!running || paused) return;
  step(); draw();
  if (running) timer = setTimeout(loop, speed);
}

function step() {
  dir = nextDir;
  const [dx, dy] = DIRS[dir];
  const head = { x: snake[0].x + dx, y: snake[0].y + dy };
  const hitWall = head.x < 0 || head.y < 0 || head.x >= GRID || head.y >= GRID;
  const hitSelf = snake.slice(0, -1).some(s => s.x === head.x && s.y === head.y);
  if (hitWall || hitSelf) { gameOver(); return; }
  snake.unshift(head);
  if (head.x === food.x && head.y === food.y) {
    score++;
    sfx.eat();
    document.getElementById("score").textContent = score;
    speed = Math.max(55, speed - 3);              // gets faster as you grow
    placeFood();
  } else {
    snake.pop();
  }
}

function gameOver() {
  running = false; over = true;
  const newBest = score > best && score > 0;
  if (newBest) { sfx.over(); setTimeout(sfx.best, 550); } else { sfx.over(); }
  if (score > best) {
    best = score;
    document.getElementById("best").textContent = best;
    try { localStorage.setItem("snakeBest", best); } catch (e) {}
  }
  msg("Game over! Score " + score + " · press any arrow key to play again");
}

function draw() {
  ctx.fillStyle = "#0f1317"; ctx.fillRect(0, 0, BOARD, BOARD);
  ctx.fillStyle = "#e5534b";                       // food
  ctx.beginPath();
  ctx.arc(food.x*CELL + CELL/2, food.y*CELL + CELL/2, CELL/2 - 2, 0, Math.PI*2);
  ctx.fill();
  snake.forEach((s, i) => {                        // snake
    ctx.fillStyle = i === 0 ? "#7ee787" : "#3fb950";
    ctx.fillRect(s.x*CELL + 1, s.y*CELL + 1, CELL - 2, CELL - 2);
  });
  if (over) {
    ctx.fillStyle = "rgba(0,0,0,0.55)"; ctx.fillRect(0, 0, BOARD, BOARD);
    ctx.fillStyle = "#fff"; ctx.font = "bold " + Math.round(BOARD / 12) + "px system-ui";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("GAME OVER", BOARD/2, BOARD/2);
  }
}

function msg(t) { document.getElementById("msg").textContent = t; }

document.addEventListener("keydown", e => {
  if (e.key === " ") {
    e.preventDefault();
    if (!running) return;
    paused = !paused; sfx.pause(); msg(paused ? "Paused · press Space to resume" : ""); loop();
    return;
  }
  if (e.key === "m" || e.key === "M") { toggleSound(); return; }
  const d = KEYS[e.key];
  if (d) { e.preventDefault(); if (!paused) setDir(d); }
});
document.querySelectorAll("#pad button").forEach(b =>
  b.addEventListener("click", () => setDir(b.dataset.d)));

// Swipe on the board to steer (phones / tablets)
let touchStart = null;
canvas.addEventListener("touchstart", e => {
  const t = e.changedTouches[0]; touchStart = { x: t.clientX, y: t.clientY };
}, { passive: true });
canvas.addEventListener("touchend", e => {
  if (!touchStart) return;
  const t = e.changedTouches[0];
  const dx = t.clientX - touchStart.x, dy = t.clientY - touchStart.y;
  touchStart = null;
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 20) return;   // ignore taps
  setDir(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
}, { passive: true });

fitBoard();
reset();
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the terminal quiet
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    socketserver.TCPServer.allow_reuse_address = True
    try:
        server = socketserver.TCPServer(("127.0.0.1", port), Handler)
    except OSError:
        print(f"Port {port} is busy. Try: python3 snake_game.py 8001")
        sys.exit(1)

    url = f"http://localhost:{port}"
    print(f"🐍 Snake is running at {url}")
    print("Press Ctrl+C here to stop.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
