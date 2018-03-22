# coding: utf-8
'''
Created on Aug 21, 2017

@author: sanin
'''
import numpy as np
import findRegions

def removeInersections(self, y1, y2, index):
    # calculate relative first derivatives
    d1 = np.diff(y1)
    d1 = np.append(d1, d1[-1])
    d2 = np.diff(y2)
    d2 = np.append(d2, d2[-1])
    regout = []
    reg = findRegions(index)
    #print('Initial regions  %s'%str(reg))
    for r in reg:
        if y1[r[0]] > y2[r[0]] and y1[r[1]-1] < y2[r[1]-1]:
            if np.all(d1[r[0]:r[1]]*d2[r[0]:r[1]] < 0.0):
                continue
        if y1[r[0]] < y2[r[0]] and y1[r[1]-1] > y2[r[1]-1]:
            if np.all(d1[r[0]:r[1]]*d2[r[0]:r[1]] < 0.0):
                continue
        regout.append(r)
    #print('Filtered regions %s'%str(regout))
    return regout

