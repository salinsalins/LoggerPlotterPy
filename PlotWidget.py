# coding: utf-8
"""
Customized pyqtgraph.PlotWidget
with corrected mouse operation

Created on 12 aug 2024
@author: Sanin
"""

import threading

import pyqtgraph
from pyqtgraph.Qt import QtCore, QtWidgets

pyqtgraph.setConfigOption('foreground', 'k')


class PlotWidget(pyqtgraph.PlotWidget):
    MENU = ['Hide plot', 'Show new plot', 'Show plot', 'Show parameters']
    # print(QtWidgets.QMenu)

    def __init__(self, parent=None, height=300, width=300, background='#1d648da0',
                 foreground='k'):
        super().__init__(parent, background=background)
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
        # add menu
        self.getPlotItem().showGrid(True, True)
        self.my_menu = QtWidgets.QMenu()
        self.my_menu.addAction(self.MENU[0])
        self.my_menu.addAction(self.MENU[1])
        self.my_menu.addAction(self.MENU[2])
        self.my_menu.addSeparator()
        self.my_menu.addAction(self.MENU[3])
        # correct mouse behaviour
        # self.setMouseMode(self.RectMode)
        vb = self.getPlotItem().getViewBox()
        vb.mouseClickEvent = self.mouseClickEvent
        vb.mouseDragEvent = self.mouseDragEvent

    def clearScaleHistory(self):
        vb = self.getPlotItem().getViewBox()
        if len(vb.axHistory) > 0:
            vb.showAxRect(vb.axHistory[0])
        vb.axHistory = []  # maintain a history of zoom locations
        vb.axHistoryPointer = -1  # pointer into the history

    def wheelEvent(self, ev, axis=None):
        ev.ignore()

    def mouseClickEvent(self, ev):
        if ev.double() and ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            # self.my_menu.popup(ev.screenPos().toPoint())
            action = self.my_menu.exec(ev.screenPos().toPoint())
            if action is None:
                return
            if action.text() == self.MENU[0]:
                self.my_action.hide_plot(self.my_name, self.my_index)
            elif action.text() == self.MENU[1]:
                self.my_action.show_plot(self.my_name, self.my_index)
            elif action.text() == self.MENU[2]:
                self.my_action.show_plot_on_right(self.my_name, self.my_index)
            elif action.text() == self.MENU[3]:
                self.my_action.signal_params(self.my_name)
        elif ev.button() == QtCore.Qt.RightButton:
            if ev.double():
                self.timer.cancel()
                ev.ignore()
                pyqtgraph.ViewBox.mouseClickEvent(self.getPlotItem().getViewBox(), ev)
            else:
                ev.accept()
                self.timer = threading.Timer(0.3, self.double_click_timer_handler)
                self.timer.start()
                # self.autoRange()

    def double_click_timer_handler(self):
        self.clearScaleHistory()
        self.autoRange()
        return True

    def mouseDragEvent(self, ev, **kwargs):
        if ev.button() != QtCore.Qt.LeftButton:
            ev.accept()
        else:
            pyqtgraph.ViewBox.mouseDragEvent(self.getPlotItem().getViewBox(), ev, **kwargs)

    # def mouseClickEvent(self, ev):
    #     ev.ignore()

    # def plot(self, x, y, *args, **kwargs):
    #     print('plot')
    #     self.getPlotItem().plot(x, y, *args, **kwargs)
