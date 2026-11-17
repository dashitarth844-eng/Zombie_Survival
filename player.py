import pygame


class Player:

    def __init__(self, x, y, name, character):

        self.x = x
        self.y = y

        self.name = name
        self.character = character

        self.speed = 5
        self.health = 100

        self.radius = 25

        self.color = (50, 120, 220)


    def move(self):

        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]:
            self.y -= self.speed

        if keys[pygame.K_s]:
            self.y += self.speed

        if keys[pygame.K_a]:
            self.x -= self.speed

        if keys[pygame.K_d]:
            self.x += self.speed


    def keep_inside_screen(self, width, height):

        if self.x < self.radius:
            self.x = self.radius

        if self.x > width - self.radius:
            self.x = width - self.radius

        if self.y < self.radius:
            self.y = self.radius

        if self.y > height - self.radius:
            self.y = height - self.radius


    def draw(self, screen):

        # Draw player
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x), int(self.y)),
            self.radius
        )

        # Player outline
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(self.x), int(self.y)),
            self.radius,
            2
        )

        # Player name
        font = pygame.font.Font(None, 30)

        name_text = font.render(
            self.name,
            True,
            (255, 255, 255)
        )

        screen.blit(
            name_text,
            name_text.get_rect(
                center=(int(self.x), int(self.y) - 40)
            )
        )