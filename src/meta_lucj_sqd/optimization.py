import numpy as np


def spsa_step(parameters, plus_value, minus_value, direction, iteration, config):
    c = config['c'] / (iteration + 1) ** config['gamma']
    a = config['a'] / (iteration + 1 + config['stability']) ** config['alpha']
    gradient = (plus_value - minus_value) / (2 * c) * direction
    step = -a * gradient
    norm = np.linalg.norm(step)
    if norm > config['max_step_norm']:
        step *= config['max_step_norm'] / norm
    return parameters + step
