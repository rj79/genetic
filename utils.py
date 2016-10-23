from math import sqrt

def constrain(num, minimum, maximum):
    if num < minimum:
        num = minimum
    if num > maximum:
        num = maximum
    return num

class Vector2D:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2D(self.x + other.x,
                        self.y + other.y)

    def __sub__(self, other):
        return Vector2D(self.x - other.x,
                        self.y - other.y)

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other):
        self.x -= other.x
        self.y -= other.y
        return self

    def size(self):
        return sqrt(pow(self.x, 2) + pow(self.y, 2))

    def scaled(self, s):
        return Vector2D(self.x * s, self.y * s)

    def normalized(self):
        return self.scaled(1 / self.size())

    def distance(self, other):
        return sqrt(pow(other.x - self.x, 2) + pow(other.y - self.y, 2))

    def clone(self):
        return Vector2D(self.x, self.y)

    def tuple(self):
        return (self.x, self.y)

    def __str__(self):
        return '({:.2f}, {:.2f})'.format(self.x, self.y)


class Clock:
    def __init__(self):
        self.reset()

    def _read(self):
        import pygame
        return pygame.time.get_ticks() / 1000

    def is_paused(self):
        return self.paused

    def start(self):
        self.epoch = self._read()
        self.old_now = self.epoch

    def reset(self):
        self.now = 0
        self.old_now = 0
        self.elapsed_time = 0
        self.elapsed_dt = 0
        self.epoch = 0
        self.paused = False

    def get_time_and_delta(self):
        self.old_now = self.now
        self.now = self._read() - self.epoch
        return self.now, self.now - self.old_now

    def toggle_pause(self):
        if not self.paused:
            now = self._read()
            self.elapsed_time = now - self.epoch
            self.elapsed_dt = now - self.now
        else:
            now = self._read()
            self.old_now = now - self.elapsed_dt
            self.epoch = now - self.elapsed_time
        self.paused = not self.paused
