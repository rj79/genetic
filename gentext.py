#!/usr/bin/env python3
import random
import string
import time

MUTATION_P = 0.01

def create_random_gene():
    return random.choice(string.ascii_lowercase + ' ')
    
def create_random_individual(length):
    genes = []
    for i in range(length):
        genes += create_random_gene()
    return Individual(genes)

class Individual:
    def __init__(self, genes=None):
        if genes is None:
            self.genes = []
        else:
            self.genes = genes[:]
        self.fitness = 0
        self.selection_limit = 0

    def get_genes(self):
        return self.genes
    
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
                new_genes.append(create_random_gene())
            else:
                new_genes.append(self.genes[i])
        self.genes = new_genes
        
    def __str__(self):
        return '(I {} {})'.format(self.genes, self.fitness)

    
class Evaluator:
    def __init__(self, target):
        self.target = target
        self.done = False

    def evaluate(self, ind):
        fitness = 1
        genes = ind.get_genes()
        for i in range(len(genes)):
            if genes[i] == self.target[i]:
                fitness *= 4
        ind.set_fitness(fitness)

        if ind.get_genes() == self.target:
            self.done = True
            
        return fitness

    def finished(self):
        return self.done


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
        
class BreakpointCombinator:
    def combine(self, p1, p2):
        combined_genes = []
        p1g = p1.get_genes()
        p2g = p2.get_genes()
        n = random.randint(0, len(p1g) - 1)
        return p1g[0:n] + p2g[n:]

    
class Population:
    def __init__(self, size, isize, evaluator):
        self.individuals = []
        self.evaluator = evaluator
        for i in range(size):
            self.individuals.append(create_random_individual(isize))

    def evaluate_all(self, engine):
        sum = 0
        max_fitness = 0
        for ind in self.individuals:
            fitness = self.evaluator.evaluate(ind)
            sum += fitness
            ind.set_selection_limit(sum)
            
            if fitness > max_fitness:
                max_fitness = fitness

        engine.set_fitness_sum(sum)

    def finished(self):
        return evaluator.finished()
    
    def set_individuals(self, individuals):
        self.individuals = individuals[:]

    def select_individual(self, p):
        for ind in self.individuals:
            if p < ind.get_selection_limit():
                return ind
        raise RuntimeException()

    def get_size(self):
        return len(self.individuals)

    def __str__(self):
       return '<P {}>'.format(', '.join([str(ind) for ind in self.individuals])) 
    
class Engine:
    def __init__(self, population):
        self.generation = 1
        self.fitness_sum = 0
        self.population = population
        self.done = False
        self.combinator = ElementWiseCombinator()

    def select_parent(self):
        p = random.random() * self.fitness_sum
        return population.select_individual(p)

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
            new_individual = Individual(new_genes)
            new_individual.mutate()
            print('{} x {} -> {}'.format(str(p1), str(p2), str(new_individual)))
            new_individuals.append(new_individual)

        self.population.set_individuals(new_individuals)            

    def set_combinator(self, combinator):
        self.combinator = combinator

    def run(self):
        fitness = 0
        self.done = False
        while not self.done:
            print('Generation {}'.format(self.generation))
            self.population.evaluate_all(self)
            self.evolve()
            self.generation += 1
            if self.population.finished():
                break
#            time.sleep(1)


genes = list('win')
evaluator = Evaluator(genes)
combinator = BreakpointCombinator()
population = Population(8, len(genes), evaluator)
engine = Engine(population)
#engine.set_combinator(combinator)
engine.run()
