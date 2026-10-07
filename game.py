import pygame
import time

from barrel import Explosion, spawn_barrels, zombies_in_blast
from zombies import spawn_zombie

WIDTH, HEIGHT = 800, 560
FPS = 60
BG = (30,35,25)

MAX_HP = 3
INVINCIBLE_MS = 1500
CLIP_SIZE = 12
RELOAD_MS = 2000

SPEED = 4


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.color = (60,160,220)
        self.bullets = []
        self.shoot_cooldown = 0
        self.hp = MAX_HP
        self.invincible_ms = 0
        self.ammo = CLIP_SIZE
        self.reload_ms = 0

    @property
    def invincible(self):
        return self.invincible_ms > 0

    @property
    def reloading(self):
        return self.reload_ms > 0

    def take_hit(self):
        """Lose 1 HP unless invincible. Returns True if damage was applied."""
        if self.invincible or self.hp <= 0:
            return False
        self.hp -= 1
        self.invincible_ms = INVINCIBLE_MS
        return True

    def start_reload(self):
        if not self.reloading and self.ammo < CLIP_SIZE:
            self.reload_ms = RELOAD_MS

    def tick_timers(self, dt_ms):
        self.invincible_ms = max(0, self.invincible_ms - dt_ms)
        if self.reload_ms > 0:
            self.reload_ms -= dt_ms
            if self.reload_ms <= 0:
                self.reload_ms = 0
                self.ammo = CLIP_SIZE

    def move(self, keys, width, height):
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = SPEED
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = SPEED
        self.rect.x = max(0, min(width-self.rect.width, self.rect.x+dx))
        self.rect.y = max(0, min(height-self.rect.height, self.rect.y+dy))
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def shoot(self, target_pos):
        if self.shoot_cooldown > 0 or self.reloading: return
        if self.ammo <= 0:
            self.start_reload()
            return
        cx, cy = self.rect.center
        tx, ty = target_pos
        dx, dy = tx-cx, ty-cy
        dist = (dx**2+dy**2)**0.5
        if dist == 0: return
        vx, vy = dx/dist*10, dy/dist*10
        self.bullets.append([cx-4, cy-4, vx, vy])
        self.shoot_cooldown = 15
        self.ammo -= 1
        if self.ammo == 0:
            self.start_reload()

    def update_bullets(self, width, height):
        live = []
        for b in self.bullets:
            b[0] += b[2]; b[1] += b[3]
            if 0 <= b[0] <= width and 0 <= b[1] <= height:
                live.append(b)
        self.bullets = live

    def draw(self, screen):
        # Blink while invincible
        if not (self.invincible and (self.invincible_ms // 100) % 2 == 0):
            pygame.draw.rect(screen, self.color, self.rect, border_radius=6)
        for b in self.bullets:
            pygame.draw.circle(screen, (255,220,60), (int(b[0]), int(b[1])), 5)


class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Zombie Escape")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.hud_font = pygame.font.SysFont("monospace", 20)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.reset()

    def reset(self):
        self.player = Player(WIDTH//2, HEIGHT//2)
        self.zombies = [spawn_zombie(WIDTH, HEIGHT, self.player.rect, wave=1) for _ in range(4)]
        self.barrels = spawn_barrels(WIDTH, HEIGHT, self.player.rect)
        self.explosions = []
        self.score = 0
        self.wave = 1
        self.kills = 0
        self.kills_to_next = 8
        self.game_over = False
        self.start_time = time.time()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.reset()
            if event.type == pygame.MOUSEBUTTONDOWN and not self.game_over:
                self.player.shoot(event.pos)
        return True

    def register_kill(self, zombie):
        if zombie in self.zombies:
            self.zombies.remove(zombie)
            self.kills += 1
            self.score += 10

    def explode(self, barrel):
        self.barrels.remove(barrel)
        self.explosions.append(Explosion(barrel.rect.center))
        for z in zombies_in_blast(self.zombies, barrel.rect.center):
            self.register_kill(z)

    def update(self, dt_ms=1000 // FPS):
        if self.game_over: return
        keys = pygame.key.get_pressed()
        self.player.move(keys, WIDTH, HEIGHT)
        self.player.tick_timers(dt_ms)
        self.player.update_bullets(WIDTH, HEIGHT)
        self.score = int(time.time() - self.start_time)
        for e in self.explosions:
            e.update(dt_ms)
        self.explosions = [e for e in self.explosions if not e.done]

        for z in self.zombies:
            z.update(self.player.rect.center)
            if z.rect.colliderect(self.player.rect):
                self.player.take_hit()
        if self.player.hp <= 0:
            self.game_over = True

        for b in self.player.bullets[:]:
            bx, by = int(b[0]), int(b[1])
            barrel = next((br for br in self.barrels if br.rect.collidepoint(bx, by)), None)
            if barrel:
                self.explode(barrel)
                self.player.bullets.remove(b)
                continue
            zombie = next((z for z in self.zombies if z.rect.collidepoint(bx, by)), None)
            if zombie:
                if zombie.hit():
                    self.register_kill(zombie)
                self.player.bullets.remove(b)

        if self.kills >= self.kills_to_next:
            self.kills = 0
            self.wave += 1
            self.kills_to_next = 8 + self.wave * 2
            for _ in range(self.wave + 3):
                self.zombies.append(spawn_zombie(WIDTH, HEIGHT, self.player.rect, wave=self.wave))

    def hud_text(self):
        p = self.player
        ammo = f"RELOAD {p.reload_ms/1000:.1f}s" if p.reloading else f"{p.ammo}/{CLIP_SIZE}"
        return f"HP: {p.hp}/{MAX_HP}  Ammo: {ammo}  Wave: {self.wave}  Score: {self.score}  Kills: {self.kills}/{self.kills_to_next}"

    def draw(self):
        self.screen.fill(BG)
        for x in range(0, WIDTH, 60):
            pygame.draw.line(self.screen, (40,45,35), (x,0), (x,HEIGHT), 1)
        for y in range(0, HEIGHT, 60):
            pygame.draw.line(self.screen, (40,45,35), (0,y), (WIDTH,y), 1)
        for b in self.barrels: b.draw(self.screen)
        for z in self.zombies: z.draw(self.screen)
        self.player.draw(self.screen)
        for e in self.explosions: e.draw(self.screen)
        hud_bg = pygame.Rect(0, 0, WIDTH, 40)
        pygame.draw.rect(self.screen, (15,20,15), hud_bg)
        hud = self.hud_font.render(self.hud_text(), True, (160,220,120))
        self.screen.blit(hud, (8, 8))
        if self.game_over:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0,0,0,160))
            self.screen.blit(ov, (0,0))
            m = self.big_font.render("DEVOURED!", True, (180,40,40))
            s = self.font.render(f"Wave {self.wave} | Score {self.score} | Press R", True, (200,200,200))
            self.screen.blit(m, (WIDTH//2-m.get_width()//2, HEIGHT//2-40))
            self.screen.blit(s, (WIDTH//2-s.get_width()//2, HEIGHT//2+20))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            dt_ms = self.clock.tick(FPS)
            self.update(dt_ms)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
