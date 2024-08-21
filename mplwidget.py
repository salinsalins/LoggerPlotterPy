# coding: utf-8
'''
Created on 31 мая 2017 г.

@author: Sanin
'''

# import matplotlib
# matplotlib.rcParams['path.simplify'] = True
# matplotlib.rcParams['path.simplify_threshold'] = 1.0
# import matplotlib.style as mplstyle
# mplstyle.use('fast')

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.figure import Figure


class PlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, height=300, width=300):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self.ntb = NavigationToolbar(canvas, self)
        # self.ntb.hide()
        layout.addWidget(self.ntb)
        layout.addWidget(canvas)
        self.ax = canvas.figure.subplots()
        self.setLayout(layout)
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
        _copy_attrs(self.ax, self)

    def setTitle(self, text):
        pass
        # self.ax.title = text

    def plot(self, x, y, *args, **kwargs):
        keys = {'color': 'color', 'width': 'linewidth',
                'symbol': 'marker', 'symbolSize': 'markersize'}
        kw = {'color': 'green', 'linewidth': 0.5, 'marker': '', 'markersize': 1.0}
        for k in keys:
            if k in kwargs:
                source = kwargs
            elif 'pen' in kwargs:
                source = kwargs['pen']
            else:
                continue
            if k in source:
                kw[keys[k]] = source[k]
        c = 'green'
        w = 0.5
        m = ''
        if 'color' in kwargs:
            c = kwargs.pop('color')
        elif 'pen' in kwargs:
            p = kwargs.pop('pen')
            if 'color' in p:
                c = p['color']
        if 'width' in kwargs:
            w = kwargs.pop('width')
        elif 'pen' in kwargs:
            p = kwargs.pop('pen')
            if 'width' in p:
                w = p['width']
        if 'symbol' in kwargs:
            m = kwargs.pop('symbol')
        elif 'pen' in kwargs:
            p = kwargs.pop('pen')
            if 'symbol' in p:
                m = p['symbol']
        self.ax.plot(x, y, color=c, linewidth=w, marker=m)

    def clearScaleHistory(self):
        pass

    def autoRange(self):
        pass


def _copy_attrs(src, dst):
    for o in dir(src):
        if not hasattr(dst, o):
            setattr(dst, o, getattr(src, o))
