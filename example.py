#!/usr/bin/env python3
from math import pow, cos, sin, pi
from random import random, randrange, choice, randint
from utils import Clock, Vector2D
import gengine
import pygame
import time

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GREY = (128, 128, 128)
YELLOW = (255, 255, 0)

FORCE_FACTOR = 15.0

class Thing:
    def __init__(self):
        self.pos = Vector2D()
        self.velocity = Vector2D()
        self.accel = Vector2D()
        self.color = WHITE
        self.radius = 10
        self.active = True

    def apply_force(self, force):
        self.accel += force

    def set_pos(self, x, y):
        self.pos.x = x
        self.pos.y = y

    def set_color(self, color):
        self.color = color

    def set_radius(self, radius):
        self.radius = radius

    def pre_update(counter, dt):
        pass

    def post_update(self, counter, dt):
        pass

    def update(self, counter, dt):
        self.accel = Vector2D()
        self.pre_update(counter, dt)

        if self.active:
            drag = self.velocity.scaled(-2)
            self.apply_force(drag)
            self.velocity += self.accel.scaled(dt)
            self.pos += self.velocity

        self.post_update(counter, dt)

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, [int(u) for u in self.pos.tuple()], self.radius)
        pygame.draw.circle(surf, WHITE, [int(u) for u in self.pos.tuple()], self.radius, 1)

    def __str__(self):
        return '(Thing {})'.format(str(self.pos))


class Obstacle(Thing):
    def __init__(self):
        super().__init__()
        self.color = RED


class Target(Thing):
    def __init__(self):
        super().__init__()
        self.color = GREEN


class Creature(Thing):
    def __init__(self, dna=None):
        super().__init__()
        self.color = BLUE
        self.fitness = 0
        self.crashed = False
        self.completed = False
        self.ind = None
        self.arrival_time = None

    def set_individual(self, ind):
        self.ind = ind

    def complete(self, t):
        if not self.completed:
            self.completed = True
            self.arrival_time = t
            self.color = YELLOW

    def crash(self, t):
        if not self.crashed:
            self.crashed = True
            self.arrival_time = t
            self.color = GREY

    def has_completed(self):
        return self.completed

    def has_crashed(self):
        return self.crashed

    def pre_update(self, counter, dt):
        self.apply_force(self.ind.get_gene(counter))

        if self.crashed or self.completed:
            self.active = False


class Client(gengine.BaseClient):
    def __init__(self):
        self.width = 0
        self.height = 0
        self.complete_count = 0
        self.now = 0
        self.clock = Clock()

        self.draggables = []
        self.dragging = None

        self.exit_requested = False
        self.best_time = None

    def get_time(self):
        return pygame.time.get_ticks() / 1000

    def get_configuration(self):
        return {'population_size': 100,
                'dna_size': 250,
                'mutation_p': 0.001}

    def create_gene(self):
        size = random() * FORCE_FACTOR
        return self.create_random_unit_vector().scaled(size)

    def create_individual(self):
        c = Creature()
        c.set_pos(self.width / 2, self.height - 100)
        return c

    def evaluate_fitness(self, ind):
        obj = ind.custom_object

        d = obj.pos.distance(self.target.pos)

        # Avoid division by 0.
        if d < 1:
            d = 1

        # Fitness will be between 0 and 1
        fitness = 1 / (d * d)

        # The arrival factor is the arrival time normalized
        # between 0 and 1, where 0 represents the start of
        # the simulation and 1 the end of the simulation.
        if obj.arrival_time is None:
            obj.arrival_time = self.now

        arrival_factor = obj.arrival_time / self.now

        if obj.has_crashed():
            # Give more penalty to objects that crashed early
            fitness *= pow(arrival_factor, 3)
        if obj.has_completed():
            # Boost objects that completed early
            fitness /= (pow(arrival_factor, 3))

            if self.best_time is None or obj.arrival_time < self.best_time:
                self.best_time = obj.arrival_time

            self.complete_count += 1
        return fitness

    def create_random_unit_vector(self):
        angle = random() * 2 * pi;
        return Vector2D(cos(angle), sin(angle))

    def on_generation_begin(self, generation):
        self.complete_count = 0

    def on_generation_end(self, generation):
        print("Generation {} end".format(generation))
        print('  Completed: {}'.format(self.complete_count))
        if self.best_time:
            print('  Best time: {:.3f}'.format(self.best_time))

    def check_pos(self, thing, t):
        if thing.pos.x < 0 or thing.pos.x > self.width or thing.pos.y < 0 or thing.pos.y > self.height:
            thing.crash(t)

        if thing.pos.distance(self.target.pos) < thing.radius + self.target.radius:
            thing.complete(t)

        for obstacle in self.obstacles:
            if thing.pos.distance(obstacle.pos) < thing.radius + obstacle.radius:
                thing.crash(t)

    def update(self, thing, counter, dt):
        thing.update(counter, dt)

    def draw(self, thing):
        thing.draw(self.screen)

    def handle_input(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.exit_requested = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.exit_requested = True
                elif event.key == pygame.K_SPACE:
                    self.clock.toggle_pause()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                thing = self.find_thing(event.pos)
                if thing:
                    self.dragging = thing
                    pos = event.pos
                    self.drag_offset = self.dragging.pos - Vector2D(pos[0], pos[1])
            elif event.type == pygame.MOUSEBUTTONUP:
                self.dragging = None
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    pos = event.pos
                    x = Vector2D(pos[0], pos[1])
                    self.dragging.pos = x + self.drag_offset

                    # Invalidate best time if target was moved
                    if self.dragging == self.target:
                        self.best_time = None

    def find_thing(self, pos):
        x = Vector2D(pos[0], pos[1])
        for thing in self.draggables:
            if x.distance(thing.pos) < thing.radius:
                return thing
        return None

    def main_loop(self):
        pygame.init()
        self.width = 600
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.target = Target()
        self.engine = gengine.Engine(self)

        self.target.set_radius(20)
        self.target.set_pos(self.width * 2 / 3, 2 * self.target.radius)

        self.obstacles = []
        ob1 = Obstacle()
        ob1.set_radius(100)
        ob1.set_pos(self.width/2, self.height/2)

        ob2 = Obstacle()
        ob2.set_radius(30)
        ob2.set_pos(self.width/2 + 150, self.height/2 - 170)

        self.obstacles.append(ob1)
        self.obstacles.append(ob2)

        self.draggables.extend(self.obstacles)
        self.draggables.append(self.target)

        self.clock.start()
        self.engine.start()
        counter = 0
        while not self.exit_requested:

            self.handle_input()

            if not self.clock.is_paused():
                self.now = self.clock.get_time()
                dt = self.clock.get_dt()

                self.engine.for_each_custom_call(lambda x: self.update(x, counter, dt))
                self.engine.for_each_custom_call(lambda x: self.check_pos(x, self.now))

                counter += 1
                if counter == self.engine.get_gene_size():
                    self.engine.run_once()
                    self.clock.reset()
                    self.clock.start()
                    counter = 0

            self.screen.fill(BLACK)
            self.engine.for_each_custom_call(self.draw)
            for ob in self.obstacles:
                ob.draw(self.screen)

            self.target.draw(self.screen)
            pygame.display.flip()
            time.sleep(0.01)


def setup():
    client = Client()
    client.main_loop()

if __name__ == '__main__':
    setup()
