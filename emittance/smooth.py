# coding: utf-8
'''
Created on 31 мая 2017 г.

@author: Sanin
'''
import numpy as np


def smooth(y, n):
    if n < 2 :
        return y
    cumsum = np.cumsum(np.insert(y, 0, 0.0)) 
    n2 = int(n/2) + int(n%2)
    y[n2:-n2+1] = (cumsum[n:] - cumsum[:-n]) / n
    for i in range(n2):
        y[i] = cumsum[i+n2] / (i + n2 + 1)
    for i in range(n2):
        y[-(i+1)] = (cumsum[-1]-cumsum[-i-n2-1]) / (i + n2)
    return y

def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0)) 
    return (cumsum[N:] - cumsum[:-N]) / N
