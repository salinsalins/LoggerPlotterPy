# coding: utf-8
'''
Created on 16 april 2021
@author: Sanin
'''

from PyQt5 import QtGui
#from PyQt5 import QtWidgets as QtGui
import pyqtgraph
#from pyqtgraph import PlotWidget as Figure

class MplWidget(pyqtgraph.PlotWidget):
    def __init__(self, parent=None, height=300, width=300):
        # initialization of Qt MainWindow widget
        QtGui.QWidget.__init__(self, parent)

        self.ntb = ToolBar()
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)

class ToolBar():
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