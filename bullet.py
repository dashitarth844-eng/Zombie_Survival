
import pygame
import math


class Bullet:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)

        self.speed = 12
        self.damage = 25
        self.radius = 5
        self.color = (255, 220, 50)

        # Calculate bullet direction
        dx = target_x - x
        dy = target_y - y

        distance = math.sqrt(dx * dx + dy * dy)

        if distance != 0:
            self.dx = dx / distance
            self.dy = dy / distance
        else:
            self.dx = 0
            self.dy = 0

    def move(self):
        """Move the bullet towards the target."""
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

    def update(self):
        """Update bullet position each game frame."""
        self.move()

    def draw(self, screen):
        """Draw the bullet on the screen."""
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x), int(self.y)),
            self.radius
        )

    def is_off_screen(self, width, height):
        """Check whether the bullet has left the screen."""
        return (
            self.x < 0
            or self.x > width
            or self.y < 0
            or self.y > height
        )