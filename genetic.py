#!/usr/bin/env python3
from math import sqrt, pow, cos, sin, pi
from random import random, randrange, choice, randint
import pygame
import time
import gentext

def rmap(val, smin, smax, tmin, tmax):
    return (smin + (val - smin) / (smax - smin) * (tmax - tmin) + tmin)

def rlimit(val, low, high):
    return min(max(val, low), high)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

RADIUS = 10
FORCE_FACTOR = 2.0

MAX_COUNT = 200
counter = 0

class Vector2d:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2d(self.x + other.x,
                        self.y + other.y)

    def __sub__(self, other):
        return Vector2d(self.x - other.x,
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
        return Vector2d(self.x * s, self.y * s)

    def normalized(self):
        return self.scaled(1 / self.size())

    def distance(self, other):
        return sqrt(pow(other.x - self.x, 2) + pow(other.y - self.y, 2))

    def clone(self):
        return Vector2d(self.x, self.y)

    def tuple(self):
        return (self.x, self.y)

    def __str__(self):
        return '({:.2f}, {:.2f})'.format(self.x, self.y)

class Thing:
    def __init__(self):
        self.pos = Vector2d()
        self.velocity = Vector2d()
        self.accel = Vector2d()
        self.color = WHITE
        self.radius = RADIUS
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

    def pre_update(self, dt):
        pass

    def update(self, dt):
        self.pre_update(dt)

        if self.active:
            drag = self.velocity.scaled(-0.1*dt)
            self.apply_force(drag)
            self.velocity += self.accel.scaled(dt)
            self.pos += self.velocity
            self.accel = Vector2d()

        self.post_update(dt)

    def post_update(self, dt):
        pass

    def draw(self, surf):
        #print('DRAW', self.pos)
        pygame.draw.circle(surf, self.color, [int(u) for u in self.pos.tuple()], self.radius)
        pygame.draw.circle(surf, WHITE, [int(u) for u in self.pos.tuple()], self.radius, 1)


class Obstacle(Thing):
    def __init__(self):
        super().__init__()
        self.color = RED


class Target(Thing):
    def __init__(self):
        super().__init__()
        self.color = GREEN


class Evaluator:
    def __init__(self, target=None):
        self.target = target
        self.done = False

    def evaluate(self, ind):
        fitness = 1
        ind.set_fitness(fitness)

        # TODO: Calculate done condition
        # ... code here...

        d = ind.custom_object.pos.distance(self.target.pos)
        return fitness

    def finished(self):
        return self.done


class Creature(Thing):
    def __init__(self, dna=None):
        super().__init__()
        self.fitness = 0
        self.failed = False
        self.completed = False
        self.color = BLUE
        #if dna is None:
        #    self.dna = DNA()
        #else:
        #    self.dna = dna.clone()

        self.ind = None

    def set_individual(self, ind):
        self.ind = ind

    def set_dna(self, dna):
        pass
        #self.dna = dna.clone()

    def complete(self):
        self.completed = True
        self.complete_time = counter

    def mutate(self):
        #self.dna = self.dna.mutated()
        pass

    def fail(self):
        self.failed = True
        self.fail_time = counter

    def reset(self):
        self.fitness = 0
        self.failed = False
        self.completed = False
        self.active = True

    def action(self):
        self.pre_update(0)

    def pre_update(self, dt):
        global counter
        if counter >= self.ind.get_genes_length():
            self.failed = True
        else:
            self.accel = self.ind.get_gene(counter)

        if self.failed or self.completed:
            self.active = False

        #self.apply_force(self.velocity.scaled(-0.1))


class Client(gentext.BaseClient):
    def create_gene(self):
        return self.create_random_unit_vector().scaled(FORCE_FACTOR)

    def create_individual(self):
        return Creature()

    def create_random_unit_vector(self):
        angle = random() * 2 * pi;
        return Vector2d(cos(angle), sin(angle))

    def on_generation_begin(self, generation):
        print("Generation {}".format(generation))

    def check_pos(self, thing):
        if thing.pos.x < 0 or thing.pos.x > self.width or thing.pos.y < 0 or thing.pos.y > self.height:
            thing.fail()
        if thing.pos.distance(self.target.pos) < 2 * RADIUS:
            thing.complete()

        for obstacle in self.obstacles:
            if thing.pos.distance(obstacle.pos) < thing.radius + obstacle.radius:
                thing.fail()

    def update(self, thing, dt):
        #print('UPDATE', thing, dt)
        thing.update(dt)

    def draw(self, thing):
        thing.draw(self.screen)

    def main_loop(self):
        self.target = Target()
        self.evaluator = Evaluator(self.target)
        self.engine = gentext.Engine(self, self.evaluator)
        self.engine.populate_random(10, 50)

        pygame.init()
        self.width = 600
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        clock = pygame.time.Clock()
        startx = self.width / 2
        starty = self.height - 100
        self.engine.for_each_custom_call(lambda x: x.set_pos(startx, starty))
        done = False

        self.target.set_radius(20)
        self.target.set_pos(self.width * 2 / 3, 2 * self.target.radius)

        self.obstacles = []
        ob1 = Obstacle()
        ob1.set_radius(100)
        ob1.set_pos(self.width/2, self.height/2)
        self.obstacles.append(ob1)

        global counter

        while not done:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        done = True

            dt = clock.tick() / 1000

            self.engine.for_each_custom_call(lambda x: self.update(x, dt))
            self.engine.for_each_custom_call(self.check_pos)

            counter += 1
            if counter == self.engine.get_gene_size():
                self.engine.run_once()
                self.engine.for_each_custom_call(lambda x: x.set_pos(self.width/2, self.height/2))
                counter = 0

            print(counter)
            #
                #population.combine(target)
                #population.mutate()
                #population.set_position(startx, starty)
                #population.draw(screen)

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
