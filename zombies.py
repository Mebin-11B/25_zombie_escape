import math
import random

import pygame


class Zombie:
    SPEED = 1.5
    HP = 3
    SIZE = 30
    COLOR = (60, 140, 60)

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, self.SIZE, self.SIZE)
        # Float position: rect coords are ints, so fractional speeds would truncate to 0.
        self.x = float(x)
        self.y = float(y)
        self.color = self.COLOR
        self.hp = self.HP
        self.wobble = random.uniform(0, 6.28)
        self.frame = 0

    def update(self, player_pos):
        px, py = player_pos
        cx, cy = self.rect.center
        dx, dy = px - cx, py - cy
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist:
            self.x += dx / dist * self.SPEED
            self.y += dy / dist * self.SPEED
            self.rect.x = round(self.x)
            self.rect.y = round(self.y)
        self.frame += 1

    def hit(self):
        self.hp -= 1
        return self.hp <= 0

    def draw(self, screen):
        wobble_y = int(math.sin(self.frame * 0.2) * 3)
        draw_rect = self.rect.move(0, wobble_y)
        pygame.draw.rect(screen, self.color, draw_rect, border_radius=5)
        eye_r = max(2, self.SIZE // 8)
        eye_y = draw_rect.y + self.SIZE // 3
        for ex in (draw_rect.x + self.SIZE // 5, draw_rect.x + self.SIZE * 3 // 5):
            pygame.draw.circle(screen, (200, 40, 40), (ex, eye_y), eye_r)


class FastZombie(Zombie):
    SPEED = 2.8
    HP = 1
    SIZE = 20
    COLOR = (200, 190, 50)


class TankZombie(Zombie):
    SPEED = 0.8
    HP = 6
    SIZE = 44
    COLOR = (110, 50, 120)


def pick_zombie_class(wave, rng=random):
    """Weighted mix of zombie types; Tanks only appear from wave 2."""
    classes = [Zombie, FastZombie, TankZombie]
    weights = [5, 3, 2 if wave >= 2 else 0]
    return rng.choices(classes, weights=weights)[0]


def spawn_zombie(width, height, player_rect, wave=1, margin=120, cls=None):
    cls = cls or pick_zombie_class(wave)
    while True:
        x = random.randint(0, width - cls.SIZE)
        y = random.randint(0, height - cls.SIZE)
        rect = pygame.Rect(x, y, cls.SIZE, cls.SIZE)
        if not rect.colliderect(player_rect.inflate(margin, margin)):
            return cls(x, y)
