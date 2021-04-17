from PyQt5 import QtGui  # (the example applies equally well to PySide2)
import pyqtgraph as pg

## Always start by initializing Qt (only once per application)
app = QtGui.QApplication([])

## Define a top-level widget to hold everything
w = QtGui.QWidget()

## Create some widgets to be placed inside
btn = QtGui.QPushButton('press me')
text = QtGui.QLineEdit('enter text')
listw = QtGui.QListWidget()
plot = pg.PlotWidget()

## Create a grid layout to manage the widgets size and position
layout = QtGui.QGridLayout()
w.setLayout(layout)

## Add widgets to the layout in their proper positions
layout.addWidget(btn, 0, 0)   # button goes in upper-left
layout.addWidget(text, 1, 0)   # text edit goes in middle-left
layout.addWidget(listw, 2, 0)  # list widget goes in bottom-left
layout.addWidget(plot, 0, 1, 3, 1)  # plot goes on right side, spanning 3 rows

import numpy as np
x = np.random.normal(size=1000)
y = np.random.normal(size=1000)
plot.plot(x, y, pen=None, symbol='o')  ## setting pen=None disables line drawing
plot.plot(x*2, y*2)  ## setting pen=None disables line drawing


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.autoRange()

    def mouseDragEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev)


app = pg.mkQApp()

axis = pg.DateAxisItem(orientation='bottom')
vb = CustomViewBox()

pw = pg.PlotWidget(viewBox=vb, axisItems={'bottom': axis}, enableMenu=False,
                   title="PlotItem with DateAxisItem and custom ViewBox<br>Menu disabled, mouse behavior changed: left-drag to zoom, right-click to reset zoom")
dates = np.arange(8) * (3600 * 24 * 356)
pw.plot(x=dates, y=[1, 6, 2, 4, 3, 5, 6, 8], symbol='o')
pw.show()
pw.setWindowTitle('pyqtgraph example: customPlot')
#plot.clear()

plot.plot(x, y*2, pen='r')
plot.plot(x*2, y, pen='g')

a = plot.getPlotItem()

plot.setMinimumHeight(300)
plot.setMinimumWidth(500)

## Display the widget as a new window
w.show()

## Start the Qt event loop
app.exec_()