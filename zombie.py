import math
import os
import pygame


class Zombie:
    _sprite_cache = {}

    def __init__(self, x, y, damage=1, zombie_type="Normal", is_elite=False):
        self.x = float(x)
        self.y = float(y)
        self.zombie_type = zombie_type
        self.is_elite = is_elite
        self.damage = damage + (1 if is_elite else 0)
        self.last_attack_time = -1000
        self.attack_cooldown = 1000
        self.hit_flash_until = -1

        zombie_settings = {
            "Normal": {
                "speed": 1.5,
                "health": 100,
                "radius": 22,
                "color": (70, 190, 90),
                "image": "normal.png",
                "size": 64,
                "score_value": 1,
                "scrap_value": 1,
            },
            "Runner": {
                "speed": 3.0,
                "health": 60,
                "radius": 18,
                "color": (245, 210, 60),
                "image": "runner.png",
                "size": 56,
                "score_value": 2,
                "scrap_value": 2,
            },
            "Tank": {
                "speed": 0.8,
                "health": 250,
                "radius": 30,
                "color": (190, 65, 65),
                "image": "tank.png",
                "size": 84,
                "score_value": 5,
                "scrap_value": 4,
            },
        }

        settings = zombie_settings.get(
            zombie_type, zombie_settings["Normal"]
        )

        self.speed = settings["speed"] * (1.15 if is_elite else 1.0)
        base_health = settings["health"] * (1.75 if is_elite else 1.0)
        self.health = float(base_health)
        self.max_health = float(base_health)
        self.radius = settings["radius"] + (4 if is_elite else 0)
        self.color = settings["color"]
        self.score_value = settings["score_value"] * (3 if is_elite else 1)
        self.scrap_value = settings["scrap_value"] * (3 if is_elite else 1)

        sprite_size = settings["size"] + (12 if is_elite else 0)
        self.image = self.load_image(settings["image"], sprite_size)

    def load_image(self, filename, size):
        """Load and cache the zombie sprite from the assets/zombies folder."""
        cache_key = (filename, size)
        if cache_key in Zombie._sprite_cache:
            return Zombie._sprite_cache[cache_key]

        asset_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets",
            "zombies",
        )
        image_path = os.path.join(asset_folder, filename)

        try:
            image = pygame.image.load(image_path).convert_alpha()
            scaled = pygame.transform.smoothscale(image, (size, size))
            Zombie._sprite_cache[cache_key] = scaled
            return scaled
        except (pygame.error, FileNotFoundError, OSError):
            print(f"Zombie image unavailable: {image_path}")
            Zombie._sprite_cache[cache_key] = None
            return None

    def move_towards_player(self, player, other_zombies=None):
        """Move towards the player while gently separating from other zombies."""
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)

        move_x = 0.0
        move_y = 0.0

        if distance > self.radius + player.radius and distance != 0:
            move_x += (dx / distance) * self.speed
            move_y += (dy / distance) * self.speed

        # Soft separation force so hordes don't collapse onto one pixel
        if other_zombies:
            sep_x = 0.0
            sep_y = 0.0
            for other in other_zombies:
                if other is self:
                    continue
                ox = self.x - other.x
                oy = self.y - other.y
                odist = math.hypot(ox, oy)
                min_sep = self.radius + other.radius
                if 0 < odist < min_sep:
                    push = (min_sep - odist) / min_sep
                    sep_x += (ox / odist) * push * 0.9
                    sep_y += (oy / odist) * push * 0.9
            move_x += sep_x
            move_y += sep_y

        self.x += move_x
        self.y += move_y

    def take_damage(self, amount, current_time=None):
        """Reduce zombie health and trigger a brief hit-flash outline."""
        if current_time is None:
            current_time = pygame.time.get_ticks()
        self.health -= amount
        self.hit_flash_until = current_time + 90

    def attack_player(self, player, current_time=None):
        """Damage the player once per attack cooldown."""
        if current_time is None:
            current_time = pygame.time.get_ticks()

        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)

        if distance <= self.radius + player.radius:
            if current_time - self.last_attack_time >= self.attack_cooldown:
                if hasattr(player, "take_damage"):
                    actual_damage = player.take_damage(self.damage, current_time)
                else:
                    player.health = max(0, player.health - self.damage)
                    actual_damage = self.damage
                self.last_attack_time = current_time
                return actual_damage
        return 0

    def draw_health_bar(self, screen):
        bar_width = self.radius * 2
        bar_height = 6
        bar_x = int(self.x - self.radius)
        bar_y = int(self.y - self.radius - 12)

        pygame.draw.rect(
            screen,
            (70, 20, 20),
            (bar_x, bar_y, bar_width, bar_height),
        )

        health_ratio = max(0.0, min(1.0, self.health / self.max_health))
        current_width = int(bar_width * health_ratio)

        if current_width > 0:
            bar_color = (250, 195, 55) if self.is_elite else (70, 230, 90)
            pygame.draw.rect(
                screen,
                bar_color,
                (bar_x, bar_y, current_width, bar_height),
            )

    def draw(self, screen, current_time=None):
        """Draw the sprite, or a coloured circle if no image is found."""
        if current_time is None:
            current_time = pygame.time.get_ticks()

        cx, cy = int(self.x), int(self.y)

        if self.is_elite:
            pygame.draw.circle(
                screen,
                (250, 200, 65),
                (cx, cy),
                self.radius + 5,
                2,
            )

        if self.image is not None:
            image_rect = self.image.get_rect(center=(cx, cy))
            screen.blit(self.image, image_rect)
        else:
            pygame.draw.circle(screen, self.color, (cx, cy), self.radius)
            pygame.draw.circle(
                screen,
                (245, 245, 245),
                (cx, cy),
                self.radius,
                2,
            )

        if current_time < self.hit_flash_until:
            pygame.draw.circle(
                screen,
                (255, 255, 255),
                (cx, cy),
                self.radius + 2,
                2,
            )

        self.draw_health_bar(screen)