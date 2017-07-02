# coding: utf-8
'''
Created on 27 June 2017.

@author: Sanin
'''
import numpy as np

def gaussfit(x, y, arg=None):
    if arg is None:
        arg = x
    ysum = np.sum(y)
    x0 = np.sum(x*y)/ysum
    width = np.sqrt(np.abs(np.sum((x-x0)**2*y)/ysum))
    y1 = np.exp(-(x-x0)**2/(2*width**2))
    w = y1
    #m1 = np.abs(x-x0) < (4.0 * width)
    m3 = y > 0.1 * y.max()
    #m3 = np.logical_and(m1, m2)
    a = np.average(y[m3]/y1[m3], weights=w[m3])
    #a = y.max()
    return a*np.exp(-(arg-x0)**2/(2*width**2))
