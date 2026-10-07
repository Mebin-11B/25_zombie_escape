import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import game
from barrel import EXPLOSION_RADIUS, Barrel
from game import CLIP_SIZE, INVINCIBLE_MS, MAX_HP, RELOAD_MS, GameEngine
from zombies import FastZombie, TankZombie, Zombie, pick_zombie_class, spawn_zombie

FRAME = 16


@pytest.fixture
def eng():
    e = GameEngine()
    e.zombies = []
    e.barrels = []
    yield e
    pygame.quit()


def place_on_player(eng, cls=Zombie):
    z = cls(0, 0)
    z.rect.center = eng.player.rect.center
    z.x, z.y = z.rect.x, z.rect.y
    eng.zombies.append(z)
    return z


def fire_at(eng, x, y):
    eng.player.shoot((x, y))


# ---- Task 1: health ----
def test_starts_with_full_hp_and_hud_shows_it(eng):
    assert eng.player.hp == MAX_HP == 3
    assert "HP: 3/3" in eng.hud_text()


def test_touch_costs_one_hp_then_invincible(eng):
    place_on_player(eng)
    eng.update(FRAME)
    assert eng.player.hp == 2 and eng.player.invincible and not eng.game_over
    for _ in range(10):  # still overlapping, no further damage
        eng.update(FRAME)
    assert eng.player.hp == 2


def test_invincibility_expires_then_next_hit_lands(eng):
    z = place_on_player(eng)
    eng.update(FRAME)
    eng.update(INVINCIBLE_MS - 2 * FRAME)
    assert eng.player.invincible and eng.player.hp == 2  # window still open
    eng.zombies.remove(z)  # step away so expiry is observable
    eng.update(2 * FRAME)
    assert not eng.player.invincible and eng.player.hp == 2
    eng.zombies.append(z)
    eng.update(FRAME)
    assert eng.player.hp == 1 and not eng.game_over


def test_game_over_only_at_zero_hp(eng):
    place_on_player(eng)
    for expected_hp in (2, 1):
        eng.update(FRAME)
        assert eng.player.hp == expected_hp and not eng.game_over
        eng.update(INVINCIBLE_MS)
    eng.update(FRAME)
    assert eng.player.hp == 0 and eng.game_over


# ---- Task 2: ammo ----
def test_clip_depletes_and_triggers_reload(eng):
    p = eng.player
    for _ in range(CLIP_SIZE):
        p.shoot((700, 100))
        p.shoot_cooldown = 0
    assert p.ammo == 0 and p.reloading and len(p.bullets) == CLIP_SIZE


def test_cannot_shoot_while_reloading_and_ammo_restored_after_full_2s(eng):
    p = eng.player
    p.ammo = 0
    p.start_reload()
    p.shoot((700, 100))
    assert len(p.bullets) == 0
    p.tick_timers(RELOAD_MS - 1)
    assert p.reloading and p.ammo == 0
    p.shoot((700, 100))
    assert len(p.bullets) == 0
    p.tick_timers(1)
    assert not p.reloading and p.ammo == CLIP_SIZE
    p.shoot((700, 100))
    assert len(p.bullets) == 1 and p.ammo == CLIP_SIZE - 1


def test_hud_shows_ammo_and_reload_countdown(eng):
    assert f"Ammo: {CLIP_SIZE}/{CLIP_SIZE}" in eng.hud_text()
    eng.player.ammo = 0
    eng.player.start_reload()
    assert "RELOAD 2.0s" in eng.hud_text()
    eng.player.tick_timers(500)
    assert "RELOAD 1.5s" in eng.hud_text()


def test_no_reload_when_clip_full(eng):
    eng.player.start_reload()
    assert not eng.player.reloading


# ---- Task 3: barrels ----
def test_reset_places_four_barrels_not_on_player():
    e = GameEngine()
    assert len(e.barrels) == 4
    assert all(not b.rect.colliderect(e.player.rect) for b in e.barrels)
    pygame.quit()


def test_barrel_explosion_kills_nearby_only_and_removes_barrel(eng):
    b = Barrel(100, 200)
    eng.barrels = [b]
    near = Zombie(*b.rect.center); near.rect.center = (b.rect.centerx + 50, b.rect.centery)
    far = Zombie(0, 0); far.rect.center = (b.rect.centerx + EXPLOSION_RADIUS + 40, b.rect.centery)
    eng.zombies = [near, far]
    eng.player.rect.center = (700, 500)
    eng.player.bullets = [[b.rect.centerx, b.rect.centery, 0, 0]]
    eng.update(FRAME)
    assert eng.barrels == [] and eng.zombies == [far]
    assert eng.explosions and eng.kills == 1
    assert eng.player.bullets == []


def test_bullet_in_flight_hits_barrel(eng):
    eng.player.rect.center = (100, 300)
    eng.barrels = [Barrel(300, 285)]
    fire_at(eng, 400, 300)
    for _ in range(40):
        eng.update(FRAME)
    assert eng.barrels == []


def test_explosion_effect_expires(eng):
    eng.barrels = [Barrel(300, 285)]
    eng.player.bullets = [[310, 295, 0, 0]]
    eng.update(FRAME)
    assert len(eng.explosions) == 1
    eng.update(1000)
    assert eng.explosions == []


# ---- Task 4: zombie types ----
def test_type_stats():
    assert (FastZombie.HP, TankZombie.HP, Zombie.HP) == (1, 6, 3)
    assert FastZombie.SPEED > Zombie.SPEED > TankZombie.SPEED
    assert FastZombie.SIZE < Zombie.SIZE < TankZombie.SIZE


def test_fast_dies_in_one_hit_tank_needs_six():
    f, t = FastZombie(0, 0), TankZombie(0, 0)
    assert f.hit()
    assert [t.hit() for _ in range(6)] == [False] * 5 + [True]


def test_bullet_combat_tank_survives_five_hits(eng):
    eng.player.rect.center = (700, 500)
    t = TankZombie(300, 300); eng.zombies = [t]
    for _ in range(5):
        eng.player.bullets = [[t.rect.centerx, t.rect.centery, 0, 0]]
        eng.update(FRAME)
        t.rect.center = (300, 300); t.x, t.y = t.rect.x, t.rect.y
    assert t in eng.zombies and t.hp == 1


def test_movement_speed_ordering():
    target = (1000, 1000)
    dist = {}
    for cls in (Zombie, FastZombie, TankZombie):
        z = cls(0, 0)
        for _ in range(100):
            z.update(target)
        dist[cls] = z.x + z.y
    assert dist[FastZombie] > dist[Zombie] > dist[TankZombie] > 0


def test_no_tanks_wave1_all_types_later():
    import random
    rng = random.Random(1)
    assert TankZombie not in {pick_zombie_class(1, rng) for _ in range(300)}
    assert {pick_zombie_class(3, rng) for _ in range(300)} == {Zombie, FastZombie, TankZombie}


def test_spawn_respects_bounds_and_player_margin():
    p = pygame.Rect(400, 280, 32, 32)
    for cls in (Zombie, FastZombie, TankZombie):
        for _ in range(50):
            z = spawn_zombie(800, 560, p, cls=cls)
            assert isinstance(z, cls)
            assert pygame.Rect(0, 0, 800, 560).contains(z.rect)
            assert not z.rect.colliderect(p.inflate(120, 120))


def test_wave_progression_spawns_mixed_types(eng):
    eng.kills = eng.kills_to_next
    eng.player.rect.center = (400, 280)
    eng.update(FRAME)
    assert eng.wave == 2 and eng.kills == 0 and eng.kills_to_next == 12
    assert len(eng.zombies) == 5


# ---- restart ----
def test_restart_after_game_over_resets_everything(eng):
    place_on_player(eng)
    for _ in range(3):
        eng.update(FRAME)
        eng.update(INVINCIBLE_MS)
    eng.update(FRAME)
    assert eng.game_over
    eng.player.ammo = 0; eng.player.start_reload()
    eng.wave, eng.kills = 5, 3
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    assert eng.handle_events()
    p = eng.player
    assert not eng.game_over and p.hp == MAX_HP and not p.invincible
    assert p.ammo == CLIP_SIZE and not p.reloading and p.bullets == []
    assert eng.wave == 1 and eng.kills == 0 and len(eng.zombies) == 4
    assert len(eng.barrels) == 4 and eng.explosions == []


def test_draw_smoke_all_states(eng):
    eng.zombies = [Zombie(50, 50), FastZombie(90, 90), TankZombie(150, 150)]
    eng.barrels = [Barrel(300, 300)]
    eng.player.take_hit()
    eng.player.start_reload()
    eng.explosions = [game.Explosion((200, 200))]
    eng.draw()
    eng.game_over = True
    eng.draw()
