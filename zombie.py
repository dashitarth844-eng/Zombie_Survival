
import math
import os
import pygame


class Zombie:
    def __init__(self, x, y, damage=1, zombie_type="Normal"):
        self.x = float(x)
        self.y = float(y)
        self.zombie_type = zombie_type
        self.damage = damage
        self.last_attack_time = 0
        self.attack_cooldown = 1000

        zombie_settings = {
            "Normal": {
                "speed": 1.5,
                "health": 100,
                "radius": 22,
                "color": (70, 190, 90),
                "image": "normal.png",
                "size": 64,
            },
            "Runner": {
                "speed": 3.0,
                "health": 60,
                "radius": 18,
                "color": (245, 210, 60),
                "image": "runner.png",
                "size": 56,
            },
            "Tank": {
                "speed": 0.8,
                "health": 250,
                "radius": 30,
                "color": (190, 65, 65),
                "image": "tank.png",
                "size": 84,
            },
        }

        settings = zombie_settings.get(
            zombie_type, zombie_settings["Normal"]
        )

        self.speed = settings["speed"]
        self.health = settings["health"]
        self.max_health = settings["health"]
        self.radius = settings["radius"]
        self.color = settings["color"]

        self.image = self.load_image(
            settings["image"], settings["size"]
        )

    def load_image(self, filename, size):
        """Load the zombie sprite from the assets/zombies folder."""
        asset_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets",
            "zombies",
        )
        image_path = os.path.join(asset_folder, filename)

        try:
            image = pygame.image.load(image_path).convert_alpha()
            return pygame.transform.smoothscale(
                image, (size, size)
            )
        except (pygame.error, FileNotFoundError, OSError):
            print(f"Zombie image unavailable: {image_path}")
            return None

    def move_towards_player(self, player):
        """Move the zombie towards the player."""
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)

        if distance > self.radius + player.radius:
            if distance != 0:
                self.x += (dx / distance) * self.speed
                self.y += (dy / distance) * self.speed

    def attack_player(self, player):
        """Damage the player once per attack cooldown."""
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)

        if distance <= self.radius + player.radius:
            current_time = pygame.time.get_ticks()

            if current_time - self.last_attack_time >= self.attack_cooldown:
                player.health -= self.damage
                player.health = max(0, player.health)
                self.last_attack_time = current_time

    def draw_health_bar(self, screen):
        bar_width = self.radius * 2
        bar_height = 6
        bar_x = int(self.x - self.radius)
        bar_y = int(self.y - self.radius - 12)

        pygame.draw.rect(
            screen, (70, 20, 20),
            (bar_x, bar_y, bar_width, bar_height)
        )

        health_ratio = max(
            0, min(1, self.health / self.max_health)
        )
        current_width = int(bar_width * health_ratio)

        if current_width > 0:
            pygame.draw.rect(
                screen, (70, 230, 90),
                (bar_x, bar_y, current_width, bar_height)
            )

    def draw(self, screen):
        """Draw the sprite, or a coloured circle if no image is found."""
        if self.image is not None:
            image_rect = self.image.get_rect(
                center=(int(self.x), int(self.y))
            )
            screen.blit(self.image, image_rect)
        else:
            pygame.draw.circle(
                screen,
                self.color,
                (int(self.x), int(self.y)),
                self.radius,
            )
            pygame.draw.circle(
                screen,
                (245, 245, 245),
                (int(self.x), int(self.y)),
                self.radius,
                2,
            )

        self.draw_health_bar(screen)