
import numpy as np

def myDistFunc(x):
    y = 1 + np.sign(x / 10 + 50 * np.sin(2 * np.pi * x / 200) * np.tanh(x / 100))
    return y
    