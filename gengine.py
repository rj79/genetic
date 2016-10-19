#!/usr/bin/env python3
import random
import string
import time
from utils import constrain


class ElementWiseCombinator:
    """
    Combinator that for each gene randomly either takes it from parent 1 or
    parent 2.
    """
    def combine(self, p1, p2):
        combined_genes = []
        p1g = p1.get_dna()
        p2g = p2.get_dna()
        for g1, g2 in zip(p1g, p2g):
            if random.random() < 0.5:
                combined_genes.append(g1)
            else:
                combined_genes.append(g2)
        return combined_genes


class RandomBreakpointCombinator:
    """
    Combinator that takes a sequence of the DNA from parent 1 and the rest of
    the sequence from parent 2.
    """
    def combine(self, p1, p2):
        combined_genes = []
        p1g = p1.get_dna()
        p2g = p2.get_dna()
        n = random.randint(0, len(p1g) - 1)
        return p1g[0:n] + p2g[n:]


class RandomParentCombinator:
    """
    Combinator that selects the complete DNA from either parent 1 or 2.
    """
    def combine(self, p1, p2):
        if random.random() < 0.5:
            return p1.get_dna()
        else:
            return p2.get_dna()


class BaseIndividualMixin:
    """
    Objects that have a DNA and are part of the simulation should inherit or
    mixin this class.
    """
    def __init__(self):
        self.dna = None
        self.fitness = 0

    def set_fitness(self, fitness):
        self.fitness = fitness

    def get_fitness(self):
        return self.fitness

    def set_dna(self, dna):
        self.dna = dna

    def get_dna(self):
        return self.dna


class Population:
    def __init__(self, engine):
        if engine is None:
            raise RuntimeError('Engine not set')
        self.engine = engine
        self.individuals = []

    def add(self, ind):
        self.individuals.append(ind)

    def iterator(self):
        return iter(self.individuals)

    def set_individuals(self, individuals):
        self.individuals = list(individuals)

    def select_individual(self):
        """
        Select an individual based on fitness distribution
        """
        # Special handling if all individuals have zero fitness
        # In that case, just pick any
        allzero = True
        for ind in self.individuals:
            if ind.get_fitness() > 0:
                allzero = False

        if allzero:
            return self.individuals[random.randint(0, len(self.individuals) - 1)]

        # Monte-Carlo style accept-reject algorithm
        # Assumes that fitness is normalized between 0 and 1
        timeout = 1000000
        while timeout > 0:
            i = random.randint(0, len(self.individuals) - 1)
            u = random.random()
            if u <= self.individuals[i].fitness:
                return self.individuals[i]
            timeout -= 1
        # We can get here in case all individuals have 0 fitness
        # so just pick any.
        return self.individuals[random.randint(0, len(self.individuals) - 1)]

    def get_size(self):
        return len(self.individuals)

    def __str__(self):
       return '<P {}>'.format(', '.join([str(ind) for ind in self.individuals]))


class Engine:
    def __init__(self, client):
        if client is None:
            raise RuntimeError('Client must be set')
        # TODO: Check that client has the right callable functions
        # ... code here ...

        self.client = client
        self.generation = 1
        self.population = None
        self.combinator = ElementWiseCombinator()
        self.pop_size = 3
        self.mutate_probability = 0.01
        self.initialized = False

    def _get_configuration(self):
        config = self.client.get_configuration()
        # TODO: Rewrite this more elegantly and less verbose ...
        try:
            self.pop_size = config['population_size']
        except:
            pass

        try:
            self.mutate_probability = config['mutation_p']
        except:
            pass

    def set_mutation_probability(self, p):
        """
        Set the probability of gene mutation. p should be in the range [0, 1]
        """
        self.mutate_probability = constrain(p, 0, 1)
        return self.mutate_probability

    def get_mutation_probability(self):
        """
        Returns the current mutation probability
        """
        return self.mutate_probability

    def _populate(self, pop_size):
        if self.population is not None:
            raise RuntimeError('Populate can only be called once')

        self.population = Population(self)

        for i in range(pop_size):
            dna = self.client.create_dna()
            ind = self.client.create_individual()
            ind.set_dna(dna)
            self.population.add(ind)

    def _select_parents(self):
        p1 = self.population.select_individual()
        p2 = self.population.select_individual()
        return p1, p2

    def _mutate(self, dna, probability):
        new_dna = list(dna)
        for i in range(len(dna)):
            if random.random() < probability:
                new_dna = self.client.mutate_dna(new_dna)
        return new_dna

    def _evolve(self):
        new_individuals = []

        for i in range(self.population.get_size()):
            p1, p2 = self._select_parents()
            new_dna = self.combinator.combine(p1, p2)
            new_dna = self._mutate(new_dna, self.mutate_probability)
            new_individual = self.client.create_individual()
            new_individual.set_dna(new_dna)
            new_individuals.append(new_individual)

        self.population.set_individuals(new_individuals)

    def set_combinator(self, combinator):
        """
        A client can set a custom combinator object. The combinator object
        must have a combine() method which the engine calls to combie the DNA
        of two parents and returns a combined DNA.
        The combine() function should take two objects of that inherit from
        BaseIndividualMixin and return a list of genes.
        """
        self.combinator = combinator

    def population_iterator(self):
        """
        Returns an iterator to the list of individuals in the population.
        The types of each individual will match whatever is returned by
        client.create_individual
        """
        return self.population.iterator()

    def _evaluate_all(self, engine):
        fitness_list = []
        max_fitness = 0

        # Collect fitness value for each individual as well as
        # find maximum fitness in the population
        for ind in self.population_iterator():
            fitness = self.client.evaluate_fitness(ind)

            if fitness < 0:
                raise RuntimeError('Fitness can not be negative')

            fitness_list.append(fitness)

            if fitness > max_fitness:
                max_fitness = fitness

        # Avoid division by zero below
        if max_fitness == 0:
            max_fitness = 1

        # Normalize fitness to range [0, 1]
        i = 0
        for ind in self.population_iterator():
            fitness_list[i] /= max_fitness
            ind.set_fitness(fitness_list[i])
            i += 1

    def initialize(self):
        """
        The application should call this prior to calling any other method in
        the engine. It will call on_init() and generate an initial population.
        """
        if not self.initialized:
            self.initialized = True
            self.client.on_init(self)
            self._get_configuration()
            self._populate(self.pop_size)
            self.client.on_new_population(self.generation)
        else:
            raise RuntimeError("Engine already initialized")


    def evolve(self):
        """
        The client should call this every time it wishes to have a new
        generation of the population generated.
        """
        if not self.initialized:
            raise RuntimeError("Engine not initialized")

        self._evaluate_all(self)
        self.client.on_evaluated(self.generation)
        self._evolve()
        self.generation += 1
        self.client.on_new_population(self.generation)


class BaseClient:
    """
    Clients of the engine should subclass and override the methods of this
    class. For meaningful operation, at least the following need to be
    overriden:
      * create_dna
      * create_individual
      * mutate
      * evaluate_fitness
    """
    def get_configuration(self):
        """
        Should return a dictionary with configuration options.
        If an empty dictionary is returned, the default configuration is used.
        """
        return {}

    def create_dna(self):
        """
        Called by the engine when it needs to generate a new dna.
        Should return a list of genes.
        """
        raise NotImplementedError('You must implement create_dna')

    def mutate_dna(self, dna):
        """
        Called by the engine when it needs to mutate dna.
        Should return a mutated version of the dna
        """
        raise NotImplementedError('You must implement mutate_dna')

    def create_individual(self):
        """
        Should return a subclass of BaseIndividualMixin.
        """
        raise NotImplementedError('You must implement create_individual')

    def on_init(self, engine):
        """
        Called by the engine before any other function in the client is called.
        This allows you to do any setup before the simulation starts.
        The engine object itself is passed as a parameter.
        """
        pass

    def on_new_generation(self, generation):
        """
        Called by the engine when a new generation is ready.
        """
        pass

    def on_evaluated(self, generation):
        """
        Called by the engine when all individuals' fitness has been evaluated
        in the current generation. This allows the client to calculate
        statistics, show progress and similar.
        """
        pass

    def evaluate_fitness(self, ind):
        """
        Should calculate and return the fitness of the individual.
        """
        raise NotImplementedError('You must implement evaluate_fitness')


"""
The following part of the file contains a small example and is not part of the
library itself.
"""
class ExampleClient(BaseClient):
    """
    A very simple client that uses the engine.
    """

    def __init__(self, target_text):
        super().__init__()
        self.engine = None
        self.target = list(target_text)
        self.solution_found = False
        self.generation = 0

    def on_init(self, engine):
        self.engine = engine

    def get_configuration(self):
        return {'population_size': 8}

    def on_new_population(self, generation):
        self.generation = generation

    def create_dna(self):
        dna = []
        for i in range(len(self.target)):
            dna.append(random.choice(string.ascii_lowercase + ' '))
        return dna

    def create_individual(self):
        return BaseIndividualMixin()

    def mutate_dna(self, dna):
        i = random.randint(0, len(dna) - 1)
        dna[i] = random.choice(string.ascii_lowercase + ' ')
        return dna

    def evaluate_fitness(self, ind):
        fitness = 2
        genes = ind.get_dna()
        print(genes)
        for i in range(len(genes)):
            if genes[i] == self.target[i]:
                fitness *= fitness

        if ind.get_dna() == self.target:
            self.solution_found = True
            print('Found solution {} in {} generations.'.format(self.target, self.generation))

        return fitness

    def is_done(self):
        return self.solution_found

if __name__ == '__main__':
    client = ExampleClient('to be or not to be')
    engine = Engine(client)
    engine.initialize()
    while not client.is_done():
        engine.evolve()
