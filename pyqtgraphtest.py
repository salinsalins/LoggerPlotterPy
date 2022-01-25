import sys
import PyQt6
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QLineEdit, QListWidget, QWidget, QPushButton, QGridLayout


## Always start by initializing Qt (only once per application)
app = QApplication(sys.argv)

## Define a top-level widget to hold everything
w = QWidget()

## Create some widgets to be placed inside
btn = QPushButton('press me')
text = QLineEdit('enter text')
listw = QListWidget()

# plot = pg.PlotWidget()

## Create a grid layout to manage the widgets size and position
layout = QGridLayout()
w.setLayout(layout)

## Add widgets to the layout in their proper positions
layout.addWidget(btn, 0, 0)  # button goes in upper-left
layout.addWidget(text, 1, 0)  # text edit goes in middle-left
layout.addWidget(listw, 2, 0)  # list widget goes in bottom-left
#layout.addWidget(plot, 0, 1, 3, 1)  # plot goes on right side, spanning 3 rows

import numpy as np

label = pg.LabelItem(justify='right')

x = np.random.normal(size=1000)
y = np.random.normal(size=1000)
# p1 = plot.plot(x, y, pen=None, symbol='o')  ## setting pen=None disables line drawing
# plot.plot(x * 2, y * 2)  ## setting pen=None disables line drawing

# plot.plot(x, y * 2, pen='r')
# plot.plot(x * 2, y, pen='g')

# a = plot.getPlotItem()

# plot.setMinimumHeight(300)
# plot.setMinimumWidth(500)

## Display the widget as a new window
w.show()

## Start the Qt event loop
pg.plot(x=[0, 5, 6, 2], y=[1, 9, 10, 15])
# app.exec_()
app.exec()
