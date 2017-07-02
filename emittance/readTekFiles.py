# coding: utf-8
'''
Created on 31 мая 2017 г.

@author: Sanin
'''
import os
import glob
import numpy as np
from my_isfread import my_isfread as isfread

def readTekFiles(folder, mask='*.isf'):
    fileNames = glob.glob(os.path.join(str(folder), mask))
    nx = len(fileNames)
    if nx <= 0 :
        return None, []
    # Determine Y size of data for one scan - ny
    x,y,h = isfread(fileNames[0])
    ny = len(y)
    # Define Data Array
    data  =  np.zeros((nx, ny), dtype=np.float64)
    # Read Data Array
    for i in range(nx) :
        x,y,h = isfread(fileNames[i])
        data[i,:] = y[:]
    return data, fileNames
