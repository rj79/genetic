#!/usr/bin/env python3
import random
import string
import time
from utils import constrain

class NullIndividual:
    def __init__(self):
        pass

    def set_individual(self, ind):
        pass

    def action(self):
        pass

class Individual:
    def __init__(self, engine=None, genes=None):

        self.custom_object = None

        if engine is None:
            raise RuntimeError('Engine not set')

        self.engine = engine
        if genes is None:
            self.genes = []
        else:
            self.genes = genes[:]
        self.fitness = 0

    def get_genes_length(self):
        return len(self.genes)

    def set_custom_object(self, obj):
        self.custom_object = obj

    def get_genes(self):
        return self.genes

    def get_gene(self, index):
        return self.genes[index]

    def set_fitness(self, fitness):
        if fitness < 0 or fitness > 1:
            raise RuntimeError('Fitness must be in range [0, 1] was', fitness)
        self.fitness = fitness

    def mutate(self, probability):
        new_genes = []
        for i in range(len(self.genes)):
            if random.random() < probability:
                new_genes.append(self.engine.client.create_gene())
            else:
                new_genes.append(self.genes[i])
        self.genes = new_genes

    def __str__(self):
        return '(I {} {})'.format(', '.join([str(x) for x in self.genes]), self.fitness)


class ElementWiseCombinator:
    def combine(self, p1, p2):
        combined_genes = []
        p1g = p1.get_genes()
        p2g = p2.get_genes()
        for i in range(len(p1g)):
            if random.random() < 0.5:
                combined_genes.append(p1g[i])
            else:
                combined_genes.append(p2g[i])
        return combined_genes


class RandomBreakpointCombinator:
    def combine(self, p1, p2):
        combined_genes = []
        p1g = p1.get_genes()
        p2g = p2.get_genes()
        n = random.randint(0, len(p1g) - 1)
        return p1g[0:n] + p2g[n:]


class Population:
    def __init__(self, engine):
        if engine is None:
            raise RuntimeError('Engine not set')
        self.engine = engine
        self.individuals = []

    def add(self, ind):
        self.individuals.append(ind)

    def get_individuals(self):
        return self.individuals

    def set_individuals(self, individuals):
        self.individuals = individuals[:]

    def select_individual(self):
        """
        Select an individual based on fitness distribution
        """
        # Special handling if all individuals have zero fitness
        # In that case, just pick any
        allzero = True
        for ind in self.individuals:
            if ind.fitness > 0:
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

    def for_each_custom_call(self, fn):
        for ind in self.individuals:
            fn(ind.custom_object)

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
        self.stop_requested = False
        self.generation = 1
        self.population = None
        self.combinator = ElementWiseCombinator()
        self.pop_size = 3
        self.gene_size = 1
        self.mutate_probability = 0.01

    def _get_configuration(self):
        config = self.client.get_configuration()
        # TODO: Rewrite this more elegantly
        try:
            self.pop_size = config['population_size']
        except:
            pass

        try:
            self.gene_size = config['dna_size']
        except:
            pass

        try:
            self.mutate_probability = config['mutation_p']
        except:
            pass

    def request_stop(self):
        """
        A client can call this method to request that the engine stops.
        """
        self.stop_requested = True

    def set_mutation_probability(self, p):
        """
        Set the probability of gene mutation. p should be in the range [0, 1]
        """
        self.mutate_probability = constrain(p, 0, 1)
        return self.mutate_probability

    def get_mutation_probability(self):
        return self.mutate_probability

    def get_gene_size(self):
        """
        Returns the number of genes in each individual's DNA
        """
        return self.gene_size

    def _populate_random(self, pop_size, gene_size):
        if self.population is not None:
            raise RuntimeError('Populate can only be called once')

        self.population = Population(self)
        self.gene_size = gene_size

        for i in range(pop_size):
            genes = []
            for j in range(gene_size):
                genes.append(self.client.create_gene())
            self.population.add(self._create_individual(genes))

    def _create_individual(self, new_genes):
        obj = self.client.create_individual()
        ind = Individual(self, new_genes)
        ind.set_custom_object(obj)
        obj.set_individual(ind)
        return ind

    def _select_parents(self):
        p1 = self.population.select_individual()
        p2 = self.population.select_individual()
        return p1, p2

    def _evolve(self):
        new_individuals = []

        for i in range(self.population.get_size()):
            p1, p2 = self._select_parents()
            new_genes = self.combinator.combine(p1, p2)
            new_individual = self._create_individual(new_genes)
            new_individual.mutate(self.mutate_probability)
            new_individuals.append(new_individual)

        self.population.set_individuals(new_individuals)

    def set_combinator(self, combinator):
        """
        A client can set a custom combinator object. The combinator object
        must have a combine() method which the engine calls to combie two
        parents to create a new individual for the next generation.
        The combine() function should take to parent individuals and return a
        vector of genes.
        """
        self.combinator = combinator

    def for_each_custom_call(self, fn):
        """
        A client can use this to call a function for each individual in the
        population. The individual is sent as parameter.
        """
        self.population.for_each_custom_call(fn)

    def _evaluate_all(self, engine):
        fitness_list = []
        max_fitness = 0

        # Collect fitness value for each individual as well as
        # find maximum fitness in the population
        for ind in self.population.get_individuals():
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
        for ind in self.population.get_individuals():
            fitness_list[i] /= max_fitness
            ind.set_fitness(fitness_list[i])
            i += 1
        #print('\n'.join(['{:.5f}'.format(x) for x in reversed(sorted(fitness_list))]))

    def run(self):
        """
        This is the entry point for the simulation.
        """
        self.client.on_init(self)
        self._get_configuration()
        self._populate_random(self.pop_size, self.gene_size)
        while True:
            self.client.on_new_generation(self.generation)
            self._evaluate_all(self)
            self.client.on_evaluated(self.generation)
            if self.stop_requested:
                break
            self._evolve()
            self.generation += 1

class BaseClient:
    """
    Clients of the engine should subclass and override the methods of this
    class. For meaningful operation, at least the following need to be
    overriden:
      * create_gene
      * create_individual
      * evaluate_fitness
    """
    def get_configuration(self):
        """
        Should return a dictionary with configuration options.
        If an empty dictionary is returned, the default configuration is used.
        """
        return {}

    def create_gene(self):
        """
        Called by the engine when it needs to generate a gene.
        Should return a single gene.
        """
        raise NotImplementedError('You must subclass BaseClient')

    def create_individual(self):
        """
        Should return an object that uses the dna.
        """
        raise NotImplementedError('You must subclass BaseClient')

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
        Implement your simulation loop here. Return when you have finished
        simulating this generation. You can have your event handling code in
        here too in case of interactive applications.
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
        raise NotImplementedError('You must sublcass BaseClient')


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
        return {'population_size': 8,
                'dna_size': len(self.target)}

    def on_new_generation(self, generation):
        self.generation = generation

    def create_gene(self):
        return random.choice(string.ascii_lowercase + ' ')

    def create_individual(self):
        return NullIndividual()

    def evaluate_fitness(self, ind):
        fitness = 2
        genes = ind.get_genes()
        for i in range(len(genes)):
            if genes[i] == self.target[i]:
                fitness *= fitness

        if ind.get_genes() == self.target:
            self.solution_found = True
            self.engine.request_stop()
            print('Found solution {} in {} generations.'.format(self.target, self.generation))

        return fitness

if __name__ == '__main__':
    client = ExampleClient('to be or not to be')
    engine = Engine(client)
    engine.run()
