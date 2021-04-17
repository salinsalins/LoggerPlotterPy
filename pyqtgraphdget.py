# coding: utf-8
'''
Created on 16 april 2021
@author: Sanin
'''

import pyqtgraph
pg = pyqtgraph
from pyqtgraph.Qt import QtCore

#pyqtgraph.setConfigOption('background', '#1d648d')
pyqtgraph.setConfigOption('background', 'w')
pyqtgraph.setConfigOption('foreground', 'k')
pyqtgraph.setConfigOption('antialias', True)
pyqtgraph.setConfigOption('leftButtonPan', False)


class CustomViewBox(pyqtgraph.ViewBox):
    def __init__(self, *args, **kwds):
        pyqtgraph.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)
        self.setBackgroundColor('#1d648da0')
        #self.setBorder(pen=('green', 5))

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            if ev.double():
                pyqtgraph.ViewBox.mouseClickEvent(self, ev)
            else:
                self.autoRange()

    def mouseDragEvent(self, ev, **kwargs):
        if ev.button() != QtCore.Qt.LeftButton:
            ev.ignore()
        else:
            pyqtgraph.ViewBox.mouseDragEvent(self, ev, **kwargs)

    def wheelEvent(self, ev, axis=None):
        ev.ignore()


class MplWidget(pyqtgraph.PlotWidget):
    def __init__(self, parent=None, height=300, width=300):
        super().__init__(viewBox=CustomViewBox())
        self.canvas = MplAdapter(self)
        self.canvas.ax = MplAdapter(self)
        self.ntb = ToolBar()
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
        self.getPlotItem().showGrid(True, True)
        #self.getPlotItem().getAxis('left').setBackgroundColor('w')
        #pyqtgraph.GridItem().setPen('k')

class MplAdapter:
    def __init__(self, item):
        self.item = item
        #super().__init__()
        pass

    def grid(self, val=True):
        self.item.getPlotItem().showGrid(val, val)

    def set_title(self, val=''):
        self.item.getPlotItem().setTitle(val)

    def set_xlabel(self, val=''):
        self.item.setLabel('bottom', val)

    def set_ylabel(self, val=''):
        self.item.setLabel('left', val)
        pass

    def draw(self, val=''):
        pass

    def plot(self, x, y, color='#ffffff'):
        self.item.plot(x, y, pen={'color': color, 'width': 2})

    def clear(self):
        self.item.clear()


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