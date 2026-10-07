import random

import pygame

BARREL_COUNT = 4
BARREL_SIZE = 26
EXPLOSION_RADIUS = 110
EXPLOSION_MS = 400
HUD_HEIGHT = 40


class Barrel:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, BARREL_SIZE, BARREL_SIZE)

    def draw(self, screen):
        pygame.draw.rect(screen, (170, 60, 30), self.rect, border_radius=4)
        pygame.draw.rect(screen, (230, 170, 40), self.rect, width=3, border_radius=4)
        pygame.draw.line(screen, (230, 170, 40), self.rect.midleft, self.rect.midright, 2)


class Explosion:
    """Short-lived visual effect; damage is applied once by `explode`."""

    def __init__(self, center, radius=EXPLOSION_RADIUS, duration_ms=EXPLOSION_MS):
        self.center = center
        self.radius = radius
        self.duration_ms = duration_ms
        self.age_ms = 0

    @property
    def done(self):
        return self.age_ms >= self.duration_ms

    def update(self, dt_ms):
        self.age_ms += dt_ms

    def draw(self, screen):
        t = min(1.0, self.age_ms / self.duration_ms)
        pygame.draw.circle(screen, (255, 140, 30), self.center, int(self.radius * t), 6)
        pygame.draw.circle(screen, (255, 230, 120), self.center, int(self.radius * 0.5 * (1 - t)) + 2)


def spawn_barrels(width, height, avoid_rect, count=BARREL_COUNT, rng=random):
    """Random non-overlapping barrels, clear of the player and the HUD bar."""
    barrels = []
    while len(barrels) < count:
        x = rng.randint(20, width - BARREL_SIZE - 20)
        y = rng.randint(HUD_HEIGHT + 20, height - BARREL_SIZE - 20)
        rect = pygame.Rect(x, y, BARREL_SIZE, BARREL_SIZE)
        if rect.colliderect(avoid_rect.inflate(160, 160)):
            continue
        if any(rect.colliderect(b.rect.inflate(40, 40)) for b in barrels):
            continue
        barrels.append(Barrel(x, y))
    return barrels


def zombies_in_blast(zombies, center, radius=EXPLOSION_RADIUS):
    cx, cy = center
    r2 = radius * radius
    return [z for z in zombies
            if (z.rect.centerx - cx) ** 2 + (z.rect.centery - cy) ** 2 <= r2]
