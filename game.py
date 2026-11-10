import math
import random
import time
import tkinter as tk

# =====================================================================
# WARNA: tema baru "Synthwave" (ungu gelap, pink, cyan, oranye)
# =====================================================================
THEME = {
    'bg':      '#1a0b2e',   # latar utama (ungu tua)
    'grid':    '#2b1550',   # garis kisi latar
    'bar':     '#26104a',   # panel HUD
    'text':    '#f1e9ff',   # teks utama
    'muted':   '#a78bd0',   # teks petunjuk
    'accent':  '#ffd166',   # teks pesan utama
    'shadow':  '#0b0416',   # bayangan teks
    'ball':    '#fff3b0',   # bola (krem terang)
    'ball_edge': '#ffffff',
    'paddle':  '#4cc9f0',   # paddle (cyan)
    'paddle_edge': '#caf0f8',
    'brick3':  '#9d4edd',   # brick 3 pukulan (ungu)
    'brick2':  '#ff4d9d',   # brick 2 pukulan (pink)
    'brick1':  '#ffb703',   # brick 1 pukulan (oranye)
    'ok':      '#4ade80',
    'warn':    '#ffb703',
    'bad':     '#ff4d9d',
    'info':    '#4cc9f0',
}

FONT = 'Courier'


class GameObject(object):
    def __init__(self, canvas, item):
        self.canvas = canvas
        self.item = item

    def get_position(self):
        return self.canvas.coords(self.item)

    def move(self, x, y):
        self.canvas.move(self.item, x, y)

    def delete(self):
        self.canvas.delete(self.item)


class Ball(GameObject):
    def __init__(self, canvas, x, y, speed):
        self.radius = 10
        self.speed = speed          # KECEPATAN: sekarang dalam piksel per DETIK
        self.dx = 0
        self.dy = 0
        self.last_hit = set()
        item = canvas.create_oval(x - self.radius, y - self.radius,
                                  x + self.radius, y + self.radius,
                                  fill=THEME['ball'],
                                  outline=THEME['ball_edge'], width=2)
        super(Ball, self).__init__(canvas, item)
        self.set_velocity(random.choice([-0.4, 0.4]))

    def set_velocity(self, dx_ratio):
        self.dx = self.speed * dx_ratio
        self.dy = -math.sqrt(self.speed ** 2 - self.dx ** 2)

    def update(self, dt):
        """HALUS: bola bergerak sejauh (kecepatan x waktu yang benar-benar
        berlalu), jadi tidak patah-patah walau timer Tkinter tidak presisi."""
        coords = self.get_position()
        width = self.canvas.winfo_width()
        if coords[0] <= 0:
            self.dx = abs(self.dx)
        elif coords[2] >= width:
            self.dx = -abs(self.dx)
        if coords[1] <= 0:
            self.dy = abs(self.dy)
        self.move(self.dx * dt, self.dy * dt)

    def collide(self, game_objects):
        points = 0
        coords = self.get_position()
        ball_x = (coords[0] + coords[2]) / 2
        ball_y = (coords[1] + coords[3]) / 2

        paddle = None
        bricks = []
        for obj in game_objects:
            if isinstance(obj, Paddle):
                paddle = obj
            elif isinstance(obj, Brick):
                bricks.append(obj)

        if paddle is not None:
            pc = paddle.get_position()
            center = (pc[0] + pc[2]) / 2
            half = (pc[2] - pc[0]) / 2
            offset = max(-1.0, min(1.0, (ball_x - center) / half))
            self.set_velocity(offset * 0.8)

        if bricks:
            bc = bricks[0].get_position()
            if len(bricks) == 1 and ball_x > bc[2]:
                self.dx = abs(self.dx)
            elif len(bricks) == 1 and ball_x < bc[0]:
                self.dx = -abs(self.dx)
            else:
                centers = []
                for b in bricks:
                    p = b.get_position()
                    centers.append((p[1] + p[3]) / 2)
                brick_y = sum(centers) / len(centers)
                if ball_y < brick_y:
                    self.dy = -abs(self.dy)
                else:
                    self.dy = abs(self.dy)

            fresh = [b for b in bricks if b not in self.last_hit]
            for b in fresh:
                points += b.hit()
        self.last_hit = set(bricks)
        return points


class Paddle(GameObject):
    def __init__(self, canvas, x, y):
        self.width = 80
        self.height = 10
        self.ball = None
        item = canvas.create_rectangle(x - self.width / 2,
                                       y - self.height / 2,
                                       x + self.width / 2,
                                       y + self.height / 2,
                                       fill=THEME['paddle'],
                                       outline=THEME['paddle_edge'], width=2)
        super(Paddle, self).__init__(canvas, item)

    def set_ball(self, ball):
        self.ball = ball

    def move(self, offset):
        """HALUS: offset dipotong sesuai sisa ruang, jadi paddle bisa
        menempel tepat di dinding (tidak berhenti beberapa piksel sebelumnya)."""
        coords = self.get_position()
        width = self.canvas.winfo_width()
        offset = max(-coords[0], min(width - coords[2], offset))
        if offset == 0:
            return
        super(Paddle, self).move(offset, 0)
        if self.ball is not None:
            self.ball.move(offset, 0)


class Brick(GameObject):
    COLORS = {1: THEME['brick1'], 2: THEME['brick2'], 3: THEME['brick3']}

    def __init__(self, canvas, x, y, hits):
        self.width = 75
        self.height = 20
        self.hits = hits
        color = Brick.COLORS[hits]
        item = canvas.create_rectangle(x - self.width / 2,
                                       y - self.height / 2,
                                       x + self.width / 2,
                                       y + self.height / 2,
                                       fill=color,
                                       outline=THEME['bg'], width=2,
                                       tags='brick')
        super(Brick, self).__init__(canvas, item)

    def hit(self):
        self.hits -= 1
        if self.hits == 0:
            self.delete()
            return 20
        self.canvas.itemconfig(self.item, fill=Brick.COLORS[self.hits])
        return 10


class Game(tk.Frame):
    FRAME_DELAY = 8       # HALUS: cek tiap ~8 ms (Windows membulatkan ke ~15 ms = ~60 fps)
    START_LIVES = 3
    BASE_SPEED = 520      # KECEPATAN: piksel/detik (v4 = 320) -> sekitar 1,6x lebih cepat
    MAX_SPEED = 900       # KECEPATAN: batas maksimal (v4 = 560)
    SPEED_PER_LEVEL = 60  # KECEPATAN: tambahan per level
    PADDLE_SPEED = 750    # KECEPATAN: piksel/detik saat tombol ditahan
    MAX_STEP = 5          # HALUS: bola dicek tabrakan tiap <= 5 px, jadi tidak tembus

    def __init__(self, master):
        super(Game, self).__init__(master, bg=THEME['bg'])
        self.width = 610
        self.height = 400
        self.high_score = 0
        self.keys = set()                   # HALUS: tombol yang sedang ditahan
        self.last_time = time.perf_counter()
        self.canvas = tk.Canvas(self, bg=THEME['bg'],
                                width=self.width,
                                height=self.height,
                                highlightthickness=0)
        self.canvas.pack()
        self.pack()
        self.canvas.focus_set()

        # HALUS: memantau tombol ditekan/dilepas (bukan mengandalkan key-repeat)
        self.canvas.bind('<KeyPress>', self.on_key_press)
        self.canvas.bind('<KeyRelease>', self.on_key_release)
        self.canvas.bind('<FocusOut>', lambda _: self.keys.clear())

        self.reset_game()
        self.tick()

    # ---------- setup ----------
    def reset_game(self):
        self.canvas.delete('all')
        self.lives = self.START_LIVES
        self.score = 0
        self.level = 1
        self.items = {}
        self.ball = None
        self.state = 'wait'   # wait | ready | running | paused | over

        self.draw_background()
        self.paddle = Paddle(self.canvas, self.width / 2, 326)
        self.items[self.paddle.item] = self.paddle
        self.build_level()
        self.draw_hud()
        self.setup_game()

    def draw_background(self):
        for x in range(0, self.width + 1, 40):
            self.canvas.create_line(x, 0, x, self.height,
                                    fill=THEME['grid'], tags='grid')
        for y in range(0, self.height + 1, 40):
            self.canvas.create_line(0, y, self.width, y,
                                    fill=THEME['grid'], tags='grid')

    def build_level(self):
        rows = min(2 + self.level, 6)
        for row in range(rows):
            y = 50 + row * 22
            if row == 0 and self.level >= 3:
                hits = 3
            elif row < rows // 2:
                hits = 2
            else:
                hits = 1
            for x in range(5, self.width - 5, 75):
                self.add_brick(x + 37.5, y, hits)

    def add_brick(self, x, y, hits):
        brick = Brick(self.canvas, x, y, hits)
        self.items[brick.item] = brick

    def add_ball(self):
        if self.ball is not None:
            self.ball.delete()
        paddle_coords = self.paddle.get_position()
        x = (paddle_coords[0] + paddle_coords[2]) * 0.5
        speed = min(self.BASE_SPEED + (self.level - 1) * self.SPEED_PER_LEVEL,
                    self.MAX_SPEED)
        self.ball = Ball(self.canvas, x, 310, speed)
        self.paddle.set_ball(self.ball)
        self.canvas.tag_raise('hud')

    def setup_game(self):
        self.add_ball()
        self.update_hud()
        self.show_message('Level %d\nTekan Spasi untuk mulai' % self.level)
        self.state = 'ready'

    # ---------- tampilan ----------
    def draw_text(self, x, y, text, size=14, anchor='center', bold=False,
                  color=None, tags=()):
        style = 'bold' if bold else 'normal'
        return self.canvas.create_text(x, y, text=text, anchor=anchor,
                                       font=(FONT, size, style),
                                       fill=color or THEME['text'],
                                       justify='center', tags=tags)

    def show_message(self, text, color=None):
        self.hide_message()
        cx = self.width / 2
        self.draw_text(cx + 2, 232, text, 20, bold=True,
                       color=THEME['shadow'], tags='msg')
        self.draw_text(cx, 230, text, 20, bold=True,
                       color=color or THEME['accent'], tags='msg')

    def hide_message(self):
        self.canvas.delete('msg')

    def draw_hud(self):
        self.canvas.create_rectangle(0, 0, self.width, 34,
                                     fill=THEME['bar'], outline='',
                                     tags='hud')
        self.canvas.create_line(0, 34, self.width, 34,
                                fill=THEME['muted'], tags='hud')
        self.lives_text = self.draw_text(10, 17, '', 12, 'w', True,
                                         THEME['bad'], 'hud')
        self.level_text = self.draw_text(self.width / 2, 17, '', 12,
                                         'center', True, THEME['info'],
                                         'hud')
        self.score_text = self.draw_text(self.width - 10, 17, '', 12, 'e',
                                         True, THEME['ok'], 'hud')
        self.draw_text(self.width / 2, 388,
                       'Tahan Panah / A-D: gerak  |  Spasi: mulai  |  P: pause',
                       9, color=THEME['muted'], tags='hud')

    def update_hud(self):
        self.canvas.itemconfig(self.lives_text,
                               text='HP ' + '♥' * self.lives)
        self.canvas.itemconfig(self.level_text, text='LEVEL %d' % self.level)
        self.canvas.itemconfig(
            self.score_text,
            text='SKOR %d  BEST %d' % (self.score, self.high_score))

    # ---------- input ----------
    def on_key_press(self, event):
        key = event.keysym.lower()
        first_press = key not in self.keys   # abaikan pengulangan otomatis
        self.keys.add(key)
        if not first_press:
            return
        if key == 'space':
            self.on_space()
        elif key == 'p':
            self.toggle_pause()
        elif key == 'r':
            self.on_restart()

    def on_key_release(self, event):
        self.keys.discard(event.keysym.lower())

    def on_space(self):
        if self.state == 'ready':
            self.hide_message()
            self.paddle.set_ball(None)
            self.state = 'running'

    def toggle_pause(self):
        if self.state == 'running':
            self.state = 'paused'
            self.show_message('PAUSE\nTekan P untuk lanjut', THEME['info'])
        elif self.state == 'paused':
            self.hide_message()
            self.state = 'running'

    def on_restart(self):
        if self.state == 'over':
            self.reset_game()

    # ---------- loop utama ----------
    def tick(self):
        """HALUS: satu loop yang selalu berjalan. Mengukur waktu nyata (dt)
        sejak frame sebelumnya lalu menggerakkan paddle dan bola sesuai dt."""
        now = time.perf_counter()
        dt = min(now - self.last_time, 0.05)   # batasi agar tidak 'melompat' saat lag
        self.last_time = now

        if self.state in ('ready', 'running'):
            self.update_paddle(dt)
        if self.state == 'running':
            self.step_game(dt)
        self.after(self.FRAME_DELAY, self.tick)

    def update_paddle(self, dt):
        direction = 0
        if 'left' in self.keys or 'a' in self.keys:
            direction -= 1
        if 'right' in self.keys or 'd' in self.keys:
            direction += 1
        if direction:
            self.paddle.move(direction * self.PADDLE_SPEED * dt)

    def cleared(self):
        return len(self.canvas.find_withtag('brick')) == 0

    def fell(self):
        return self.ball.get_position()[3] >= self.height

    def step_game(self, dt):
        # HALUS: gerakan dipecah jadi langkah kecil (<= MAX_STEP px) dan
        # tabrakan dicek di tiap langkah, jadi bola cepat pun tidak menembus.
        steps = max(1, int(math.ceil(self.ball.speed * dt / self.MAX_STEP)))
        sub_dt = dt / steps
        for _ in range(steps):
            self.check_collisions()
            if self.cleared() or self.fell():
                break
            self.ball.update(sub_dt)

        if self.cleared():
            self.state = 'wait'
            self.show_message('Level %d selesai!' % self.level, THEME['ok'])
            self.after(1500, self.next_level)
        elif self.fell():
            self.lose_life()

    def next_level(self):
        self.level += 1
        self.build_level()
        self.setup_game()

    def lose_life(self):
        self.lives -= 1
        self.update_hud()
        if self.lives <= 0:
            self.game_over()
        else:
            self.state = 'wait'
            self.show_message('Bola jatuh!', THEME['warn'])
            self.after(1000, self.setup_game)

    def game_over(self):
        self.state = 'over'
        self.show_message('GAME OVER\nSkor: %d\nTekan R untuk main lagi'
                          % self.score, THEME['bad'])

    def check_collisions(self):
        ball_coords = self.ball.get_position()
        items = self.canvas.find_overlapping(*ball_coords)
        objects = [self.items[x] for x in items if x in self.items]
        points = self.ball.collide(objects)
        if points:
            self.score += points
            self.high_score = max(self.high_score, self.score)
            self.update_hud()


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Brick Breaker - Synthwave')
    root.configure(bg=THEME['bg'])
    root.resizable(False, False)
    game = Game(root)
    game.mainloop()