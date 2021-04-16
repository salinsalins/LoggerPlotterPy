# coding: utf-8
'''
Created on 16 april 2021
@author: Sanin
'''

from PyQt5 import QtGui
#from PyQt5 import QtWidgets as QtGui
import pyqtgraph
#from pyqtgraph import PlotWidget as Figure
bgc = '#1d648d'
pyqtgraph.setConfigOption('background', '#1d648d')

class MplWidget(pyqtgraph.PlotWidget):
    def __init__(self, parent=None, height=300, width=300):
        super().__init__()
        self.canvas = axes_adapter(self)
        self.canvas.ax = axes_adapter(self)
        self.ntb = ToolBar()

        self.setMinimumHeight(height)
        self.setMinimumWidth(width)

class axes_adapter(pyqtgraph.PlotWidget):
    def __init__(self, item):
        self.item = item
        super().__init__()
        pass

    def grid(self, val=True):
        self.item.getPlotItem().showGrid(val, val)

    def set_title(self, val=''):
        self.item.getPlotItem().setTitle(val)

    def set_xlabel(self, val=''):
        pass

    def set_ylabel(self, val=''):
        pass

    def draw(self, val=''):
        pass

    def plot(self, x, y, color='#ffffff'):
        self.item.plot(x, y, pen=color)


class ToolBar:
    def __init__(self, *args):
        pass

    def hide(self, *args):
        pass

    def show(self, *args):
        pass

    def setIconSize(self, *args):
        pass

    def setFixedSize(self, *args):
        pass