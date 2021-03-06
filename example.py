#!/usr/bin/env python3
from math import pow, cos, sin, pi
from random import random, randrange, choice, randint
from utils import Clock, Vector2D, constrain
import gengine
import pygame
import time
import pickle

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GREY = (128, 128, 128)
YELLOW = (255, 255, 0)
DARK_PINK = (128, 0, 128)

FORCE_FACTOR = 50.0
DRAG_FACTOR = 1

MUTATION_SPEEDS = [0,
                   0.0001, 0.0002, 0.0005,
                   0.001, 0.002, 0.005,
                   0.01, 0.02, 0.05,
                   0.1, 0.2, 0.5,
                   1.0]

LEFT_BUTTON = 1
MIDDLE_BUTTON = 2
RIGHT_BUTTON = 3
SCROLL_UP = 4
SCROLL_DOWN = 5

STATEFILE = 'state.pickle'


class Thing:
    def __init__(self):
        self.pos = Vector2D()
        self.velocity = Vector2D()
        self.accel = Vector2D()
        self.color = WHITE
        self.radius = 10
        self.active = True
        self.removable = False

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
            v_size = self.velocity.size()
            drag = self.velocity.scaled(-DRAG_FACTOR * pow(v_size, 2))
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
        self.radius = 20
        self.removable = True


class Target(Thing):
    def __init__(self):
        super().__init__()
        self.color = GREEN


class Launcher(Thing):
    def __init__(self):
        super().__init__()
        self.color = DARK_PINK
        self.radius = 15

    def set_radius(self, radius):
        # Don't allow radius to be changed
        pass


class Creature(Thing, gengine.BaseIndividualMixin):
    def __init__(self):
        super().__init__()
        self.color = BLUE
        self.fitness = 0
        self.crashed = False
        self.completed = False
        self.arrival_time = None

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
        if self.crashed or self.completed:
            self.active = False
        else:
            self.apply_force(self.get_dna()[counter])

DNA_SIZE = 300

class Client(gengine.BaseClient):
    def __init__(self):
        self.width = 0
        self.height = 0
        self.complete_count = 0
        self.latest_complete_count = 0
        self.now = 0
        self.clock = Clock()

        self.exit_requested = False
        self.draggables = []
        self.dragging = None
        self.launcher = None
        self.target = None

        self.best_time = None
        self.mutate_index = 4
        self.font = None

        self.all_inactive = True
        self.generation = 0

    def get_configuration(self):
        return {'population_size': 100,
                'mutation_p': MUTATION_SPEEDS[self.mutate_index]}

    def create_dna(self):
        dna = []
        for i in range(DNA_SIZE):
            size = random() * FORCE_FACTOR
            dna.append(self.create_random_unit_vector().scaled(size))
        return dna

    def mutate_dna(self, dna):
        i = randint(0, len(dna) - 1)
        size = random() * FORCE_FACTOR
        dna[i] = self.create_random_unit_vector().scaled(size)
        return dna

    def create_individual(self):
        c = Creature()
        c.set_pos(self.launcher.pos.x, self.launcher.pos.y)
        return c

    def evaluate_fitness(self, ind):
        d = ind.pos.distance(self.target.pos)

        # Avoid division by 0.
        if d < 1:
            d = 1

        # Fitness will be between 0 and 1
        fitness = 1 / (d * d)

        # The arrival factor is the arrival time normalized
        # between 0 and 1, where 0 represents the start of
        # the simulation and 1 the end of the simulation.
        if ind.arrival_time is None:
            ind.arrival_time = self.now

        arrival_factor = ind.arrival_time / self.now

        # Special case if individual arrives right away. This can happen for
        # instance if target and launcher are extremeoy close, so it's kind of
        # invalid, so just avoid division by zero.
        if arrival_factor == 0:
            arrival_factor = 1

        if ind.has_crashed():
            # Give more penalty to objects that crashed early
            fitness *= pow(arrival_factor, 3)
        if ind.has_completed():
            # Boost objects that completed early
            fitness /= (pow(arrival_factor, 3))

            if self.best_time is None or ind.arrival_time < self.best_time:
                self.best_time = ind.arrival_time

            self.complete_count += 1
        return fitness

    def create_random_unit_vector(self):
        angle = random() * 2 * pi;
        return Vector2D(cos(angle), sin(angle))

    def check_pos(self, thing, t):
        if thing.pos.x < 0 or thing.pos.x > self.width or thing.pos.y < 0 or thing.pos.y > self.height:
            thing.crash(t)

        if thing.pos.distance(self.target.pos) < thing.radius + self.target.radius:
            thing.complete(t)

        for obstacle in self.obstacles:
            if thing.pos.distance(obstacle.pos) < thing.radius + obstacle.radius:
                thing.crash(t)

        if thing.active:
            self.all_inactive = False

    def update(self, thing, counter, dt):
        thing.update(counter, dt)

    def draw(self, thing):
        thing.draw(self.screen)

    def change_mutation(self, delta):
        self.mutate_index += delta
        self.mutate_index = constrain(self.mutate_index, 0, len(MUTATION_SPEEDS) - 1)
        p = self.engine.set_mutation_probability(MUTATION_SPEEDS[self.mutate_index])
        print('Mutation probability: {:.4f}'.format(p))

    def request_stop(self):
        self.exit_requested = True

    def handle_input(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.request_stop()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.request_stop()
                elif event.key == pygame.K_SPACE:
                    self.clock.toggle_pause()
                elif event.key == pygame.K_m:
                    self.change_mutation(1)
                elif event.key == pygame.K_n:
                    self.change_mutation(-1)
                elif event.key == pygame.K_F5:
                    self.save()
                elif event.key == pygame.K_F9:
                    self.load()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                thing = self.find_thing(event.pos)
                if event.button == LEFT_BUTTON:
                    if thing:
                        self.dragging = thing
                        pos = event.pos
                        self.drag_offset = self.dragging.pos - Vector2D(pos[0], pos[1])
                elif event.button == RIGHT_BUTTON:
                    if thing is None:
                        new_obstacle = Obstacle()
                        new_obstacle.set_pos(event.pos[0], event.pos[1])
                        self.obstacles.append(new_obstacle)
                        self.draggables.append(new_obstacle)
                    else:
                        if thing.removable:
                            self.obstacles.remove(thing)
                            self.draggables.remove(thing)
                elif event.button == SCROLL_UP:
                    if thing is not None:
                        thing.set_radius(constrain(thing.radius + 10, 10, 100))
                elif event.button == SCROLL_DOWN:
                    if thing is not None:
                        thing.set_radius(constrain(thing.radius - 10, 10, 100))

            elif event.type == pygame.MOUSEBUTTONUP:
                self.dragging = None
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    pos = event.pos
                    x = Vector2D(pos[0], pos[1])
                    self.dragging.pos = x + self.drag_offset

                    # Invalidate best time since circumstances have changed.
                    self.best_time = None

    def find_thing(self, pos):
        x = Vector2D(pos[0], pos[1])
        for thing in self.draggables:
            if x.distance(thing.pos) < thing.radius:
                return thing
        return None

    def on_init(self, engine):
        pygame.init()
        self.width = 600
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.target = Target()
        self.engine = engine

        self.launcher = Launcher()
        self.launcher.set_pos(self.width / 2, self.height - 100)

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

        self.draggables.append(self.launcher)
        self.draggables.extend(self.obstacles)
        self.draggables.append(self.target)

        self.font = pygame.font.SysFont('sans', 20)

    def draw_text(self, text, x, y):
        s = self.font.render(text, True, WHITE)
        self.screen.blit(s, (x, y))

    def draw_everything(self, generation):
        self.screen.fill(BLACK)

        for ind in self.engine.population_iterator():
            self.draw(ind)

        for ob in self.obstacles:
            ob.draw(self.screen)

        self.launcher.draw(self.screen)
        self.target.draw(self.screen)

        self.draw_text('m={:.4f}'.format(self.engine.get_mutation_probability()), 4, 4)
        self.draw_text('generation: {}'.format(generation), 4, 24)
        self.draw_text('completed: {}'.format(self.latest_complete_count), 4, 44)
        if self.best_time:
            self.draw_text('best time: {:.3f} s'.format(self.best_time), 4, 64)
        pygame.display.flip()

    def start(self):
        engine.initialize()
        self.complete_count = 0
        self.clock.reset()
        self.clock.start()
        counter = 0
        accumulator = 0.0
        dt = 0.01
        while not self.exit_requested:
            self.all_inactive = True
            self.handle_input()

            if not self.clock.is_paused():
                self.now, frame_time = self.clock.get_time_and_delta()
                if frame_time > 0.25:
                    print("Warning: Frame rate low!")
                    frame_time = 0.25

                accumulator += frame_time

                while accumulator >= dt:
                    for ind in self.engine.population_iterator():
                        self.update(ind, counter, dt)

                    for ind in self.engine.population_iterator():
                        self.check_pos(ind, self.now)

                    accumulator -= dt
                    self.now += dt

                    counter += 1
                    if counter == DNA_SIZE or self.all_inactive:
                        self.engine.evolve()
                        counter = 0
                        self.complete_count = 0
                        self.clock.reset()
                        self.clock.start()
            else:
                time.sleep(0.1)

            self.draw_everything(self.generation)

    def on_new_population(self, generation):
        self.generation = generation

    def save(self):
        data = {'target': self.target,
                'obstacles': self.obstacles}
        with open(STATEFILE, 'wb') as f:
            pickle.dump(data, f)

    def load(self):
        data = None
        try:
            with open(STATEFILE, 'rb') as f:
                data = pickle.load(f)
        except:
            return
        self.target = data['target']
        self.obstacles = data['obstacles']
        self.draggables = []
        self.draggables.append(self.target)
        self.draggables.extend(self.obstacles)
        self.best_time = None

    def on_evaluated(self, generation):
        self.latest_complete_count = self.complete_count
        print("Generation {} end".format(generation))
        print('  Completed: {}'.format(self.complete_count))
        if self.best_time:
            print('  Best time: {:.3f}'.format(self.best_time))


if __name__ == '__main__':
    client = Client()
    engine = gengine.Engine(client)
    client.start()
