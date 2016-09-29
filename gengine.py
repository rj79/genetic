#!/usr/bin/env python3
import random
import string
import time

def constrain(num, minimum, maximum):
    if num < minimum:
        num = minimum
    if num > maximum:
        num = maximum
    return num

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
        self.generation = 1
        self.population = None
        self.done = False
        self.combinator = ElementWiseCombinator()
        self.started = False
        self.pop_size = 1
        self.gene_size = 1
        self.mutate_probability = 0.01

    def get_configuration(self):
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

    def set_mutation_probability(self, p):
        self.mutate_probability = limit(p, 0, 1)

    def get_gene_size(self):
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
        self.combinator = combinator

    def for_each_custom_call(self, fn):
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

    def start(self):
        if not self.started:
            self.started = True
            self.get_configuration()
            self._populate_random(self.pop_size, self.gene_size)
            self.client.on_generation_begin(self.generation)

    def run_once(self):
        if not self.started:
            raise RuntimeError('You must start the engine first')

        self._evaluate_all(self)
        self.client.on_generation_end(self.generation)
        self._evolve()
        self.generation += 1
        self.client.on_generation_begin(self.generation)

    def run(self):
        self.done = False
        while not self.done:
            self.run_once()
            if self.client.is_stop_requested():
                break


class BaseClient:
    """
    Clients of the engine should subclass and override the
    methods of this class.
    For meaningful operation, at least the following need to be
    overriden:
      * create_gene
      * create_individual
      * evaluate_fitness
    """
    def get_configuration(self):
        """
        Should return a dictionary with configuration options.
        If an empty dictionary is returned, the default configuration
        is used.
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

    def on_generation_begin(self, generation):
        """
        Called by the engine when a new generation starts.
        """
        pass

    def on_generation_end(self, generation):
        """
        Called by the engine when a generation ends.
        """
        pass

    def evaluate_fitness(self, ind):
        """
        Should calculate and return the fitness of the individual.
        """
        raise NotImplementedError('You must sublcass BaseClient')

    def is_stop_requested(self):
        """
        Called by the engine during run() to determine if the
        simulation should stop.
        """
        return False


class ExampleClient(BaseClient):
    """
    A very simple client that uses the engine.
    """

    def __init__(self, target_text):
        super().__init__()
        self.target = list(target_text)
        self.solution_found = False
        self.generation = 0

    def get_configuration(self):
        return {'population_size': 8,
                'dna_size': len(self.target)}

    def on_generation_begin(self, generation):
        self.generation = generation

    def on_generation_end(self, generation):
        pass

    def create_gene(self):
        return random.choice(string.ascii_lowercase + ' ')

    def create_individual(self):
        return NullIndividual()

    def is_stop_requested(self):
        return self.solution_found

    def evaluate_fitness(self, ind):
        fitness = 2
        genes = ind.get_genes()
        for i in range(len(genes)):
            if genes[i] == self.target[i]:
                fitness *= fitness

        if ind.get_genes() == self.target:
            self.solution_found = True
            print('Found solution {} in {} generations.'.format(self.target, self.generation))

        return fitness

if __name__ == '__main__':
    client = ExampleClient('to be or not to be')
    engine = Engine(client)
    engine.start()
    engine.run()
