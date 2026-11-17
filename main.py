
import math
import os
import random
import sys

import pygame
import database

from player import Player
from zombie import Zombie
from bullet import Bullet


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

font = pygame.font.Font(None, 30)
small_font = pygame.font.Font(None, 23)
title_font = pygame.font.Font(None, 76)
subtitle_font = pygame.font.Font(None, 40)


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

name_input_text = "Player"
name_input_active = False

zombies = []
bullets = []

wave = 1
score = 0
kills = 0

last_shot_time = 0
shoot_cooldown = 300

loading_start_time = 0
game_start_time = 0
game_saved = False


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
    color=BLUE, text_color=WHITE
):
    rect = pygame.Rect(x, y, width, height)
    button_color = color

    if rect.collidepoint(pygame.mouse.get_pos()):
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

    text_surface = font.render(
        text, True, text_color
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


# ==================================================
# DIFFICULTY
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


# ==================================================
# DATABASE CONNECTION
# ==================================================

def save_current_game():
    """Save a completed game exactly once."""
    global game_saved

    if game_saved:
        return

    survival_seconds = max(
        0,
        (pygame.time.get_ticks() - game_start_time) // 1000
    )

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
    global player, zombies, bullets
    global wave, score, kills, last_shot_time
    global game_saved, game_start_time

    player = None
    zombies = []
    bullets = []

    wave = 1
    score = 0
    kills = 0
    last_shot_time = 0

    game_saved = False
    game_start_time = 0


def start_wave():
    global zombies

    zombies = []

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

    for zombie_type in zombie_types:
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

        zombie = Zombie(
            x, y,
            damage=damage,
            zombie_type=zombie_type
        )

        speed_increase = (wave - 1) * 0.08

        if zombie_type == "Tank":
            zombie.speed += speed_increase * 0.5
        else:
            zombie.speed += speed_increase

        zombies.append(zombie)


def begin_game():
    global player, player_name
    global current_screen, loading_start_time
    global game_start_time, game_saved

    player_name = name_input_text.strip() or "Player"

    reset_game()

    player = Player(
        SCREEN_WIDTH // 2,
        SCREEN_HEIGHT // 2,
        player_name,
        selected_character
    )

    loading_start_time = pygame.time.get_ticks()
    game_start_time = loading_start_time
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
        "Keep moving and aim carefully!",
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
        "PLAYER SETUP", 150, title_font, CYAN
    )
    draw_centered_text(
        "Enter your name before starting",
        215, font, GREY
    )

    screen.blit(
        font.render("Player Name:", True, WHITE),
        (390, 290)
    )

    input_rect = pygame.Rect(570, 280, 320, 48)

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
        SCREEN_WIDTH // 2 - 210, 365,
        420, 50, PANEL
    )

    start_rect = draw_button(
        "START SURVIVING",
        SCREEN_WIDTH // 2 - 140, 455,
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

    ratio = max(0, min(1, player.health / 100))
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

    screen.blit(
        small_font.render(
            f"Health: {int(player.health)}/100",
            True, WHITE
        ),
        (x, y + 31)
    )


def draw_game():
    draw_background()

    for bullet in bullets:
        bullet.draw(screen)

    for zombie in zombies:
        zombie.draw(screen)

    if player is not None:
        player.draw(screen)

    draw_health_bar()

    stats = small_font.render(
        f"Player: {player_name}   Wave: {wave}   "
        f"Score: {score}   Kills: {kills}   "
        f"Zombies left: {len(zombies)}",
        True, WHITE
    )
    screen.blit(stats, (25, 90))

    controls = small_font.render(
        "WASD: Move | Mouse: Shoot | P: Pause",
        True, GREY
    )
    screen.blit(
        controls,
        controls.get_rect(
            midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 15)
        )
    )


# ==================================================
# WAVE COMPLETE
# ==================================================

def draw_wave_complete():
    draw_background()

    draw_centered_text(
        f"WAVE {wave} COMPLETED!",
        210, title_font, GREEN
    )
    draw_centered_text(
        f"Current score: {score}",
        275, subtitle_font, WHITE
    )
    draw_centered_text(
        "Ready for the next wave?",
        325, font, GREY
    )

    next_rect = draw_button(
        "NEXT WAVE",
        SCREEN_WIDTH // 2 - 140, 390,
        280, 55, GREEN
    )
    menu_rect = draw_button(
        "MAIN MENU",
        SCREEN_WIDTH // 2 - 140, 465,
        280, 55, BLUE
    )

    return next_rect, menu_rect


# ==================================================
# PAUSE SCREEN
# ==================================================

def draw_paused():
    draw_game()

    overlay = pygame.Surface(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 185))
    screen.blit(overlay, (0, 0))

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
        "GAME OVER", 180, title_font, RED
    )
    draw_centered_text(
        f"Final score: {score}",
        250, subtitle_font, WHITE
    )
    draw_centered_text(
        f"Zombies defeated: {kills}",
        295, font, GREY
    )

    restart_rect = draw_button(
        "PLAY AGAIN",
        SCREEN_WIDTH // 2 - 140, 370,
        280, 55, GREEN
    )
    menu_rect = draw_button(
        "MAIN MENU",
        SCREEN_WIDTH // 2 - 140, 445,
        280, 55, BLUE
    )

    return restart_rect, menu_rect


# ==================================================
# DATABASE LEADERBOARD
# ==================================================

def draw_leaderboard():
    draw_background()

    draw_centered_text(
        "LEADERBOARD", 65, title_font, YELLOW
    )

    try:
        records = database.get_top_scores(10)
    except Exception as error:
        records = []
        print("Could not load leaderboard:", error)

    headers = ["Rank", "Player", "Difficulty", "Wave", "Score", "Kills"]
    columns = [100, 280, 520, 760, 900, 1050]
    header_y = 150

    for heading, x in zip(headers, columns):
        surface = font.render(heading, True, CYAN)
        screen.blit(surface, (x, header_y))

    if not records:
        draw_centered_text(
            "No saved games yet. Complete a game first.",
            250, font, GREY
        )
    else:
        for index, record in enumerate(records):
            (
                name, difficulty, reached_wave,
                saved_score, saved_kills,
                survival_seconds, played_at
            ) = record

            y = 200 + index * 40

            values = [
                str(index + 1),
                name[:16],
                difficulty,
                str(reached_wave),
                str(saved_score),
                str(saved_kills),
            ]

            for value, x in zip(values, columns):
                surface = small_font.render(
                    value, True, WHITE
                )
                screen.blit(surface, (x, y))

    back_rect = draw_button(
        "BACK TO MENU",
        SCREEN_WIDTH // 2 - 140, 630,
        280, 50, BLUE
    )

    return back_rect


# ==================================================
# MAIN EVENT LOOP
# ==================================================

running = True

while running:

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
                elif character_rect.collidepoint(event.pos):
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
                    now = pygame.time.get_ticks()

                    if now - last_shot_time >= shoot_cooldown:
                        bullets.append(
                            Bullet(
                                player.x, player.y,
                                event.pos[0], event.pos[1]
                            )
                        )
                        last_shot_time = now

            elif current_screen == "wave_complete":
                next_rect, menu_rect = draw_wave_complete()

                if next_rect.collidepoint(event.pos):
                    wave += 1
                    start_wave()
                    current_screen = "game"
                elif menu_rect.collidepoint(event.pos):
                    reset_game()
                    current_screen = "menu"

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
                back_rect = draw_leaderboard()

                if back_rect.collidepoint(event.pos):
                    current_screen = "menu"

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

        player.move()
        player.keep_inside_screen(
            SCREEN_WIDTH, SCREEN_HEIGHT
        )

        for zombie in zombies:
            zombie.move_towards_player(player)
            zombie.attack_player(player)

        for bullet in bullets[:]:
            bullet.update()

            if bullet.is_off_screen(
                SCREEN_WIDTH, SCREEN_HEIGHT
            ):
                bullets.remove(bullet)
                continue

            for zombie in zombies[:]:
                distance = math.hypot(
                    bullet.x - zombie.x,
                    bullet.y - zombie.y
                )

                if distance <= zombie.radius + bullet.radius:
                    zombie.health -= bullet.damage

                    if bullet in bullets:
                        bullets.remove(bullet)

                    if zombie.health <= 0:
                        zombies.remove(zombie)
                        score += 1
                        kills += 1

                    break

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
    clock.tick(FPS)


pygame.quit()
sys.exit()