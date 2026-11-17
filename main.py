import math
import os
import random
import sys

import pygame
import database

from bullet import Bullet
from player import CHARACTER_ARCHETYPES, Player
from zombie import Zombie


# ==================================================
# INITIALISATION
# ==================================================

pygame.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT)
)
pygame.display.set_caption("Zombie Survival")

clock = pygame.time.Clock()


# ==================================================
# COLOURS AND FONTS
# ==================================================

WHITE = (245, 245, 245)
BLACK = (10, 12, 18)
DARK = (18, 24, 36)
PANEL = (29, 38, 55)
BORDER = (65, 78, 100)
RED = (230, 65, 65)
GREEN = (70, 210, 110)
BLUE = (65, 145, 240)
YELLOW = (250, 200, 65)
GREY = (155, 165, 180)
CYAN = (70, 210, 230)
PURPLE = (165, 105, 245)
ORANGE = (245, 145, 55)

font = pygame.font.Font(None, 30)
small_font = pygame.font.Font(None, 23)
tiny_font = pygame.font.Font(None, 19)
title_font = pygame.font.Font(None, 76)
subtitle_font = pygame.font.Font(None, 40)

PAUSE_OVERLAY = pygame.Surface(
    (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
)
PAUSE_OVERLAY.fill((0, 0, 0, 185))


# ==================================================
# ZOMBIE INFORMATION IMAGES
# ==================================================

ZOMBIE_ASSET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets",
    "zombies",
)


def load_zombie_image(filename, size):
    image_path = os.path.join(
        ZOMBIE_ASSET_DIR, filename
    )

    try:
        image = pygame.image.load(
            image_path
        ).convert_alpha()

        return pygame.transform.smoothscale(
            image, (size, size)
        )

    except (pygame.error, FileNotFoundError, OSError):
        print(f"Could not load zombie image: {image_path}")
        return None


normal_image = load_zombie_image("normal.png", 100)
runner_image = load_zombie_image("runner.png", 100)
tank_image = load_zombie_image("tank.png", 120)


# ==================================================
# GAME VARIABLES
# ==================================================

current_screen = "menu"

player = None
player_name = "Player"
selected_character = "Soldier"
selected_difficulty = "Easy"
leaderboard_filter = "All"

name_input_text = "Player"
name_input_active = False

zombies = []
bullets = []
pickups = []
particles = []
floating_texts = []

wave = 1
score = 0
kills = 0
combo_count = 0
combo_expires_at = 0
COMBO_WINDOW_MS = 2600

# Active gameplay time (ms) excludes paused & wave-complete screens
active_play_ms = 0
last_shot_time = -1000
damage_vignette_until = -1

loading_start_time = 0
game_saved = False

# Wave Armory upgrade levels
upgrade_levels = {
    "damage": 0,
    "fire_rate": 0,
    "health": 0,
    "speed": 0,
}


# ==================================================
# UI HELPERS
# ==================================================

def draw_background():
    screen.fill(DARK)

    for x in range(0, SCREEN_WIDTH, 50):
        pygame.draw.line(
            screen, (25, 33, 47),
            (x, 0), (x, SCREEN_HEIGHT)
        )

    for y in range(0, SCREEN_HEIGHT, 50):
        pygame.draw.line(
            screen, (25, 33, 47),
            (0, y), (SCREEN_WIDTH, y)
        )


def draw_button(
    text, x, y, width, height,
    color=BLUE, text_color=WHITE,
    button_font=font, enabled=True
):
    rect = pygame.Rect(x, y, width, height)
    button_color = color if enabled else (45, 52, 66)
    label_color = text_color if enabled else GREY

    if enabled and rect.collidepoint(pygame.mouse.get_pos()):
        button_color = tuple(
            min(channel + 25, 255)
            for channel in color
        )

    pygame.draw.rect(
        screen, button_color, rect,
        border_radius=10
    )
    pygame.draw.rect(
        screen, BORDER, rect, 2,
        border_radius=10
    )

    text_surface = button_font.render(
        text, True, label_color
    )
    screen.blit(
        text_surface,
        text_surface.get_rect(center=rect.center)
    )

    return rect


def draw_centered_text(
    text, y, text_font=font, color=WHITE
):
    surface = text_font.render(text, True, color)

    screen.blit(
        surface,
        surface.get_rect(
            center=(SCREEN_WIDTH // 2, y)
        )
    )


def format_duration(seconds):
    mins, secs = divmod(max(0, int(seconds)), 60)
    if mins > 0:
        return f"{mins}m {secs:02d}s"
    return f"{secs}s"


# ==================================================
# DIFFICULTY & UPGRADE HELPERS
# ==================================================

def get_zombie_damage():
    if selected_difficulty == "Easy":
        return 1
    elif selected_difficulty == "Medium":
        return 3

    return 5


def get_available_zombie_types():
    if selected_difficulty == "Easy":
        return ["Normal"]

    if selected_difficulty == "Medium":
        return ["Normal", "Runner"]

    return ["Normal", "Runner", "Tank"]


def get_upgrade_cost(key):
    base_costs = {
        "damage": 6,
        "fire_rate": 6,
        "health": 5,
        "speed": 6,
    }
    return base_costs[key] + upgrade_levels[key] * 5


def apply_upgrade(key):
    if player is None:
        return False

    cost = get_upgrade_cost(key)
    if player.scrap < cost:
        return False

    player.scrap -= cost
    upgrade_levels[key] += 1

    if key == "damage":
        player.bullet_damage += 5
    elif key == "fire_rate":
        player.shoot_cooldown = max(110, int(player.shoot_cooldown * 0.88))
    elif key == "health":
        player.max_health += 10
        player.health = min(float(player.max_health), player.health + 30)
    elif key == "speed":
        player.speed = round(player.speed + 0.4, 2)

    return True


# ==================================================
# PARTICLES, FLOATING TEXT & PICKUPS
# ==================================================

def spawn_particles(x, y, color, count=8, speed_range=(1.5, 4.5), radius=3):
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(*speed_range)
        particles.append({
            "x": float(x),
            "y": float(y),
            "dx": math.cos(angle) * speed,
            "dy": math.sin(angle) * speed,
            "life": random.randint(14, 26),
            "max_life": 26,
            "color": color,
            "radius": radius,
        })


def add_floating_text(x, y, text, color=WHITE):
    floating_texts.append({
        "x": float(x),
        "y": float(y),
        "text": text,
        "color": color,
        "life": 42,
    })


def maybe_spawn_pickup(x, y, zombie_type, is_elite):
    chance = 0.20
    if zombie_type == "Tank":
        chance = 0.45
    if is_elite:
        chance = 0.85

    if random.random() > chance:
        return

    kind = random.choices(
        ["medkit", "rapid_fire", "spread_shot", "shield"],
        weights=[35, 25, 20, 20],
        k=1,
    )[0]

    pickups.append({
        "x": float(x),
        "y": float(y),
        "kind": kind,
        "radius": 15,
        "expires_at": active_play_ms + 11000,
    })


def apply_pickup(pickup):
    if player is None:
        return

    kind = pickup["kind"]
    px, py = pickup["x"], pickup["y"]

    if kind == "medkit":
        healed = min(20.0, player.max_health - player.health)
        player.health = min(float(player.max_health), player.health + 20.0)
        label = f"+{int(healed)} HP" if healed > 0 else "FULL HP"
        add_floating_text(px, py - 12, label, GREEN)
        spawn_particles(px, py, GREEN, count=10)
    elif kind == "rapid_fire":
        player.rapid_fire_until = active_play_ms + 6500
        add_floating_text(px, py - 12, "RAPID FIRE!", YELLOW)
        spawn_particles(px, py, YELLOW, count=10)
    elif kind == "spread_shot":
        player.spread_shot_until = active_play_ms + 6500
        add_floating_text(px, py - 12, "SPREAD SHOT!", PURPLE)
        spawn_particles(px, py, PURPLE, count=10)
    elif kind == "shield":
        player.shield = min(40, player.shield + 15)
        add_floating_text(px, py - 12, "SHIELD +15", CYAN)
        spawn_particles(px, py, CYAN, count=10)


def update_effects():
    for particle in particles[:]:
        particle["x"] += particle["dx"]
        particle["y"] += particle["dy"]
        particle["dx"] *= 0.93
        particle["dy"] *= 0.93
        particle["life"] -= 1
        if particle["life"] <= 0:
            particles.remove(particle)

    for ft in floating_texts[:]:
        ft["y"] -= 0.7
        ft["life"] -= 1
        if ft["life"] <= 0:
            floating_texts.remove(ft)

    for pickup in pickups[:]:
        if active_play_ms >= pickup["expires_at"]:
            pickups.remove(pickup)


def draw_pickups():
    pickup_styles = {
        "medkit": (GREEN, "+"),
        "rapid_fire": (YELLOW, "R"),
        "spread_shot": (PURPLE, "S"),
        "shield": (CYAN, "A"),
    }

    for pickup in pickups:
        remaining = pickup["expires_at"] - active_play_ms
        # Blink during the final 2.5 seconds before despawn
        if remaining < 2500 and (remaining // 150) % 2 == 0:
            continue

        color, symbol = pickup_styles[pickup["kind"]]
        bob = math.sin(active_play_ms * 0.008) * 3.0
        cx = int(pickup["x"])
        cy = int(pickup["y"] + bob)

        pygame.draw.circle(screen, PANEL, (cx, cy), pickup["radius"])
        pygame.draw.circle(screen, color, (cx, cy), pickup["radius"], 2)

        sym_surf = small_font.render(symbol, True, color)
        screen.blit(sym_surf, sym_surf.get_rect(center=(cx, cy)))


def draw_particles_and_texts():
    for particle in particles:
        pygame.draw.circle(
            screen,
            particle["color"],
            (int(particle["x"]), int(particle["y"])),
            particle["radius"],
        )

    for ft in floating_texts:
        surf = tiny_font.render(ft["text"], True, ft["color"])
        screen.blit(
            surf,
            surf.get_rect(center=(int(ft["x"]), int(ft["y"]))),
        )


def draw_crosshair():
    mx, my = pygame.mouse.get_pos()
    pygame.draw.circle(screen, CYAN, (mx, my), 9, 1)
    pygame.draw.line(screen, WHITE, (mx - 13, my), (mx - 5, my), 2)
    pygame.draw.line(screen, WHITE, (mx + 5, my), (mx + 13, my), 2)
    pygame.draw.line(screen, WHITE, (mx, my - 13), (mx, my - 5), 2)
    pygame.draw.line(screen, WHITE, (mx, my + 5), (mx, my + 13), 2)


# ==================================================
# DATABASE CONNECTION
# ==================================================

def save_current_game():
    """Save a completed game exactly once."""
    global game_saved

    if game_saved:
        return

    survival_seconds = max(0, active_play_ms // 1000)

    try:
        database.save_game(
            player_name=player_name,
            difficulty=selected_difficulty,
            wave_reached=wave,
            score=score,
            zombies_killed=kills,
            survival_seconds=survival_seconds,
        )

        game_saved = True
        print("Game statistics saved successfully!")

    except Exception as error:
        print("Could not save game statistics:", error)


# ==================================================
# GAME RESET AND WAVE SPAWNING
# ==================================================

def reset_game():
    global player, zombies, bullets, pickups, particles, floating_texts
    global wave, score, kills, combo_count, combo_expires_at
    global last_shot_time, active_play_ms, damage_vignette_until
    global game_saved

    player = None
    zombies = []
    bullets = []
    pickups = []
    particles = []
    floating_texts = []

    wave = 1
    score = 0
    kills = 0
    combo_count = 0
    combo_expires_at = 0

    active_play_ms = 0
    last_shot_time = -1000
    damage_vignette_until = -1
    game_saved = False

    for key in upgrade_levels:
        upgrade_levels[key] = 0


def fire_player_weapon(target_x, target_y):
    global last_shot_time

    if player is None:
        return

    cooldown = player.get_effective_shoot_cooldown(active_play_ms)
    if active_play_ms - last_shot_time < cooldown:
        return

    muzzle_dist = player.radius + 10
    base_angle = math.atan2(target_y - player.y, target_x - player.x)
    sx = player.x + math.cos(base_angle) * muzzle_dist
    sy = player.y + math.sin(base_angle) * muzzle_dist

    if player.has_spread_shot(active_play_ms):
        angles = [base_angle - 0.16, base_angle, base_angle + 0.16]
    else:
        angles = [base_angle]

    for angle in angles:
        tx = sx + math.cos(angle) * 200
        ty = sy + math.sin(angle) * 200
        bullets.append(
            Bullet(
                sx,
                sy,
                tx,
                ty,
                damage=player.bullet_damage,
                color=(190, 130, 255) if len(angles) > 1 else (255, 220, 50),
            )
        )

    spawn_particles(sx, sy, YELLOW, count=4, speed_range=(1.0, 3.0), radius=2)
    last_shot_time = active_play_ms


def start_wave():
    global zombies, bullets, pickups

    zombies = []
    bullets = []
    pickups = []

    available_types = get_available_zombie_types()
    damage = get_zombie_damage()

    normal_count = 3 + wave
    runner_count = max(0, wave - 1)
    tank_count = max(0, (wave - 2) // 2)

    zombie_types = ["Normal"] * normal_count

    if "Runner" in available_types:
        zombie_types.extend(["Runner"] * runner_count)

    if "Tank" in available_types:
        zombie_types.extend(["Tank"] * tank_count)

    random.shuffle(zombie_types)

    for idx, zombie_type in enumerate(zombie_types):
        side = random.randint(0, 3)

        if side == 0:
            x = random.randint(20, SCREEN_WIDTH - 20)
            y = -30
        elif side == 1:
            x = random.randint(20, SCREEN_WIDTH - 20)
            y = SCREEN_HEIGHT + 30
        elif side == 2:
            x = -30
            y = random.randint(20, SCREEN_HEIGHT - 20)
        else:
            x = SCREEN_WIDTH + 30
            y = random.randint(20, SCREEN_HEIGHT - 20)

        # Spawn one Elite boss zombie every 5th wave
        is_elite = (wave % 5 == 0) and idx == 0
        elite_type = (
            "Tank" if (is_elite and "Tank" in available_types) else zombie_type
        )

        zombie = Zombie(
            x,
            y,
            damage=damage,
            zombie_type=elite_type,
            is_elite=is_elite,
        )

        speed_increase = (wave - 1) * 0.08

        if elite_type == "Tank":
            zombie.speed += speed_increase * 0.5
        else:
            zombie.speed += speed_increase

        zombies.append(zombie)

    if wave % 5 == 0:
        add_floating_text(
            SCREEN_WIDTH // 2, 130, f"WAVE {wave} - ALPHA BOSS INCOMING!", YELLOW
        )
    else:
        add_floating_text(SCREEN_WIDTH // 2, 130, f"WAVE {wave}", CYAN)


def begin_game():
    global player, player_name
    global current_screen, loading_start_time, game_saved

    player_name = name_input_text.strip() or "Player"

    reset_game()

    player = Player(
        SCREEN_WIDTH // 2,
        SCREEN_HEIGHT // 2,
        player_name,
        selected_character,
    )

    loading_start_time = pygame.time.get_ticks()
    game_saved = False

    current_screen = "loading"


# ==================================================
# MAIN MENU
# ==================================================

def draw_menu():
    draw_background()

    draw_centered_text(
        "ZOMBIE SURVIVAL", 180, title_font, RED
    )
    draw_centered_text(
        "A 2D Top-Down Survival Shooter",
        235, subtitle_font, GREY
    )

    start_rect = draw_button(
        "START GAME",
        SCREEN_WIDTH // 2 - 130, 320,
        260, 55, GREEN
    )

    leaderboard_rect = draw_button(
        "LEADERBOARD",
        SCREEN_WIDTH // 2 - 130, 395,
        260, 55, BLUE
    )

    exit_rect = draw_button(
        "EXIT",
        SCREEN_WIDTH // 2 - 130, 470,
        260, 55, RED
    )

    return start_rect, leaderboard_rect, exit_rect


# ==================================================
# DIFFICULTY SCREEN
# ==================================================

def draw_difficulty():
    draw_background()

    draw_centered_text(
        "SELECT DIFFICULTY", 170, title_font, YELLOW
    )
    draw_centered_text(
        "Choose your survival challenge",
        230, font, GREY
    )

    easy = draw_button("EASY", 220, 330, 180, 60, GREEN)
    medium = draw_button("MEDIUM", 440, 330, 180, 60, YELLOW)
    hard = draw_button("HARD", 660, 330, 180, 60, RED)
    extreme = draw_button(
        "EXTREME", 880, 330, 180, 60, (150, 45, 55)
    )
    back = draw_button("BACK", 30, 30, 130, 45, PANEL)

    return easy, medium, hard, extreme, back


# ==================================================
# ZOMBIE INFORMATION SCREEN
# ==================================================

def draw_zombie_card(
    x, y, width, height, title,
    image, fallback_color, description,
    health_text, speed_text
):
    rect = pygame.Rect(x, y, width, height)

    pygame.draw.rect(
        screen, PANEL, rect, border_radius=14
    )
    pygame.draw.rect(
        screen, BORDER, rect, 2, border_radius=14
    )

    title_surface = subtitle_font.render(
        title, True, WHITE
    )
    screen.blit(
        title_surface,
        title_surface.get_rect(
            center=(x + width // 2, y + 35)
        )
    )

    center = (x + width // 2, y + 112)

    if image is not None:
        screen.blit(
            image, image.get_rect(center=center)
        )
    else:
        pygame.draw.circle(
            screen, fallback_color, center, 38
        )
        pygame.draw.circle(
            screen, WHITE, center, 38, 2
        )

    details = [
        (description, GREY),
        (health_text, WHITE),
        (speed_text, WHITE),
    ]

    for index, (text, color) in enumerate(details):
        surface = small_font.render(text, True, color)
        screen.blit(
            surface,
            surface.get_rect(
                center=(
                    x + width // 2,
                    y + 170 + index * 30
                )
            )
        )


def draw_zombie_information():
    draw_background()

    draw_centered_text(
        "KNOW YOUR ENEMIES", 65, title_font, RED
    )
    draw_centered_text(
        f"Difficulty: {selected_difficulty}",
        115, font, YELLOW
    )

    card_width = 320
    card_height = 280
    gap = 30
    start_x = (
        SCREEN_WIDTH - (card_width * 3 + gap * 2)
    ) // 2
    card_y = 165

    draw_zombie_card(
        start_x, card_y, card_width, card_height,
        "NORMAL ZOMBIE", normal_image, GREEN,
        "Balanced movement", "Health: 100", "Speed: Normal"
    )

    draw_zombie_card(
        start_x + card_width + gap,
        card_y, card_width, card_height,
        "RUNNER ZOMBIE", runner_image, YELLOW,
        "Fast and dangerous", "Health: 60", "Speed: High"
    )

    draw_zombie_card(
        start_x + 2 * (card_width + gap),
        card_y, card_width, card_height,
        "TANK ZOMBIE", tank_image, RED,
        "Slow but powerful", "Health: 250", "Speed: Low"
    )

    draw_centered_text(
        f"Enemy damage per attack: {get_zombie_damage()} HP",
        500, font, YELLOW
    )

    draw_centered_text(
        "Collect power-ups & press SPACE/SHIFT to dash!",
        535, small_font, GREY
    )

    continue_rect = draw_button(
        "CONTINUE",
        SCREEN_WIDTH // 2 - 120, 590,
        240, 55, GREEN
    )
    back_rect = draw_button(
        "BACK", 30, 30, 120, 45, PANEL
    )

    return continue_rect, back_rect


# ==================================================
# PLAYER SETUP
# ==================================================

def draw_player_setup():
    draw_background()

    draw_centered_text(
        "PLAYER SETUP", 120, title_font, CYAN
    )
    draw_centered_text(
        "Enter your name and choose your survivor class",
        180, font, GREY
    )

    screen.blit(
        font.render("Player Name:", True, WHITE),
        (390, 245)
    )

    input_rect = pygame.Rect(570, 235, 320, 48)

    pygame.draw.rect(
        screen, PANEL, input_rect, border_radius=8
    )
    pygame.draw.rect(
        screen,
        CYAN if name_input_active else BORDER,
        input_rect, 2, border_radius=8
    )

    display_name = name_input_text or "Type your name..."
    name_surface = small_font.render(
        display_name, True,
        WHITE if name_input_text else GREY
    )
    screen.blit(
        name_surface,
        (input_rect.x + 12, input_rect.y + 13)
    )

    character_rect = draw_button(
        f"Character: {selected_character} (C to change)",
        SCREEN_WIDTH // 2 - 210, 315,
        420, 50, PANEL
    )

    # Archetype stat preview card
    archetype = CHARACTER_ARCHETYPES[selected_character]
    card_rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, 382, 520, 110)
    pygame.draw.rect(screen, PANEL, card_rect, border_radius=10)
    pygame.draw.rect(screen, archetype["accent"], card_rect, 2, border_radius=10)

    draw_centered_text(
        archetype["description"],
        412,
        font,
        archetype["accent"],
    )
    draw_centered_text(
        f"HP: {archetype['max_health']}   |   Speed: {archetype['speed']}   |   "
        f"Damage: {archetype['bullet_damage']}   |   Fire Rate: {archetype['shoot_cooldown']}ms",
        458,
        small_font,
        WHITE,
    )

    start_rect = draw_button(
        "START SURVIVING",
        SCREEN_WIDTH // 2 - 140, 525,
        280, 55, GREEN
    )

    back_rect = draw_button(
        "BACK", 30, 30, 120, 45, PANEL
    )

    return input_rect, character_rect, start_rect, back_rect


# ==================================================
# LOADING SCREEN
# ==================================================

def draw_loading():
    draw_background()

    draw_centered_text(
        "PREPARING THE APOCALYPSE...",
        SCREEN_HEIGHT // 2 - 45,
        title_font, RED
    )
    draw_centered_text(
        "Get ready to survive!",
        SCREEN_HEIGHT // 2 + 20,
        font, GREY
    )


# ==================================================
# GAMEPLAY HUD
# ==================================================

def draw_health_bar():
    if player is None:
        return

    x, y = 25, 25
    width, height = 240, 24

    pygame.draw.rect(
        screen, (75, 25, 30),
        (x, y, width, height), border_radius=5
    )

    ratio = max(0.0, min(1.0, player.health / player.max_health))
    if ratio > 0:
        pygame.draw.rect(
            screen,
            GREEN if ratio > 0.3 else RED,
            (x, y, int(width * ratio), height),
            border_radius=5
        )

    pygame.draw.rect(
        screen, WHITE,
        (x, y, width, height), 2, border_radius=5
    )

    health_label = f"Health: {int(player.health)}/{player.max_health}"
    if player.shield > 0:
        health_label += f"  (+{int(player.shield)} Shield)"

    screen.blit(
        small_font.render(health_label, True, WHITE),
        (x, y + 31)
    )

    # Dash cooldown bar (right of health bar)
    dash_x, dash_y = 285, 25
    dash_w, dash_h = 140, 24
    dash_ratio = player.get_dash_progress(active_play_ms)

    pygame.draw.rect(
        screen, PANEL, (dash_x, dash_y, dash_w, dash_h), border_radius=5
    )
    if dash_ratio > 0:
        pygame.draw.rect(
            screen,
            CYAN if dash_ratio >= 1.0 else BLUE,
            (dash_x, dash_y, int(dash_w * dash_ratio), dash_h),
            border_radius=5,
        )
    pygame.draw.rect(
        screen, BORDER, (dash_x, dash_y, dash_w, dash_h), 2, border_radius=5
    )
    dash_text = "DASH READY" if dash_ratio >= 1.0 else "RECHARGING"
    dash_surf = tiny_font.render(dash_text, True, WHITE)
    screen.blit(
        dash_surf,
        dash_surf.get_rect(center=(dash_x + dash_w // 2, dash_y + dash_h // 2)),
    )


def draw_active_buffs_and_combo():
    if player is None:
        return

    buff_x = SCREEN_WIDTH - 25
    buff_y = 25

    active_buffs = []
    if active_play_ms < player.rapid_fire_until:
        secs = (player.rapid_fire_until - active_play_ms) / 1000.0
        active_buffs.append((f"RAPID FIRE {secs:.1f}s", YELLOW))
    if active_play_ms < player.spread_shot_until:
        secs = (player.spread_shot_until - active_play_ms) / 1000.0
        active_buffs.append((f"SPREAD SHOT {secs:.1f}s", PURPLE))

    if combo_count >= 2 and active_play_ms < combo_expires_at:
        mult = min(5, 1 + combo_count // 3)
        active_buffs.append((f"COMBO {combo_count} (x{mult})", ORANGE))

    for index, (label, color) in enumerate(active_buffs):
        surf = small_font.render(label, True, color)
        screen.blit(
            surf,
            surf.get_rect(topright=(buff_x, buff_y + index * 26)),
        )


def draw_game(show_crosshair=True):
    draw_background()

    draw_pickups()

    for bullet in bullets:
        bullet.draw(screen)

    for zombie in zombies:
        zombie.draw(screen, active_play_ms)

    if player is not None:
        player.draw(screen, active_play_ms)

    draw_particles_and_texts()
    draw_health_bar()
    draw_active_buffs_and_combo()

    scrap_value = player.scrap if player is not None else 0
    stats = small_font.render(
        f"Player: {player_name}   Wave: {wave}   "
        f"Score: {score}   Kills: {kills}   "
        f"Scrap: {scrap_value}   Zombies left: {len(zombies)}",
        True, WHITE
    )
    screen.blit(stats, (25, 90))

    controls = small_font.render(
        "WASD: Move | Mouse: Aim & Shoot | Space/Shift: Dash | P: Pause",
        True, GREY
    )
    screen.blit(
        controls,
        controls.get_rect(
            midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 15)
        )
    )

    if active_play_ms < damage_vignette_until:
        pygame.draw.rect(
            screen,
            RED,
            (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
            8,
        )

    if show_crosshair:
        draw_crosshair()


# ==================================================
# WAVE COMPLETE & FIELD ARMORY
# ==================================================

def draw_wave_complete():
    draw_background()

    draw_centered_text(
        f"WAVE {wave} COMPLETED!",
        105, title_font, GREEN
    )
    draw_centered_text(
        f"Current score: {score}   |   Scrap available: {player.scrap if player else 0}",
        165, subtitle_font, WHITE
    )
    draw_centered_text(
        "FIELD ARMORY - Upgrade before the next wave (or press C)",
        220, font, YELLOW
    )

    upgrade_specs = [
        ("damage", "DAMAGE +5", RED),
        ("fire_rate", "FIRE RATE +12%", YELLOW),
        ("health", "HEAL +30 & +10 HP", GREEN),
        ("speed", "MOVE SPEED +0.4", CYAN),
    ]

    upgrade_rects = {}
    card_w = 240
    gap = 24
    start_x = (SCREEN_WIDTH - (card_w * 4 + gap * 3)) // 2
    card_y = 265

    for idx, (key, title, color) in enumerate(upgrade_specs):
        x = start_x + idx * (card_w + gap)
        cost = get_upgrade_cost(key)
        can_afford = player is not None and player.scrap >= cost

        panel_rect = pygame.Rect(x, card_y, card_w, 150)
        pygame.draw.rect(screen, PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(screen, BORDER, panel_rect, 2, border_radius=12)

        t_surf = small_font.render(title, True, color)
        screen.blit(
            t_surf,
            t_surf.get_rect(center=(x + card_w // 2, card_y + 32)),
        )

        lvl_surf = small_font.render(
            f"Level {upgrade_levels[key]}", True, GREY
        )
        screen.blit(
            lvl_surf,
            lvl_surf.get_rect(center=(x + card_w // 2, card_y + 64)),
        )

        btn_rect = draw_button(
            f"BUY ({cost} Scrap)",
            x + 20,
            card_y + 92,
            card_w - 40,
            42,
            color=BLUE,
            button_font=small_font,
            enabled=can_afford,
        )
        upgrade_rects[key] = btn_rect

    next_rect = draw_button(
        "NEXT WAVE",
        SCREEN_WIDTH // 2 - 140, 470,
        280, 55, GREEN
    )
    menu_rect = draw_button(
        "MAIN MENU",
        SCREEN_WIDTH // 2 - 140, 545,
        280, 55, BLUE
    )

    return next_rect, menu_rect, upgrade_rects


# ==================================================
# PAUSE SCREEN
# ==================================================

def draw_paused():
    draw_game(show_crosshair=False)
    screen.blit(PAUSE_OVERLAY, (0, 0))

    draw_centered_text(
        "PAUSED", 240, title_font, YELLOW
    )

    resume_rect = draw_button(
        "RESUME",
        SCREEN_WIDTH // 2 - 130, 330,
        260, 55, GREEN
    )
    menu_rect = draw_button(
        "MAIN MENU",
        SCREEN_WIDTH // 2 - 130, 405,
        260, 55, BLUE
    )

    return resume_rect, menu_rect


# ==================================================
# GAME OVER
# ==================================================

def draw_game_over():
    draw_background()

    draw_centered_text(
        "GAME OVER", 150, title_font, RED
    )
    draw_centered_text(
        f"Final score: {score}",
        225, subtitle_font, WHITE
    )
    draw_centered_text(
        f"Wave reached: {wave}   |   Zombies defeated: {kills}   |   "
        f"Survived: {format_duration(active_play_ms // 1000)}",
        275, font, GREY
    )

    restart_rect = draw_button(
        "PLAY AGAIN",
        SCREEN_WIDTH // 2 - 140, 360,
        280, 55, GREEN
    )
    menu_rect = draw_button(
        "MAIN MENU",
        SCREEN_WIDTH // 2 - 140, 435,
        280, 55, BLUE
    )

    return restart_rect, menu_rect


# ==================================================
# DATABASE LEADERBOARD
# ==================================================

def draw_leaderboard():
    draw_background()

    draw_centered_text(
        "LEADERBOARD", 55, title_font, YELLOW
    )

    try:
        total_games, best_score, total_kills, best_wave = (
            database.get_stats_summary()
        )
        records = database.get_top_scores(10, difficulty=leaderboard_filter)
    except Exception as error:
        total_games, best_score, total_kills, best_wave = (0, 0, 0, 0)
        records = []
        print("Could not load leaderboard:", error)

    draw_centered_text(
        f"Total Runs: {total_games}   |   High Score: {best_score}   |   "
        f"Best Wave: {best_wave}   |   Total Kills: {total_kills}",
        102,
        small_font,
        GREY,
    )

    # Difficulty filter tabs
    filter_options = ["All", "Easy", "Medium", "Hard", "Extreme"]
    filter_rects = {}
    tab_w = 110
    tab_gap = 14
    tabs_start_x = (SCREEN_WIDTH - (tab_w * len(filter_options) + tab_gap * (len(filter_options) - 1))) // 2

    for idx, diff_name in enumerate(filter_options):
        tx = tabs_start_x + idx * (tab_w + tab_gap)
        is_active = leaderboard_filter == diff_name
        filter_rects[diff_name] = draw_button(
            diff_name.upper(),
            tx,
            132,
            tab_w,
            34,
            color=BLUE if is_active else PANEL,
            button_font=small_font,
        )

    headers = ["Rank", "Player", "Difficulty", "Wave", "Score", "Kills", "Time"]
    columns = [90, 220, 480, 670, 800, 940, 1080]
    header_y = 190

    for heading, x in zip(headers, columns):
        surface = font.render(heading, True, CYAN)
        screen.blit(surface, (x, header_y))

    if not records:
        draw_centered_text(
            "No saved games yet for this filter. Complete a game first.",
            300, font, GREY
        )
    else:
        for index, record in enumerate(records):
            (
                name, difficulty, reached_wave,
                saved_score, saved_kills,
                survival_seconds, played_at
            ) = record

            y = 235 + index * 38

            values = [
                str(index + 1),
                name[:16],
                difficulty,
                str(reached_wave),
                str(saved_score),
                str(saved_kills),
                format_duration(survival_seconds),
            ]

            for value, x in zip(values, columns):
                surface = small_font.render(
                    value, True, WHITE
                )
                screen.blit(surface, (x, y))

    back_rect = draw_button(
        "BACK TO MENU",
        SCREEN_WIDTH // 2 - 140, 635,
        280, 50, BLUE
    )

    return back_rect, filter_rects


# ==================================================
# MAIN EVENT LOOP
# ==================================================

running = True

while running:
    frame_dt_ms = clock.tick(FPS)

    # Toggle custom cursor visibility during active combat
    pygame.mouse.set_visible(current_screen != "game")

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                if current_screen == "game":
                    current_screen = "paused"
                elif current_screen == "paused":
                    current_screen = "game"
                elif current_screen == "zombie_info":
                    current_screen = "difficulty"
                elif current_screen == "player_setup":
                    current_screen = "zombie_info"
                elif current_screen == "difficulty":
                    current_screen = "menu"
                elif current_screen == "leaderboard":
                    current_screen = "menu"

            if (
                current_screen == "player_setup"
                and name_input_active
            ):
                if event.key == pygame.K_RETURN:
                    name_input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    name_input_text = name_input_text[:-1]
                elif (
                    len(name_input_text) < 18
                    and event.unicode.isprintable()
                ):
                    name_input_text += event.unicode

            elif current_screen == "player_setup":
                if event.key == pygame.K_c:
                    selected_character = (
                        "Survivor"
                        if selected_character == "Soldier"
                        else "Soldier"
                    )

                elif event.key == pygame.K_RETURN:
                    begin_game()

            elif current_screen == "zombie_info":
                if event.key == pygame.K_RETURN:
                    current_screen = "player_setup"

            elif current_screen == "game":
                if event.key == pygame.K_p:
                    current_screen = "paused"
                elif (
                    event.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT)
                    and player is not None
                ):
                    if player.try_dash(active_play_ms):
                        spawn_particles(
                            player.x,
                            player.y,
                            CYAN,
                            count=10,
                            speed_range=(1.5, 4.0),
                        )

            elif current_screen == "paused":
                if event.key == pygame.K_p:
                    current_screen = "game"

            elif current_screen == "wave_complete":
                if event.key == pygame.K_c:
                    wave += 1
                    start_wave()
                    current_screen = "game"
                elif event.key == pygame.K_m:
                    reset_game()
                    current_screen = "menu"

            elif current_screen == "game_over":
                if event.key == pygame.K_r:
                    reset_game()
                    current_screen = "difficulty"

            if (
                event.key == pygame.K_q
                and current_screen in ("game", "paused")
            ):
                reset_game()
                current_screen = "menu"

        elif event.type == pygame.MOUSEBUTTONDOWN:

            if current_screen == "menu":
                start_rect, leaderboard_rect, exit_rect = draw_menu()

                if start_rect.collidepoint(event.pos):
                    current_screen = "difficulty"
                elif leaderboard_rect.collidepoint(event.pos):
                    current_screen = "leaderboard"
                elif exit_rect.collidepoint(event.pos):
                    running = False

            elif current_screen == "difficulty":
                buttons = draw_difficulty()
                easy, medium, hard, extreme, back = buttons

                if easy.collidepoint(event.pos):
                    selected_difficulty = "Easy"
                    current_screen = "zombie_info"
                elif medium.collidepoint(event.pos):
                    selected_difficulty = "Medium"
                    current_screen = "zombie_info"
                elif hard.collidepoint(event.pos):
                    selected_difficulty = "Hard"
                    current_screen = "zombie_info"
                elif extreme.collidepoint(event.pos):
                    selected_difficulty = "Extreme"
                    current_screen = "zombie_info"
                elif back.collidepoint(event.pos):
                    current_screen = "menu"

            elif current_screen == "zombie_info":
                continue_rect, back_rect = draw_zombie_information()

                if continue_rect.collidepoint(event.pos):
                    current_screen = "player_setup"
                elif back_rect.collidepoint(event.pos):
                    current_screen = "difficulty"

            elif current_screen == "player_setup":
                (
                    input_rect, character_rect,
                    start_rect, back_rect
                ) = draw_player_setup()

                if input_rect.collidepoint(event.pos):
                    name_input_active = True
                else:
                    name_input_active = False

                if character_rect.collidepoint(event.pos):
                    selected_character = (
                        "Survivor"
                        if selected_character == "Soldier"
                        else "Soldier"
                    )
                elif start_rect.collidepoint(event.pos):
                    begin_game()
                elif back_rect.collidepoint(event.pos):
                    current_screen = "zombie_info"

            elif current_screen == "game":
                if event.button == 1 and player is not None:
                    fire_player_weapon(event.pos[0], event.pos[1])

            elif current_screen == "wave_complete":
                next_rect, menu_rect, upgrade_rects = draw_wave_complete()

                if next_rect.collidepoint(event.pos):
                    wave += 1
                    start_wave()
                    current_screen = "game"
                elif menu_rect.collidepoint(event.pos):
                    reset_game()
                    current_screen = "menu"
                else:
                    for key, btn_rect in upgrade_rects.items():
                        if btn_rect.collidepoint(event.pos):
                            apply_upgrade(key)
                            break

            elif current_screen == "paused":
                resume_rect, menu_rect = draw_paused()

                if resume_rect.collidepoint(event.pos):
                    current_screen = "game"
                elif menu_rect.collidepoint(event.pos):
                    reset_game()
                    current_screen = "menu"

            elif current_screen == "game_over":
                restart_rect, menu_rect = draw_game_over()

                if restart_rect.collidepoint(event.pos):
                    reset_game()
                    current_screen = "difficulty"
                elif menu_rect.collidepoint(event.pos):
                    reset_game()
                    current_screen = "menu"

            elif current_screen == "leaderboard":
                back_rect, filter_rects = draw_leaderboard()

                if back_rect.collidepoint(event.pos):
                    current_screen = "menu"
                else:
                    for diff_name, rect in filter_rects.items():
                        if rect.collidepoint(event.pos):
                            leaderboard_filter = diff_name
                            break

    # ==================================================
    # GAME UPDATES
    # ==================================================

    if current_screen == "loading":
        if (
            pygame.time.get_ticks() - loading_start_time
            >= 1000
        ):
            start_wave()
            current_screen = "game"

    elif current_screen == "game" and player is not None:
        active_play_ms += frame_dt_ms

        mouse_pos = pygame.mouse.get_pos()
        player.update_aim(mouse_pos)

        # Support holding left mouse button to fire smoothly
        if pygame.mouse.get_pressed()[0]:
            fire_player_weapon(mouse_pos[0], mouse_pos[1])

        player.move(active_play_ms)
        player.keep_inside_screen(
            SCREEN_WIDTH, SCREEN_HEIGHT
        )

        # Reset combo if window expired
        if combo_count > 0 and active_play_ms >= combo_expires_at:
            combo_count = 0

        for zombie in zombies:
            zombie.move_towards_player(player, zombies)
            dealt = zombie.attack_player(player, active_play_ms)
            if dealt > 0:
                damage_vignette_until = active_play_ms + 160
                add_floating_text(
                    player.x, player.y - 30, f"-{int(dealt)}", RED
                )

        # Collect pickups
        for pickup in pickups[:]:
            if (
                math.hypot(player.x - pickup["x"], player.y - pickup["y"])
                <= player.radius + pickup["radius"]
            ):
                apply_pickup(pickup)
                pickups.remove(pickup)

        for bullet in bullets[:]:
            bullet.update()

            if bullet.is_off_screen(
                SCREEN_WIDTH, SCREEN_HEIGHT
            ):
                bullets.remove(bullet)
                continue

            for zombie in zombies[:]:
                if id(zombie) in bullet.hit_zombie_ids:
                    continue

                distance = math.hypot(
                    bullet.x - zombie.x,
                    bullet.y - zombie.y
                )

                if distance <= zombie.radius + bullet.radius:
                    zombie.take_damage(bullet.damage, active_play_ms)
                    bullet.hit_zombie_ids.add(id(zombie))
                    spawn_particles(
                        bullet.x,
                        bullet.y,
                        zombie.color,
                        count=4,
                        speed_range=(1.0, 3.0),
                        radius=2,
                    )

                    if bullet.pierce > 0:
                        bullet.pierce -= 1
                    elif bullet in bullets:
                        bullets.remove(bullet)

                    if zombie.health <= 0:
                        zombies.remove(zombie)
                        kills += 1
                        combo_count += 1
                        combo_expires_at = active_play_ms + COMBO_WINDOW_MS
                        multiplier = min(5, 1 + combo_count // 3)
                        gained_score = zombie.score_value * multiplier
                        score += gained_score
                        player.scrap += zombie.scrap_value

                        spawn_particles(
                            zombie.x,
                            zombie.y,
                            zombie.color,
                            count=12,
                            speed_range=(1.5, 5.0),
                            radius=3,
                        )
                        score_label = f"+{gained_score}"
                        if multiplier > 1:
                            score_label += f" (x{multiplier})"
                        add_floating_text(
                            zombie.x, zombie.y - 10, score_label, YELLOW
                        )
                        maybe_spawn_pickup(
                            zombie.x,
                            zombie.y,
                            zombie.zombie_type,
                            zombie.is_elite,
                        )

                    if bullet not in bullets:
                        break

        update_effects()

        if player.health <= 0:
            save_current_game()
            current_screen = "game_over"

        elif not zombies:
            current_screen = "wave_complete"

    # ==================================================
    # DRAW
    # ==================================================

    if current_screen == "menu":
        draw_menu()

    elif current_screen == "difficulty":
        draw_difficulty()

    elif current_screen == "zombie_info":
        draw_zombie_information()

    elif current_screen == "player_setup":
        draw_player_setup()

    elif current_screen == "loading":
        draw_loading()

    elif current_screen == "game":
        draw_game()

    elif current_screen == "wave_complete":
        draw_wave_complete()

    elif current_screen == "paused":
        draw_paused()

    elif current_screen == "game_over":
        draw_game_over()

    elif current_screen == "leaderboard":
        draw_leaderboard()

    pygame.display.flip()


pygame.mouse.set_visible(True)
pygame.quit()
sys.exit()