#!/usr/bin/env python3
import random
import string
import time

MUTATION_P = 0.01


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
        self.selection_limit = 0

    def get_genes_length(self):
        return len(self.genes)

    def custom_action():
        self.custom_object.action()

    def set_custom_object(self, obj):
        self.custom_object = obj

    def get_genes(self):
        return self.genes

    def get_gene(self, index):
        return self.genes[index]

    def set_fitness(self, fitness):
        self.fitness = fitness

    def set_selection_limit(self, limit):
        self.selection_limit = limit

    def get_selection_limit(self):
        return self.selection_limit

    def mutate(self):
        new_genes = []
        for i in range(len(self.genes)):
            if random.random() < MUTATION_P:
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

    def custom_action(self):
        pass
        #for ind in self.individuals:
        #   ind.custom_object.action(cust)

    def get_individuals(self):
        return self.individuals

    def set_individuals(self, individuals):
        self.individuals = individuals[:]

    def select_individual(self, p):
        for ind in self.individuals:
            if p < ind.get_selection_limit():
                return ind
        raise RuntimeException()

    def for_each_custom_call(self, clbl):
        for ind in self.individuals:
            clbl(ind.custom_object)

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
        self.gene_size = 0
        self.generation = 1
        self.fitness_sum = 0
        self.population = None
        self.done = False
        self.combinator = ElementWiseCombinator()

    def get_gene_size(self):
        return self.gene_size

    def populate_random(self, pop_size, gene_size):
        if self.population is not None:
            raise RuntimeError('Populate can only be called once')

        self.population = Population(self)
        self.gene_size = gene_size

        for i in range(pop_size):
            genes = []
            for j in range(gene_size):
                genes.append(self.client.create_gene())
            self.population.add(self.create_individual(genes))

    def create_individual(self, new_genes):
        obj = self.client.create_individual()
        ind = Individual(self, new_genes)
        ind.set_custom_object(obj)
        obj.set_individual(ind)
        return ind

    def select_parent(self):
        p = random.random() * self.fitness_sum
        return self.population.select_individual(p)

    def set_fitness_sum(self, sum):
        self.fitness_sum = sum

    def select_parents(self):
        p1 = self.select_parent()
        p2 = self.select_parent()
        while p1 == p2:
            p2 = self.select_parent()
        return p1, p2

    def evolve(self):
        new_individuals = []

        for i in range(self.population.get_size()):
            p1, p2 = self.select_parents()
            new_genes = self.combinator.combine(p1, p2)
            new_individual = self.create_individual(new_genes)
            new_individual.mutate()
            #print('{} x {} -> {}'.format(str(p1), str(p2), str(new_individual)))
            new_individuals.append(new_individual)

        self.population.set_individuals(new_individuals)
        #for individual in new_individuals:
        #    print(individual, individual.custom_object)

    def set_combinator(self, combinator):
        self.combinator = combinator

    def for_each_custom_call(self, clbl):
        self.population.for_each_custom_call(clbl)

    def evaluate_all(self, engine):
        sum = 0
        max_fitness = 0
        for ind in self.population.get_individuals():
            fitness = self.client.evaluate(ind)
            sum += fitness
            ind.set_selection_limit(sum)

            if fitness > max_fitness:
                max_fitness = fitness

        self.set_fitness_sum(sum)

    def run_once(self):
        self.client.on_generation_begin(self.generation)
        #self.population.custom_action()
        self.evaluate_all(self)
        self.evolve()
        self.generation += 1

    def run(self):
        self.done = False
        while not self.done:
            self.run_once()
            if self.client.is_stop_requested():
                break


class BaseClient:
    def on_generation_begin(self, generation):
        pass

    def evaluate(self, ind):
        raise NotImplementedError('You must sublcass BaseClient')

    def create_gene(self):
        raise NotImplementedError('You must subclass BaseClient')

    def create_individual(self):
        raise NotImplementedError('You must subclass BaseClient')

    def is_stop_requested(self):
        return False


class ExampleClient(BaseClient):
    def __init__(self, target_text):
        super().__init__()
        self.target = list(target_text)
        self.solution_found = False

    def on_generation_begin(self, generation):
        print('Generation {}'.format(generation))

    def create_gene(self):
        return random.choice(string.ascii_lowercase + ' ')

    def create_individual(self):
        return NullIndividual()

    def is_stop_requested(self):
        return self.solution_found

    def evaluate(self, ind):
        fitness = 1
        genes = ind.get_genes()
        for i in range(len(genes)):
            if genes[i] == self.target[i]:
                fitness *= 4
        ind.set_fitness(fitness)

        if ind.get_genes() == self.target:
            self.solution_found = True

        return fitness


if __name__ == '__main__':
    client = ExampleClient('win')
    engine = Engine(client)
    engine.populate_random(8, 3)
    engine.run()
