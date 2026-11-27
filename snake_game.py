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
  body { margin: 0; min-height: 100vh; display: flex; flex-direction: column;
         align-items: center; justify-content: center; gap: 12px;
         background: #1b1f24; color: #e6e6e6; font-family: system-ui, sans-serif; }
  h1 { margin: 0; font-size: 28px; letter-spacing: 2px; }
  #info { display: flex; gap: 24px; font-size: 18px; }
  canvas { background: #0f1317; border: 3px solid #3a4250; border-radius: 6px; }
  #msg { font-size: 15px; color: #9aa4b2; height: 20px; }
  #pad { display: none; gap: 6px; flex-direction: column; align-items: center; }
  #pad button { width: 56px; height: 56px; font-size: 22px; border-radius: 10px;
                border: none; background: #3a4250; color: #fff; }
  @media (pointer: coarse) { #pad { display: flex; } }
</style>
</head>
<body>
  <h1>🐍 SNAKE</h1>
  <div id="info"><span>Score: <b id="score">0</b></span><span>Best: <b id="best">0</b></span></div>
  <canvas id="board" width="400" height="400"></canvas>
  <div id="msg">Press an arrow key (or WASD) to start · Space to pause</div>
  <div id="pad">
    <button data-d="up">▲</button>
    <div style="display:flex;gap:6px">
      <button data-d="left">◀</button><button data-d="down">▼</button><button data-d="right">▶</button>
    </div>
  </div>
<script>
const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");
const CELL = 20, GRID = canvas.width / CELL;
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

function setDir(d) {
  if (over) { reset(); }
  const [dx, dy] = DIRS[d], [cx, cy] = DIRS[dir];
  if (dx === -cx && dy === -cy) return;          // no reversing into yourself
  nextDir = d;
  if (!running) { running = true; msg(""); loop(); }
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
    document.getElementById("score").textContent = score;
    speed = Math.max(55, speed - 3);              // gets faster as you grow
    placeFood();
  } else {
    snake.pop();
  }
}

function gameOver() {
  running = false; over = true;
  if (score > best) {
    best = score;
    document.getElementById("best").textContent = best;
    try { localStorage.setItem("snakeBest", best); } catch (e) {}
  }
  msg("Game over! Score " + score + " · press any arrow key to play again");
}

function draw() {
  ctx.fillStyle = "#0f1317"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#e5534b";                       // food
  ctx.beginPath();
  ctx.arc(food.x*CELL + CELL/2, food.y*CELL + CELL/2, CELL/2 - 2, 0, Math.PI*2);
  ctx.fill();
  snake.forEach((s, i) => {                        // snake
    ctx.fillStyle = i === 0 ? "#7ee787" : "#3fb950";
    ctx.fillRect(s.x*CELL + 1, s.y*CELL + 1, CELL - 2, CELL - 2);
  });
  if (over) {
    ctx.fillStyle = "rgba(0,0,0,0.55)"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#fff"; ctx.font = "bold 32px system-ui"; ctx.textAlign = "center";
    ctx.fillText("GAME OVER", canvas.width/2, canvas.height/2);
  }
}

function msg(t) { document.getElementById("msg").textContent = t; }

document.addEventListener("keydown", e => {
  if (e.key === " ") {
    e.preventDefault();
    if (!running) return;
    paused = !paused; msg(paused ? "Paused · press Space to resume" : ""); loop();
    return;
  }
  const d = KEYS[e.key];
  if (d) { e.preventDefault(); if (!paused) setDir(d); }
});
document.querySelectorAll("#pad button").forEach(b =>
  b.addEventListener("click", () => setDir(b.dataset.d)));

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
