import numpy as np


def db2power(x):
    return np.power(10.0, x / 10.0)


def power2db(x):
    return 10.0 * np.log10(x)


def amplitude2db(x):
    return 20.0 * np.log10(x)
