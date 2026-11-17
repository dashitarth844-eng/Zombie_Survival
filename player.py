import math
import pygame


CHARACTER_ARCHETYPES = {
    "Soldier": {
        "speed": 5.0,
        "max_health": 100,
        "shoot_cooldown": 280,
        "bullet_damage": 25,
        "dash_cooldown": 2200,
        "color": (50, 120, 220),
        "accent": (120, 185, 255),
        "description": "Balanced armor, high damage rounds",
    },
    "Survivor": {
        "speed": 6.2,
        "max_health": 85,
        "shoot_cooldown": 230,
        "bullet_damage": 22,
        "dash_cooldown": 1700,
        "color": (46, 168, 156),
        "accent": (110, 235, 215),
        "description": "Fast movement, rapid trigger & dash",
    },
}


class Player:
    def __init__(self, x, y, name, character):
        self.x = float(x)
        self.y = float(y)

        self.name = name
        self.character = character

        archetype = CHARACTER_ARCHETYPES.get(
            character, CHARACTER_ARCHETYPES["Soldier"]
        )

        self.speed = archetype["speed"]
        self.max_health = archetype["max_health"]
        self.health = float(self.max_health)
        self.shoot_cooldown = archetype["shoot_cooldown"]
        self.bullet_damage = archetype["bullet_damage"]
        self.dash_cooldown = archetype["dash_cooldown"]

        self.radius = 25
        self.color = archetype["color"]
        self.accent_color = archetype["accent"]

        # Combat & movement state
        self.aim_angle = 0.0
        self.last_move_dx = 1.0
        self.last_move_dy = 0.0
        self.shield = 0
        self.scrap = 0

        # Dash state
        self.is_dashing = False
        self.dash_speed = 14.5
        self.dash_duration = 160
        self.dash_end_time = -1
        self.last_dash_time = -10000
        self.dash_dx = 1.0
        self.dash_dy = 0.0

        # Power-up timers & hit feedback (measured in active_play_ms)
        self.rapid_fire_until = -1
        self.spread_shot_until = -1
        self.hit_flash_until = -1
        self.invulnerable_until = -1

        self._name_font = pygame.font.Font(None, 28)

    def update_aim(self, mouse_pos):
        """Point the player's aim angle toward the mouse cursor."""
        mx, my = mouse_pos
        self.aim_angle = math.atan2(my - self.y, mx - self.x)

    def get_effective_shoot_cooldown(self, current_time):
        """Return shoot cooldown factoring in temporary Rapid Fire buff."""
        if current_time < self.rapid_fire_until:
            return max(90, int(self.shoot_cooldown * 0.55))
        return self.shoot_cooldown

    def has_spread_shot(self, current_time):
        """Check whether triple-bullet Spread Shot is active."""
        return current_time < self.spread_shot_until

    def try_dash(self, current_time=None):
        """Trigger a quick directional dash if off cooldown."""
        if current_time is None:
            current_time = pygame.time.get_ticks()

        if self.is_dashing:
            return False

        if current_time - self.last_dash_time < self.dash_cooldown:
            return False

        keys = pygame.key.get_pressed()
        dx = 0.0
        dy = 0.0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1.0

        dist = math.hypot(dx, dy)
        if dist > 0:
            self.dash_dx = dx / dist
            self.dash_dy = dy / dist
        else:
            self.dash_dx = math.cos(self.aim_angle)
            self.dash_dy = math.sin(self.aim_angle)

        self.is_dashing = True
        self.dash_end_time = current_time + self.dash_duration
        self.last_dash_time = current_time
        self.invulnerable_until = max(
            self.invulnerable_until, self.dash_end_time + 40
        )
        return True

    def get_dash_progress(self, current_time):
        """Return normalized dash readiness from 0.0 to 1.0."""
        elapsed = current_time - self.last_dash_time
        return max(0.0, min(1.0, elapsed / self.dash_cooldown))

    def move(self, current_time=None):
        """Move player with normalized WASD/Arrow controls or active dash."""
        if current_time is None:
            current_time = pygame.time.get_ticks()

        if self.is_dashing:
            if current_time < self.dash_end_time:
                self.x += self.dash_dx * self.dash_speed
                self.y += self.dash_dy * self.dash_speed
                return
            self.is_dashing = False

        keys = pygame.key.get_pressed()
        dx = 0.0
        dy = 0.0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1.0

        dist = math.hypot(dx, dy)
        if dist > 0:
            nx = dx / dist
            ny = dy / dist
            self.x += nx * self.speed
            self.y += ny * self.speed
            self.last_move_dx = nx
            self.last_move_dy = ny

    def take_damage(self, amount, current_time=None):
        """Apply damage considering dash i-frames and shield. Returns HP lost."""
        if current_time is None:
            current_time = pygame.time.get_ticks()

        if current_time < self.invulnerable_until:
            return 0

        remaining = float(amount)
        if self.shield > 0:
            absorbed = min(self.shield, remaining)
            self.shield -= absorbed
            remaining -= absorbed

        if remaining > 0:
            self.health = max(0.0, self.health - remaining)
            self.hit_flash_until = current_time + 140

        return remaining

    def keep_inside_screen(self, width, height):
        if self.x < self.radius:
            self.x = float(self.radius)

        if self.x > width - self.radius:
            self.x = float(width - self.radius)

        if self.y < self.radius:
            self.y = float(self.radius)

        if self.y > height - self.radius:
            self.y = float(height - self.radius)

    def draw(self, screen, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()

        cx, cy = int(self.x), int(self.y)

        # Dash aura
        if self.is_dashing:
            pygame.draw.circle(
                screen,
                (120, 230, 255),
                (cx, cy),
                self.radius + 7,
                2,
            )

        # Shield aura
        if self.shield > 0:
            pygame.draw.circle(
                screen,
                (80, 200, 255),
                (cx, cy),
                self.radius + 5,
                2,
            )

        # Gun barrel pointing toward cursor
        barrel_len = self.radius + 12
        bx = self.x + math.cos(self.aim_angle) * barrel_len
        by = self.y + math.sin(self.aim_angle) * barrel_len
        pygame.draw.line(
            screen,
            (215, 225, 235),
            (cx, cy),
            (int(bx), int(by)),
            6,
        )

        # Player body (flash red on hit)
        body_color = (
            (235, 85, 85)
            if current_time < self.hit_flash_until
            else self.color
        )
        pygame.draw.circle(screen, body_color, (cx, cy), self.radius)

        # Inner character accent ring
        pygame.draw.circle(
            screen,
            self.accent_color,
            (cx, cy),
            self.radius - 8,
            2,
        )

        # Player outline
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (cx, cy),
            self.radius,
            2,
        )

        # Player name
        name_text = self._name_font.render(
            self.name,
            True,
            (255, 255, 255),
        )
        screen.blit(
            name_text,
            name_text.get_rect(center=(cx, cy - 40)),
        )