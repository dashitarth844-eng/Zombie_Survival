import math
import pygame


class Bullet:
    def __init__(
        self,
        x,
        y,
        target_x,
        target_y,
        speed=12,
        damage=25,
        radius=5,
        color=(255, 220, 50),
        pierce=0,
    ):
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)

        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.color = color
        self.pierce = pierce
        self.hit_zombie_ids = set()

        # Calculate bullet direction
        dx = target_x - x
        dy = target_y - y

        distance = math.sqrt(dx * dx + dy * dy)

        if distance != 0:
            self.dx = dx / distance
            self.dy = dy / distance
        else:
            self.dx = 1.0
            self.dy = 0.0

    def move(self):
        """Move the bullet towards the target."""
        self.prev_x = self.x
        self.prev_y = self.y
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

    def update(self):
        """Update bullet position each game frame."""
        self.move()

    def draw(self, screen):
        """Draw the bullet and a short tracer trail on the screen."""
        tail_x = self.x - self.dx * 14
        tail_y = self.y - self.dy * 14
        pygame.draw.line(
            screen,
            (255, 180, 40),
            (int(tail_x), int(tail_y)),
            (int(self.x), int(self.y)),
            max(2, self.radius - 1),
        )
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x), int(self.y)),
            self.radius,
        )

    def is_off_screen(self, width, height):
        """Check whether the bullet has left the screen."""
        return (
            self.x < -10
            or self.x > width + 10
            or self.y < -10
            or self.y > height + 10
        )