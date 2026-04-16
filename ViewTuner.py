# coding: utf-8
"""
Created on Jul 2, 2017

@author: sanin
"""
# s='s=%r;print(s%%s)';print(s%s)

import os
import sys
import threading

import pyqtgraph
import tango
from PySide6.QtCore import Qt
from pyqtgraph import PlotDataItem

from LoggerPlotterPy import VLine, Signal, read_signal
from LoggerPlotterPy import MainWindow as LP_main_window

if os.path.realpath('../TangoUtils') not in sys.path: sys.path.append(os.path.realpath('../TangoUtils'))
# import gc
import json
import logging
import math
import time
import zipfile
import datetime
from functools import lru_cache
import numpy

from qtpy import QtGui
from qtpy.QtGui import QFont, QColor
from qtpy import uic
from qtpy import QtCore
from qtpy.QtCore import QPoint, QSize
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QMainWindow, QTableWidgetSelectionRange
from qtpy.QtWidgets import QFileDialog
from qtpy.QtWidgets import QFrame, QMenu
from qtpy.QtWidgets import QLabel, QComboBox, QMessageBox
from qtpy.QtWidgets import QTableWidgetItem, QHeaderView

# from PlotWidget import PlotWidget
# from mplwidget import PlotWidget

from QtUtils import WidgetLogHandler
from Configuration import Configuration
from config_logger import config_logger, LOG_FORMAT_STRING_SHORT
from log_exception import log_exception

import threading
import pyqtgraph
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui

np = numpy

APPLICATION_NAME = 'View tuner for Signals'
FILE_NAME = os.path.basename(__file__).replace('.py', '')
APPLICATION_NAME_SHORT = 'ViewTuner'
APPLICATION_VERSION = '1.0'
FMT = os.path.getmtime(__file__)
FMTS = time.strftime("%d-%m-%Y-%H:%M:%S", time.gmtime(os.path.getmtime(__file__)))
VERSION_DATE = FMTS
CONFIG_FILE = FILE_NAME + '.json'
UI_FILE = FILE_NAME + '.ui'
ATTRIBUTE = 'localhost:10000/sys/tg_test/1/double_spectrum_ro'
FILE = 'd:\\data\\2024\\2024-05\\2024-05-23\\2024-05-23_150741.zip'
SIGNAL = 'ADC_0/chany37.txt'

# fonts
CELL_FONT = QFont('Open Sans', 14)
CELL_FONT_BOLD = QFont('Open Sans', 14, QFont.Bold)
STATUS_BAR_FONT = CELL_FONT
CLOCK_FONT = CELL_FONT_BOLD
# colors
WHITE = QColor(255, 255, 255)
YELLOW = QColor(255, 255, 0)
GREEN = QColor(0, 255, 0)
PREVIOUS_COLOR = '#ffff00'
TRACE_COLOR = '#00ff00'
MARK_COLOR = '#ff0000'
ZERO_COLOR = '#0000ff'


# Global configuration dictionary
CONFIG = Configuration(CONFIG_FILE)


class PlotWidget(pyqtgraph.PlotWidget):
    def __init__(self, parent=None, height=300, width=300, background='#1d648da0',
                 foreground='k'):
        super().__init__(parent, background=background, foreground=foreground)
        title_font = QtGui.QFont('Arial', 20)
        axis_font = QtGui.QFont('Arial', 14)
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
        plot_item = self.getPlotItem()
        plot_item.showGrid(True, True)
        plot_item.titleLabel.item.setFont(title_font)
        plot_item.getAxis("bottom").setMaximumHeight(100)
        plot_item.getAxis("bottom").label.setFont(axis_font)
        plot_item.getAxis("bottom").setTickFont(axis_font)
        plot_item.getAxis("left").label.setFont(axis_font)
        plot_item.getAxis("left").setTickFont(axis_font)
        # add menu
        self.my_menu = None
        menu_action_txt  = ['Hide plot', 'Show new plot', 'Show plot', '', 'Show parameters']
        menu_action_func = [lambda *args, **kwargs: None, lambda *args, **kwargs: None, lambda *args, **kwargs: None, lambda *args, **kwargs: None, self.window().show_signal_params]
        self.add_menu(menu_action_txt, menu_action_func)
        # correct mouse behavior
        view_box = self.getPlotItem().getViewBox()
        view_box.mouseClickEvent = self.mouseClickEvent
        view_box.mouseDragEvent = self.mouseDragEvent
        view_box.setMouseMode(view_box.RectMode)

    def add_menu(self, menu, action_func):
        self.my_menu = QtWidgets.QMenu()
        i = 0
        for item_txt in menu:
            if item_txt == '':
                self.my_menu.addSeparator()
            else:
                action = self.my_menu.addAction(item_txt)
                action.action_funct = action_func[i]
            i += 1

    def setTitle(self, text, *args, **kwargs):
        self.getPlotItem().setTitle(text, *args, size='14pt', **kwargs)

    def clearScaleHistory(self):
        vb = self.getPlotItem().getViewBox()
        if len(vb.axHistory) > 0:
            vb.showAxRect(vb.axHistory[0])
        vb.axHistory = []  # maintain a zip_file of zoom locations
        vb.axHistoryPointer = -1  # pointer into the zip_file

    def wheelEvent(self, ev, axis=None):
        # point = ev.screenPos().toPoint()
        ev.ignore()

    def mouseClickEvent(self, ev):
        if ev.double() and ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            action = self.my_menu.exec(ev.screenPos().toPoint())
            if action is None:
                return
            action.action_funct(self.my_name)
            return
        if ev.button() == QtCore.Qt.RightButton:
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

    # def plot(self, x, y, *args, **kwargs):
    #     print('plot')
    #     self.getPlotItem().plot(x, y, *args, **kwargs)


def on_range_changed(view_item, range_list):
    # for item in view_item.addedItems:
    item = view_item.addedItems[0]
    index = np.where((item.curve.xData >= range_list[0][0]) & (item.curve.xData <= range_list[0][1]))[0]
    # if not hasattr(item, 'last_opts'):
    #     item.last_opts = item.opts.copy()
    if 0 < len(index) < 100:
        item.setSymbol('o')
    else:
        item.setSymbol(None)
        # item.opts = item.last_opts.copy()
        # delattr(item, 'last_opts')

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conf = {
            'w_height': 300,
            'w_width': 300,
            'colors': {'previous': PREVIOUS_COLOR,
                       'trace': TRACE_COLOR,
                       'mark': MARK_COLOR,
                       'zero': ZERO_COLOR
                       },
            'file_name': FILE,
            'signal_name': SIGNAL,
            'log_file_name': ''
       }
        # colors
        self.previous_color = PREVIOUS_COLOR
        self.trace_color = TRACE_COLOR
        self.mark_color = MARK_COLOR
        self.zero_color = ZERO_COLOR
        self.mplw = None
        self.file_name = FILE
        self.signal_name = SIGNAL
        self.log_file_name = ''
        self.tango_attribute = None
        self.tango_device = None

        # Configure logging
        self.logger = config_logger(level=logging.DEBUG, format_string=LOG_FORMAT_STRING_SHORT)

        # Load the UI
        uic.loadUi(UI_FILE, self)

        self.zip_file = self.comboBox
        self.signals = self.comboBox_3
        # Connect signals with the slots
        # self.select.clicked.connect(self.select_log_file)
        self.zip_file.currentIndexChanged.connect(self.file_selection_changed)
        self.pushButton_4.clicked.connect(self.select_zip_file)
        self.comboBox_3.currentIndexChanged.connect(self.signal_selection_changed)
        # self.pushButton_5.clicked.connect(self.signal_selection_changed)

        # Menu actions connection
        self.actionQuit.triggered.connect(self.save_and_exit)
        # self.actionAbout.triggered.connect(show_about)

        # main window decorations
        # icon
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        # title
        self.setWindowTitle(APPLICATION_NAME + ' version ' + APPLICATION_VERSION)
        # status bar
        self.sb = self.statusBar()
        self.sb.reformat()
        self.sb.setStyleSheet('border: 0;')
        self.sb.setStyleSheet("QStatusBar::item {border: none;}")
        # status bar: font
        self.sb.setFont(STATUS_BAR_FONT)
        # status bar: clock label
        self.sb.addPermanentWidget(VLine())  # <---
        self.sb_clock = QLabel(" ")
        self.sb_clock.setFont(CLOCK_FONT)
        self.sb.addPermanentWidget(self.sb_clock)
        # status bar: message with data file name
        self.sb_text = QLabel("")
        self.sb_text.setFont(STATUS_BAR_FONT)
        self.sb.addWidget(self.sb_text)
        self.sb.addWidget(VLine())  # <---
        self.sb_text.setText("Starting...")
        # status bar: log show widget
        self.sb_log = QLabel("")
        self.sb_log.setFont(STATUS_BAR_FONT)
        self.sb_log.time = time.time()
        self.sb.addWidget(self.sb_log)
        # status bar: log show widget: log handler
        sbhandler = WidgetLogHandler(self.sb_log)
        sbhandler.setLevel(logging.INFO)
        sbhandler.setFormatter(config_logger.log_formatter)
        self.logger.addHandler(sbhandler)
        # status bar: END

        # default settings
        self.set_default_settings()

        #
        print(APPLICATION_NAME, 'version', APPLICATION_VERSION, 'has been started')
        #

        # restore settings
        self.restore_settings()
        #
        self.zip_file.insertItem(-1, self.file_name)
        self.file_name = ''
        self.file_selection_changed(0)
        # self.comboBox_3.insertItem(-1, self.signal_name)
        # self.signal = read_signal(self.signal_name, self.file_name)
        # self.plot_signal(self.signal)

    def file_selection_changed(self, m):
        self.logger.debug('File selection changed to %s' % m)
        if m < 0:
            return
        new_file = str(self.zip_file.currentText())
        new_file = os.path.abspath(new_file)
        if not os.path.exists(new_file):
            self.logger.warning('File %s not found' % new_file)
            self.zip_file.removeItem(m)
            return
        if self.file_name != new_file:
            self.logger.debug('New file selected %s' % new_file)
            self.file_name = new_file
            channel_list = []
            blocked = self.comboBox_3.blockSignals(True)
            i = 0
            with zipfile.ZipFile(self.file_name, 'r') as zipobj:
                for name in zipobj.NameToInfo:
                    if 'paramchany' not in name:
                        channel_list.append(name)
                        self.comboBox_3.insertItem(-1, name)
            if self.signal_name not in channel_list:
                self.signal_name = channel_list[0]
            else:
                i = self.comboBox_3.findText(self.signal_name)
            self.comboBox_3.blockSignals(blocked)
            self.comboBox_3.setCurrentIndex(i)
            # self.signal = read_signal(self.signal_name, self.file_name)
            # self.plot_signal(self.signal)

    @staticmethod
    def fill_signal_widget(zip_file, widget):
        channel_list = []
        with zipfile.ZipFile(zip_file, 'r') as zipobj:
            for name in zipobj.NameToInfo:
                if 'paramchany' not in name:
                    channel_list.append(name)
                    widget.insertItem(-1, name)

    def signal_selection_changed(self, m):
        self.signal_name = str(self.comboBox_3.currentText())
        self.signal = read_signal(self.signal_name, self.file_name)
        self.plot_signal(self.signal)
        params = self.signal_params_to_dict()
        self.tableWidget_3.clearContents()
        self.tableWidget_3.setRowCount(0)
        self.tableWidget_3.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        for par in params:
            self.tableWidget_3.insertRow(0)
            item = QTableWidgetItem(par)
            self.tableWidget_3.setItem(0, 0, item)
            item = QTableWidgetItem(params[par])
            self.tableWidget_3.setItem(0, 1, item)
        self.tableWidget_3.resizeColumnsToContents()
        self.tableWidget_3.resizeRowsToContents()
        self.get_device_proxy()

    def select_zip_file(self):
        d = os.path.dirname(self.file_name)
        file_open_dialog = QFileDialog(caption='Select Zip File', directory=d)
        # open file selection dialog
        fn = file_open_dialog.getOpenFileName()[0]
        if fn is None or fn == '':
            return
        fn = os.path.abspath(fn)
        # if it is the same file as being used
        if self.file_name == fn:
            return
        # different file selected
        i = self.zip_file.findText(fn)
        if i < 0:
            # add file name to zip_file
            self.zip_file.insertItem(-1, fn)
            i = 0
        # change selection and fire callback
        if self.zip_file.currentIndex() != i:
            self.zip_file.setCurrentIndex(i)
        else:
            self.file_selection_changed(i)

    def restore_settings(self, folder='', file_name=None):
        global CONFIG_FILE
        if file_name is None:
            file_name = CONFIG_FILE
        full_name = os.path.abspath(os.path.join(str(folder), file_name))
        try:
            with open(full_name, 'r') as configfile:
                s = configfile.read()
            self.conf.update(json.loads(s))
            global CONFIG
            CONFIG = self.conf

            # Log level restore
            if 'log_level' in self.conf:
                v = self.conf['log_level']
                self.logger.setLevel(v)
            # Restore window size and position
            self.restore_window_position()
            # colors
            if 'colors' in self.conf:
                self.trace_color = self.conf['colors'].get('trace', self.trace_color)
                self.previous_color = self.conf['colors'].get('previous', self.previous_color)
                self.mark_color = self.conf['colors'].get('mark', self.mark_color)
                self.zero_color = self.conf['colors'].get('zero', self.zero_color)
            #
            self.logger.debug('Configuration restored from %s' % full_name)
            return True
        except:
            log_exception('Configuration restore error from %s' % full_name)
            return False

    def get_device_proxy(self):
        params = self.signal_params_to_dict()
        tango_host = os.getenv('TANGO_HOST')
        self.tango_device = None
        self.tango_attribute = None
        device = ''
        local_name = ''
        try:
            name = params['Signal_Name']
            # host = name.split(':')[0]
            name_split = name.split('/')
            device = '/'.join(name_split[1:4])
            local_name = name.replace(name_split[0], '')
            local_device = '/'.join(name_split[:4])
            print(name, local_name, device, local_device)
        except:
            log_exception(exc_info=False)
            return
        try:
            self.tango_device = tango.DeviceProxy(local_device)
            self.tango_attribute = tango.AttributeProxy(name)
            return
        except:
            # log_exception()
            log_exception(exc_info=False)
        try:
            self.tango_device = tango.DeviceProxy(device)
            self.tango_attribute = tango.AttributeProxy(local_name)
        except:
            log_exception(exc_info=False)

    @staticmethod
    def split_signal_name(name: str):
        split = name.split('/')
        attribute = split[-1]
        host_port = split[-1]
        device = '/'.join(split[1:-1])
        return host_port, device, attribute

    def show_signal_params(self, signal, *args):
        params = self.get_signal_params(self.signal)
        dlg = QMessageBox()
        dlg.setWindowTitle("Signal parameters for " + signal)
        dlg.setText(params)
        button = dlg.exec()

    def get_signal_params(self, signal=None):
        signal = signal if signal else self.signal
        txt = str(signal.params).replace(",", "\n")
        txt = txt.replace("b'", "'")
        txt = txt.replace("'", "")
        txt = txt.replace("{", "")
        txt = txt.replace("}", "")
        txt = txt.replace(":1", "#1")
        txt = txt.replace(":", "=")
        txt = txt.replace("#1", ":1")
        return txt

    def signal_params_to_dict(self, signal=None):
        arr = self.get_signal_params(signal).split("\n")
        result = {}
        for a in arr:
            nv = a.split("=")
            result[nv[0].strip()] = nv[1].strip()
        return result

    def plot_signal(self, signal=None):
        if signal is None:
            return
        layout = self.widget.layout()
        if self.mplw is None: # create new plot widget
            self.mplw = PlotWidget(self, height=self.conf['w_height'], width=self.conf['w_width'])
            # self.mplw.mouseClickEvent = plotMouseClickEvent
            self.mplw.my_action = self
            self.mplw.my_name = signal.name
            layout.addWidget(self.mplw)
            # Connecting the hook
            self.mplw.getViewBox().sigRangeChanged.connect(on_range_changed)
        self.mplw.clear()
        # Decorate the plot
        # mplw.showGrid(True, True)
        if math.isnan(signal.value) or signal.value is None:
            default_title = signal.name
        else:
            default_title = '{0} = {1:5.2f} {2}'.format(signal.name, signal.value, signal.unit)
        self.mplw.setTitle(LP_main_window.from_params(b'title', signal.params, default_title))
        lbl = LP_main_window.from_params(b'xlabel', signal.params)
        if lbl:
            self.mplw.setLabel('bottom', lbl)
        lbl = LP_main_window.from_params(b'ylabel', signal.params)
        if lbl:
            self.mplw.setLabel('left', lbl)
        # plot main line
        y_min = float('inf')
        y_max = float('-inf')
        x_min = float('inf')
        x_max = float('-inf')
        try:
            y_min = float(LP_main_window.from_params(b'plot_y_min', signal.params, 'inf'))
            y_max = float(LP_main_window.from_params(b'plot_y_max', signal.params, '-inf'))
            if y_max > y_min:
                self.mplw.setYRange(y_min, y_max)
        except KeyboardInterrupt:
            raise
        except:
            pass
        try:
            x_min = float(LP_main_window.from_params(b'plot_x_min', signal.params, 'inf'))
            x_max = float(LP_main_window.from_params(b'plot_x_max', signal.params, '-inf'))
            if x_max > x_min:
                self.mplw.setXRange(x_min, x_max)
        except:
            pass
        if len(signal.x) > 100:
            self.mplw.plot(signal.x, signal.y, pen={'color': self.trace_color, 'width': 1})
        else:
            self.mplw.plot(signal.x, signal.y, pen={'color': self.trace_color, 'width': 1}, symbol='o', symbolSize=8, pxMode=True )
        # plot 'mark' highlight
        if 'mark' in signal.marks:
            m1 = signal.marks['mark'][0]
            m2 = m1 + signal.marks['mark'][1]
            self.mplw.plot(signal.x[m1:m2], signal.y[m1:m2], pen={'color': self.mark_color, 'width': 1})
        # Plot 'zero' highlight
        if 'zero' in signal.marks:
            m1 = signal.marks['zero'][0]
            m2 = m1 + signal.marks['zero'][1]
            self.mplw.plot(signal.x[m1:m2], signal.y[m1:m2], pen={'color': self.zero_color, 'width': 1})
        # Show plot
        try:
            self.mplw.clearScaleHistory()
            if not (y_max > y_min) and not (x_max > x_min):
                self.mplw.autoRange()
        except:
            log_exception()
        layout.update()
        # self.logger.debug('End %s', time.time() - t0)


    def update_status_bar(self):
        if self.log_file_name is not None and self.log_table is not None:
            self.sb_text.setText('File: %s' % self.log_file_name)
        else:
            self.sb_text.setText('Data file not found')


    def get_data_folder(self):
        if self.log_file_name is None:
            data_folder = "./"
        else:
            data_folder = os.path.dirname(self.log_file_name)
        return data_folder

    def on_quit(self):
        # save global settings
        # print(self.pos().x(), self.pos().y())
        self.save_settings()

    def save_settings(self, folder: str = '', file_name=None, config: dict | None =None):
        global CONFIG_FILE
        if config is None:
            config = self.conf
        if file_name is None:
            file_name = CONFIG_FILE
        full_name = os.path.abspath(os.path.join(str(folder), file_name))
        try:
            # save window size and position
            p = self.pos()
            s = self.size()
            config['main_window'] = {'size': (s.width(), s.height()), 'position': (p.x(), p.y())}
            # log file zip_file
            # convert to JSON and write
            with open(full_name, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.debug('Configuration saved to %s' % full_name)
            return True
        except:
            log_exception('Error configuration save to %s' % full_name)
            return False

    def restore_window_position(self):
        self.setMinimumSize(640, 480)  # resize hook
        try:
            self.resize(QSize(self.conf['main_window']['size'][0], self.conf['main_window']['size'][1]))
            x = int(self.conf['main_window']['position'][0])
            y = int(self.conf['main_window']['position'][1])
            screens = QtGui.QGuiApplication.screens()
            for screenn in screens:
                sg = screenn.geometry()
                if sg.left() < x < sg.left() + sg.width():
                    if sg.top() < y < sg.top() + sg.height():
                        self.move(QPoint(x, y))
                        return
            self.move(QPoint(20, 20))
        except:
            self.logger.info('Error restoring window position')

    def set_default_settings(self):
        try:
            # window size and position
            self.resize(QSize(640, 480))
            self.move(QPoint(0, 0))
            return True
        except:
            self.logger.log(logging.WARNING, 'Default configuration error.')
            self.logger.debug('Exception:', exc_info=True)
            return False

    def is_locked(self):
        # if log file is not set = locked
        if self.log_file_name is None:
            return True
        # look for the file "lock.lock" in the folder of the log file
        folder = os.path.dirname(self.log_file_name)
        file = os.path.abspath(os.path.join(folder, "lock.lock"))
        if os.path.exists(file):
            return True
        return False

    def get_data_root(self):
        day = os.path.dirname(self.log_file_name)
        month = os.path.dirname(day)
        year = os.path.dirname(month)
        root = os.path.dirname(year)
        if not os.path.exists(root):
            self.logger.debug('Data root does not exist')
        return root

    def closeEvent(self, a0: QtGui.QCloseEvent, **kwargs) -> None:
        self.save_settings()
        a0.accept()

    def save_and_exit(self) -> None:
        self.save_settings()
        QApplication.exit()
        # QApplication.quit()



if __name__ == '__main__':
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    if len(sys.argv) >= 2:
        ATTRIBUTE = sys.argv[1]
    if len(sys.argv) >= 3:
        FILE = sys.argv[2]
    if len(sys.argv) >= 4:
        SIGNAL_NAME = sys.argv[4]
    if len(sys.argv) >= 5:
        CONFIG_FILE = sys.argv[4]
    app = QApplication(sys.argv)
    # instantiate the main window
    dmw = MainWindow()
    # connect quit processing code
    # app.aboutToQuit.connect(dmw.on_quit)
    # show main window
    dmw.show()
    # start the Qt main loop execution,
    exec_result = app.exec_()
    # exiting from this script with the same return code of Qt application
    sys.exit(exec_result)
