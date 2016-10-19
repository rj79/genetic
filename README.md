# About
A genetic algorithm engine written in Python inspired by [The Coding Rainbow](https://www.youtube.com/user/shiffman).

# Example application
An interactive example application that uses the engine is also included.

**Controls**
* Pause the simulation by pressing SPACE
* Move the green target and the red obstacles using the mouse
* Create a new obstacle by right-clicking in an empty space
* Remove an obstacle by right-clicking on it
* Change the size of an obstacle or the target using the scroll wheel
* Increase or decrease the mutation probability by pressing M or N
* Store the obstacle and target to file pressing F4
* Load the obstacle and target from file pressing F9

# Running the examples
Just type make to run the interactive example application.

gengine.py itself includes a super stripped down example without
a gui. Type 'make test' or 'python3 gengine.py' to run it.

# Using the engine
The engine performs the generic task of combining the genes of parents and
mutating genes of individuals. It does not know however how to create or
interpret the genes. Nor does it know how to evaluate the fitness of an
individual. These are all things that are unique for each application and
therefore you need to define.

The way to do this is to create a custom client class which is a subclass of
engine.BaseClient in which you define the missing pieces. During operation,
the engine will fire callbacks to the client code.

You will have to create a subclass of BaseIndividualMixin and return
objects of that type from your client's create_individual method.
To kick off the simulation, pass the client to the engine's constructor and
call engine.initialize(). This will create an initial population.
You can then use engine.population_iterator() to perform your simulation and
whenever you want to have a new generation of the population, call
engine.evolve()

There are a couple of key methods the custom client class has to implement:
* create_dna(): This factory method should create a list of gene. A gene could
be any object - it is up to you to define the interpretation of the gene.
The engine does not know or care.
* create individual(): This is a factory method that allows you to create an
individual. The object returned should be a subclass of BaseIndividualMixin.
* on_init(): When you initialize the engine, it will will call you back with
this method once before doing anything else. It allows you to do any
initialization before the simulation starts.
* evaluate_fitness(): The engine calls this method for each individual for each
generation. This happens after on_new_generation() has returned. You should
calculate a fitness value based on the unique critera for your application and
return it. The fitness value must be a non negative number. The greater the
fitness value, the greater the chance the engine will pick that individual as a
parent for the next iteration.

You also likely want to override get_configuration(), which
should return a dictionary with configuration key/value pairs. If an
empty dictionary is returned, default values are used. Configuration keys are:
  * population_size: An integer representing the number of individuals in the population.
  * mutation_p: The probability that a gene mutates between generations.

# Links
Related Coding Rainbow episodes:
* [Smart Rockets Coding Challenge](https://www.youtube.com/watch?v=bGz7mv2vD6g)
* [Genetic Algorithm: Fitness, Genotype vs Phenotype](https://www.youtube.com/watch?v=_of6UVV4HGo)
* [Genetic Algorithm: Improved Fitness Function](https://www.youtube.com/watch?v=HzaLIO9dLbA)
