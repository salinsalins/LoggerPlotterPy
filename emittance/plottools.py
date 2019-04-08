#!/usr/local/bin/python2.7
# encoding: utf-8
'''
plottools -- shortdesc

plottools is a description

It defines classes_and_methods

@author:     Andrey Sanin

@copyright:  2017 Andrey Sanin. All rights reserved.

@license:    none

@contact:    user_email
@deffield    updated: Updated
'''
def zoplot(axes, value=0.0, color='k'):
    #axes = mplWidget.canvas.ax
    xlim = axes.get_xlim()
    axes.plot(xlim, [value, value], color=color)
    axes.set_xlim(xlim)

def voplot(axes, value=0.0, color='k'):
    #axes = self.mplWidget.canvas.ax
    ylim = axes.get_ylim()
    axes.plot([value, value], ylim, color=color)
    axes.set_ylim(ylim)
