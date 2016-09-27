#!/usr/bin/env python3
from math import sqrt, pow, cos, sin, pi
from random import random, randrange, choice, randint
import pygame
import time

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

def create_random_unit_vector():
    angle = random() * 2 * pi;
    return Vector2d(cos(angle), sin(angle))

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


class DNA:
    LENGTH = MAX_COUNT
    MUTATION_P = 0.001

    def __init__(self, genes=None):
        if genes is None:
            self.genes = []
            for i in range(DNA.LENGTH):
                self.genes.append(create_random_unit_vector().scaled(FORCE_FACTOR))
        else:
            self.genes = genes[:]

    def get_gene(self, index):
        return self.genes[index]

    def combined(self, other):
        new_genes = []
        #for i in range(len(self.genes)):
        #    if random() < 0.5:
        #        new_genes.append(self.genes[i])
        #    else:
        #        new_genes.append(other.genes[i])
        #return DNA(new_genes)
        n = randint(0, len(self.genes))
        for i in range(len(self.genes)):
            if i < n:
                new_genes.append(self.genes[i].clone())
            else:
                new_genes.append(other.genes[i].clone())
        return DNA(new_genes)

    def mutated(self):
        new_genes = []
        for i in range(len(self.genes)):
            if random() < DNA.MUTATION_P:
                new_genes.append(create_random_unit_vector().scaled(FORCE_FACTOR))
            else:
                new_genes.append(self.genes[i].clone())
        return DNA(new_genes)

    def clone(self):
        return DNA(self.genes)

    def __str__(self):
        return 'DNA <' + ', '.join([str(gene) for gene in self.genes]) + '>'


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


class Creature(Thing):
    def __init__(self, dna=None):
        super().__init__()
        self.fitness = 0
        self.failed = False
        self.completed = False
        self.color = BLUE
        if dna is None:
            self.dna = DNA()
        else:
            self.dna = dna.clone()

    def set_dna(self, dna):
        self.dna = dna.clone()

    def complete(self):
        self.completed = True
        self.complete_time = counter

    def mutate(self):
        self.dna = self.dna.mutated()

    def fail(self):
        self.failed = True
        self.fail_time = counter

    def reset(self):
        self.fitness = 0
        self.failed = False
        self.completed = False
        self.active = True

    def pre_update(self, dt):
        global counter
        self.accel = self.dna.get_gene(counter)
        if counter == DNA.LENGTH:
            self.failed = True

        if self.failed or self.completed:
            self.active = False

        #self.apply_force(self.velocity.scaled(-0.1))


class Population:
    def __init__(self, size=1):
        self.things = []
        for i in range(size):
            self.things.append(Creature())

    def update(self, dt):
        for thing in self.things:
            thing.update(dt)

    def set_position(self, x, y):
        for thing in self.things:
            thing.set_pos(x, y)
            thing.reset()

    def combine(self, target):
        max_distance = 0
        min_distance = 100000

        for thing in self.things:
            d = thing.pos.distance(target.pos)
            if d < min_distance:
                min_distance = d
            if d > max_distance:
                max_distance = d

        d_range = max_distance - min_distance
        print('d_range: {}'.format(d_range))
        for thing in self.things:
            d = thing.pos.distance(target.pos)
            thing.fitness = thing.radius / d

        completed = 0
        max_fitness = 0
        for thing in self.things:
            if thing.failed:
                pass
                #thing.fitness /= 10
                #thing.fitness /= (float(MAX_COUNT) / float(thing.fail_time))
            if thing.completed:
                completed += 1
                thing.fitness *= 10
                thing.fitness *=  (float(MAX_COUNT) / float(thing.complete_time))
            if thing.fitness > max_fitness:
                max_fitness = thing.fitness

        #for thing in self.things:
        #    thing.fitness /= max_fitness

        print('Max fitness {:.3f}'.format(max_fitness))
        print('Completed {}'.format(completed))

        parent_pool = []
        for thing in self.things:
            f = rlimit(int(1000 * thing.fitness), 1, 100000)
            #print("added {} times".format(f))
            for i in range(f):
                parent_pool.append(thing)

        print("parent pool size: {}".format(len(parent_pool)))
        new_dnas = []
        for thing in self.things:
            parent1 = choice(parent_pool)
            parent2 = choice(parent_pool)
            while parent2 == parent1:
                parent2 = choice(parent_pool)
            new_dnas.append(parent1.dna.combined(parent2.dna))

        i = 0
        for thing in self.things:
            thing.set_dna(new_dnas[i])
            ++i

    def mutate(self):
        for thing in self.things:
            thing.mutate()

    def draw(self, surf):
        for thing in self.things:
            thing.draw(surf)


def main_loop():
    pygame.init()
    width = 600
    height = 600
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    population = Population(100)
    startx = width / 2
    starty = height - 100
    population.set_position(startx, starty)
    done = False

    target = Target()
    target.set_radius(20)
    target.set_pos(width * 2 / 3, 2 * target.radius)

    obstacles = []
    ob1 = Obstacle()
    ob1.set_radius(100)
    ob1.set_pos(width/2, height/2)
    obstacles.append(ob1)

    global counter

    while not done:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if event.type == pygame.KEYDOWN:
                        done = True
        time.sleep(0.01)
        dt = clock.tick() / 1000
        screen.fill(BLACK)
        population.update(dt)

        for thing in population.things:
            if thing.pos.x < 0 or thing.pos.x > width or thing.pos.y < 0 or thing.pos.y > height:
                thing.fail()
            if thing.pos.distance(target.pos) < 2 * RADIUS:
                thing.complete()

            for obstacle in obstacles:
                if thing.pos.distance(obstacle.pos) < thing.radius + obstacle.radius:
                    thing.fail()


        counter += 1
        if counter == MAX_COUNT:
            print("-------- Restart --------")
            counter = 0
            population.combine(target)
            population.mutate()
            population.set_position(startx, starty)
        population.draw(screen)

        for ob in obstacles:
            ob.draw(screen)

        target.draw(screen)
        pygame.display.flip()

if __name__ == '__main__':
    main_loop()
