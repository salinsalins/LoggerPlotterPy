# coding: utf-8
"""
Created on Jul 2, 2017
@author: sanin
"""
# s='s=%r;print(s%%s)';print(s%s)

import os
import sys

sys.path.insert(0, os.path.realpath('../TangoUtils'))
import json
import logging
import math
import time
import zipfile
import datetime
from functools import lru_cache
import numpy

from PySide6 import QtGui
from PySide6.QtGui import QFont, QColor
from PySide6.QtUiTools import QUiLoader
# from PyQt5 import uic
from PySide6 import QtCore
from PySide6.QtCore import QFile, QPoint, QSize
from PySide6.QtCore import QTimer
# from PyQt5 import QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetSelectionRange
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QFrame, QMenu
from PySide6.QtWidgets import QLabel, QComboBox, QMessageBox
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView

# from mplwidget import MplWidget
from pyqtgraphwidget import MplWidget

# util_path = os.path.realpath('../TangoUtils')
# if util_path not in sys.path: sys.path.append(util_path)
# del util_path
# sys.path.insert(0, os.path.realpath('../TangoUtils'))

from QtUtils import WidgetLogHandler
from Configuration import Configuration
from config_logger import config_logger, LOG_FORMAT_STRING_SHORT
from log_exception import log_exception

np = numpy

# from config import *

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'Plotter for Signals from Dumper'
APPLICATION_NAME_SHORT = 'LoggerPlotterPy'
APPLICATION_VERSION = '14.0'
VERSION_DATE = os.path.getmtime(__file__)
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'
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

MAIN_LOOP_TIMEOUT = 1000

# Global configuration dictionary
CONFIG = Configuration(CONFIG_FILE)


def remove_from_text(text: str, removed: str):
    if text == '':
        return text
    lines = text.split('\n')
    res = [line.strip() for line in lines if line != removed and line.strip() != '']
    if len(res) <= 0:
        return ''
    return '\n'.join(res)


def remove_from_widget(widget, removed: str):
    text = widget.toPlainText()
    widget.setPlainText(remove_from_text(text, removed))


class SignalNotFoundError(ValueError):
    pass


global sigg


@lru_cache(maxsize=256)
def calculate_extra_plot(p, file_name):
    # sig() can be used in eval(p) to select signal by name
    sig = sigg
    # print('Calculate', p)
    p = p.strip()
    s = None
    try:
        result = eval(p)
        if isinstance(result, Signal):
            s = result
        elif isinstance(result, dict):
            key = result['name']
            if key != '':
                x = result['x']
                y = result['y']
                marks = result.get('marks', {})
                # convert mark time to index
                if marks:
                    for m in marks:
                        index = numpy.searchsorted(x, [marks[m][0], marks[m][0] + marks[m][1]])
                        marks[m][0] = index[0]
                        marks[m][1] = index[1] - index[0]
                params = result.get('params', None)
                unit = result.get('unit', '')
                value = result.get('value', float('nan'))
                s = Signal(x, y, name=key, params=params, marks=marks, unit=unit, value=value)
        elif isinstance(result, list) or isinstance(result, tuple):
            if len(result) >= 3:
                key, x_val, y_val = result[:3]
                if key != '':
                    s = Signal(x_val, y_val, name=key)
            elif len(result) == 2:
                if isinstance(result[1], Signal):
                    s = result[1]
                    s.name = result[0]
                    s.data_name = s.name
        if s:
            s.calculate_value()
            s.code = p
            s.file = file_name
            config_logger.logger.debug('Plot %s has been calculated' % s.name)
        else:
            config_logger.logger.info('Can not calculate signal for "%s ..."\n', p[:20])
    except SignalNotFoundError as e:
        config_logger.logger.warning(e)
    except:
        log_exception(config_logger.logger, 'eval() error in "%s ..."\n' % p[:20], level=logging.INFO)
    return s


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.resize_hook = True
        # colors
        self.previous_color = PREVIOUS_COLOR
        self.trace_color = TRACE_COLOR
        self.mark_color = MARK_COLOR
        self.zero_color = ZERO_COLOR
        #
        self.log_file_name = None
        self.data_root = None
        self.conf = {}
        self.rmb = {}
        self.last_selection = -1
        self.current_selection = -1
        self.signal_list = []
        self.old_signal_list = []
        self.signals = []
        self.extra_cols = []
        self.extra_plots = []
        self.calculated_plots = {}
        self.data_file = None
        self.old_size = 0
        self.new_size = 0
        self.included = []
        self.excluded = []
        self.columns = []
        self.last_cell_background = None
        self.last_cell_row = -1
        self.last_cell_column = -1
        self.log_table = None
        self.cut_long_names = True
        self.fill_empty_lists = True
        # Configure logging
        self.logger = config_logger(level=logging.INFO, format_string=LOG_FORMAT_STRING_SHORT)
        # Load the UI
        # uic.loadUi(UI_FILE, self)
        ui_file = QFile(UI_FILE)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.window.on_quit = self.on_quit
        # self.window.show()
        # Connect signals with the slots
        self.pushButton_2.clicked.connect(self.select_log_file)
        self.comboBox_2.currentIndexChanged.connect(self.file_selection_changed)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
        # self.tableWidget_3.focusOutEvent = self.focus_out
        self.comboBox_1.currentIndexChanged.connect(self.log_level_index_changed)
        # Menu actions connection
        self.actionQuit.triggered.connect(self.save_and_exit)
        self.actionToday.triggered.connect(self.select_today_file)
        self.actionOpen.triggered.connect(self.select_log_file)
        self.actionPlot.triggered.connect(self.show_plot_pane)
        self.actionParameters.triggered.connect(self.show_param_pane)
        self.actionAbout.triggered.connect(self.show_about)
        # self.menuToday.aboutToShow.connect(self.select_today_file)
        # main window decoration
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.setWindowTitle(APPLICATION_NAME + ' version ' + APPLICATION_VERSION)
        # table: header
        header = self.tableWidget_3.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # table: header right click menu
        header.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.table_header_right_click_menu_wrap)
        # table: style tuning
        self.tableWidget_3.setStyleSheet("""
                QTableView {
                    gridline-color: black;
                    alternate-background-color: #d0d0d0;
                }
                QHeaderView::section {
                    background-color: palette(dark);
                    border: 1px solid black;
                }
            """)
        #
        # status bar
        sb = self.window.statusBar()
        sb.reformat()
        sb.setStyleSheet('border: 0;')
        sb.setStyleSheet("QStatusBar::item {border: none;}")
        # status bar: font
        sb.setFont(STATUS_BAR_FONT)
        # status bar: previous shot time
        self.sb_prev_shot_time = QLabel("**:**:**")
        self.sb_prev_shot_time.setFont(STATUS_BAR_FONT)
        self.sb_prev_shot_time.setStyleSheet('border: 0; color:  black; background: yellow;')
        self.sb_prev_shot_time.setText("**:**:**")
        self.sb_prev_shot_time.setVisible(False)
        sb.addWidget(self.sb_prev_shot_time)
        sb.addWidget(VLine())  # <---
        # status bar: green trace time
        self.sb_green_time = QLabel("**:**:**")
        self.sb_green_time.setFont(STATUS_BAR_FONT)
        self.sb_green_time.setStyleSheet('border: 0; color:  black; background: green;')
        self.sb_green_time.setText("**:**:**")
        self.sb_green_time.setVisible(False)
        sb.addWidget(self.sb_green_time)
        sb.addWidget(VLine())  # <---
        # status bar: config select combo
        self.sb_combo = QComboBox(self.statusBar())
        self.sb_combo.setFont(STATUS_BAR_FONT)
        sb.addWidget(self.sb_combo)
        sb.addWidget(VLine())  # <---
        self.fill_config_widget()
        # status bar: clock label
        sb.addPermanentWidget(VLine())  # <---
        self.sb_clock = QLabel(" ")
        self.sb_clock.setFont(CLOCK_FONT)
        sb.addPermanentWidget(self.sb_clock)
        # status bar: message with data file name
        self.sb_text = QLabel("")
        self.sb_text.setFont(STATUS_BAR_FONT)
        sb.addWidget(self.sb_text)
        sb.addWidget(VLine())  # <---
        self.sb_text.setText("Starting...")
        # status bar: log show widget
        self.sb_log = QLabel("")
        self.sb_log.setFont(STATUS_BAR_FONT)
        self.sb_log.time = time.time()
        sb.addWidget(self.sb_log)
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
        self.restore_local_settings()
        #
        # additional decorations
        self.tableWidget_3.horizontalHeader().setVisible(True)
        #
        self.parse_folder()

    def show(self):
        self.window.show()

    def __getattr__(self, name):
        if hasattr(self.window, name):
            attr = getattr(self.window, name)
            setattr(self, name, attr)
            return attr
        else:
            raise AttributeError()

    def fill_config_widget(self):
        global CONFIG_FILE
        try:
            self.sb_combo.currentIndexChanged.disconnect(self.config_selection_changed)
        except:
            pass
        self.sb_combo.clear()
        arr = os.listdir()
        jsonarr = [x for x in arr if x.endswith('.json')]
        for x in jsonarr:
            if CONFIG_FILE in x:
                jsonarr.pop(jsonarr.index(x))
                jsonarr.insert(0, x)
        self.sb_combo.addItems(jsonarr)
        self.sb_combo.currentIndexChanged.connect(self.config_selection_changed)

    def hide_plot(self, signal_name, index=-1):
        text = self.plainTextEdit_7.toPlainText()
        if signal_name not in text:
            return
        if index > 0:
            disp_lines = text.split('\n')
            disp_lines.pop(index)
            new_text = '\n'.join(disp_lines)
        else:
            new_text = remove_from_text(text, signal_name)
        if new_text == '':
            return
        self.plainTextEdit_7.setPlainText(new_text)
        # add to hidden columns list
        text = self.plainTextEdit_6.toPlainText() + '\n' + signal_name
        self.plainTextEdit_6.setPlainText(text)
        self.sort_text_edit_widget(self.plainTextEdit_6)
        self.save_local_settings()
        self.save_settings()
        self.plot_signals()

    def show_plot(self, signal_name, index=-1):
        cursor = QtGui.QCursor()
        position = cursor.pos()
        hidden = self.plainTextEdit_6.toPlainText()
        hidden_lines = hidden.split('\n')
        menu = QMenu()
        actions = []
        for s in hidden_lines:
            if s != '' and s not in actions:
                actions.append(s)
                menu.addAction(s)
        if len(actions) <= 0:
            return
        action = menu.exec(position)
        if action is None:
            return
        displayed = self.plainTextEdit_7.toPlainText()
        if index > 0:
            disp_lines = displayed.split('\n')
            disp_lines.insert(index + 1, action.text())
            displayed = '\n'.join(disp_lines)
        else:
            displayed = displayed.replace(signal_name, signal_name + '\n' + action.text())
        self.plainTextEdit_7.setPlainText(displayed)
        # self.plainTextEdit_6.setPlainText(remove_from_text(hidden, action.text()))
        self.save_settings()
        self.save_local_settings()
        self.plot_signals()

    def show_plot_on_right(self, signal_name, index=-1):
        cursor = QtGui.QCursor()
        position = cursor.pos()
        signal_list = self.signal_list + self.extra_plots
        actions = []
        for s in signal_list:
            if s.name != '' and s.name != signal_name and s.name not in actions:
                actions.append(s.name)
        actions.sort()
        menu = QMenu()
        for a in actions:
            menu.addAction(a)
        if len(actions) <= 0:
            return
        action = menu.exec(position)
        if action is None:
            return
        displayed = self.plainTextEdit_7.toPlainText()
        if index > 0:
            disp_lines = displayed.split('\n')
            disp_lines.insert(index + 1, action.text())
            self.plainTextEdit_7.setPlainText('\n'.join(disp_lines))
        else:
            displayed = remove_from_text(displayed, action.text())
            displayed = displayed.replace(signal_name, signal_name + '\n' + action.text())
            self.plainTextEdit_7.setPlainText(displayed)
        # self.plainTextEdit_6.setPlainText(remove_from_text(hidden, action.text()))
        self.save_settings()
        self.save_local_settings()
        self.plot_signals()

    def show_column(self, n):
        cursor = QtGui.QCursor()
        position = cursor.pos()
        hidden = self.plainTextEdit_3.toPlainText()
        hidden_lines = hidden.split('\n')
        menu = QMenu()
        actions = []
        for s in hidden_lines:
            if s != '':
                actions.append(menu.addAction(s))
        if len(actions) <= 0:
            return
        action = menu.exec(position)
        if action is None:
            return
        displayed = self.plainTextEdit_2.toPlainText()
        current = self.tableWidget_3.horizontalHeaderItem(n).text()
        displayed = displayed.replace(current, current + '\n' + action.text())
        self.plainTextEdit_2.setPlainText(displayed)
        self.plainTextEdit_3.setPlainText(remove_from_text(hidden, action.text()))

    def table_header_right_click_menu(self, n):
        # print('menu', n)
        cursor = QtGui.QCursor()
        position = cursor.pos()
        # position = n
        menu = QMenu()
        hide_action = menu.addAction("Hide column")
        show_action = menu.addAction("Show column")
        if n < self.tableWidget_3.columnCount() - 1:
            right_action = menu.addAction("Move right")
        else:
            right_action = None
        if n > 1:
            left_action = menu.addAction("Move left")
        else:
            left_action = None
        action = menu.exec(position)
        if action is None:
            return
        elif action == hide_action:
            # print("Hide", n)
            # remove from shown columns list
            t = self.tableWidget_3.horizontalHeaderItem(n).text()
            text = self.plainTextEdit_2.toPlainText()
            self.plainTextEdit_2.setPlainText(remove_from_text(text, t))
            # add to hidden columns list
            text = self.plainTextEdit_3.toPlainText()
            self.plainTextEdit_3.setPlainText(text + t + '\n')
            self.sort_text_edit_widget(self.plainTextEdit_3)
        elif action == show_action:
            self.show_column(n)
        elif n > 1 and action == left_action:
            # print("Move Left", n)
            t1 = self.tableWidget_3.horizontalHeaderItem(n).text()
            t2 = self.tableWidget_3.horizontalHeaderItem(n - 1).text()
            text = self.plainTextEdit_2.toPlainText()
            text = text.replace(t1, '*+-=*')
            text = text.replace(t2, t1)
            text = text.replace('*+-=*', t2)
            self.plainTextEdit_2.setPlainText(text)
        elif n < self.tableWidget_3.columnCount() - 1 and action == right_action:
            # print("Move Right", n)
            t1 = self.tableWidget_3.horizontalHeaderItem(n).text()
            t2 = self.tableWidget_3.horizontalHeaderItem(n + 1).text()
            text = self.plainTextEdit_2.toPlainText()
            text = text.replace(t1, '****')
            text = text.replace(t2, t1)
            text = text.replace('****', t2)
            self.plainTextEdit_2.setPlainText(text)
        self.fill_table_widget()
        self.tableWidget_3.selectRow(self.current_selection)
        self.change_background()

    def table_header_right_click_menu_wrap(self, a, *args):
        n = self.tableWidget_3.columnAt(a.x())
        if n > 0:
            self.table_header_right_click_menu(n)

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + 'version ' + APPLICATION_VERSION +
                                '\nShows saved shot logs and plot traces.', QMessageBox.StandardButton.Ok)

    def show_plot_pane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionParameters.setChecked(False)
        self.save_local_settings()
        self.save_settings()
        # self.table_selection_changed(True)
        self.parse_folder()

    def show_param_pane(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionParameters.setChecked(True)
        self.sort_text_edit_widget(self.plainTextEdit_3)
        self.sort_text_edit_widget(self.plainTextEdit_6)
        self.fill_config_widget()

    def select_log_file(self):
        """Opens a file select dialog"""
        # define current dir
        if self.log_file_name is None:
            d = "./"
        else:
            d = os.path.dirname(self.log_file_name)
        file_open_dialog = QFileDialog(caption='Select Log File', directory=d)
        # open file selection dialog
        fn = file_open_dialog.getOpenFileName()
        # Qt4 and Qt5 compatibility workaround
        if fn is not None and len(fn) > 1:
            fn = fn[0]
        # if fn is empty
        if fn is None or fn == '':
            return
        fn = os.path.abspath(fn)
        # if it is the same file as being used
        if self.log_file_name == fn:
            return
        # different file selected
        i = self.comboBox_2.findText(fn)
        if i < 0:
            # add file name to history
            self.comboBox_2.insertItem(-1, fn)
            i = 0
        # change selection and fire callback
        if self.comboBox_2.currentIndex() != i:
            self.comboBox_2.setCurrentIndex(i)
        else:
            self.file_selection_changed(i)

    def select_today_file(self):
        ydf = datetime.datetime.today().strftime('%Y')
        mdf = datetime.datetime.today().strftime('%Y-%m')
        ddf = datetime.datetime.today().strftime('%Y-%m-%d')
        logfn = datetime.datetime.today().strftime('%Y-%m-%d.log')
        rootfn = os.path.dirname(self.log_file_name)
        fn = os.path.abspath(os.path.join(rootfn[:-23], ydf, mdf, ddf, logfn))
        if not os.path.exists(fn):
            self.logger.error(f"Today file {fn} does not exist")
            return
        # if it is the same file as being used
        if self.log_file_name == fn:
            return
        # different file selected
        i = self.comboBox_2.findText(fn)
        if i < 0:
            # add file name to history
            self.comboBox_2.insertItem(-1, fn)
            i = 0
        # change selection and fire callback
        self.comboBox_2.setCurrentIndex(i)

    def get_selected_row(self, widget=None):
        if widget is None:
            widget = self.tableWidget_3
        rng = widget.selectedRanges()
        # if selection is empty
        if len(rng) < 1:
            self.logger.debug('Empty selection')
            return -1
        # top row of the selection
        row_s = rng[0].topRow()
        # if selected the same row
        if self.current_selection == row_s:
            self.logger.debug('Selection unchanged')
            return row_s
        # different row selected
        self.logger.debug('Selection changed from %s to %i', self.current_selection, row_s)
        return row_s

    def sig(self, name):
        for sg in self.signal_list:
            if sg.name == name:
                return sg
        raise ValueError('Signal %s not found' % name)

    def table_selection_changed(self, force=False):
        sig = self.sig
        row_s = self.get_selected_row(self.tableWidget_3)
        if row_s < 0:
            return
        if force or self.current_selection != row_s:
            # gc.collect()
            self.scrollAreaWidgetContents_3.setUpdatesEnabled(False)
            self.tableWidget_3.setUpdatesEnabled(False)
            try:
                # read signals from zip file
                folder = os.path.dirname(self.log_file_name)
                zip_file_name = self.log_table(row_s, "File")['text']
                self.logger.debug('Using zip File "%s" from %s', zip_file_name, folder)
                self.data_file = DataFile(zip_file_name, folder=folder)
                self.old_signal_list = self.signal_list + self.extra_plots
                self.signal_list = self.data_file.read_all_signals()
                self.last_selection = self.current_selection
                self.current_selection = row_s
                self.restore_background()
                self.plot_signals()
                self.update_status_bar()
            except:
                r = QTableWidgetSelectionRange(self.current_selection, 0, self.current_selection,
                                               self.tableWidget_3.columnCount() - 1)
                self.tableWidget_3.setRangeSelected(r, True)
                log_exception(self)
            finally:
                self.tableWidget_3.setUpdatesEnabled(True)
                self.scrollAreaWidgetContents_3.setUpdatesEnabled(True)

    def calculate_extra_plots(self):

        def sig(name):
            # signal_list = self.signal_list + self.extra_plots
            for sg in self.signal_list:
                if sg.name == name:
                    return sg
            for sg in self.extra_plots:
                if sg.name == name:
                    return sg
            raise SignalNotFoundError('Signal %s not found' % name)
            # return None

        global sigg
        sigg = sig

        self.extra_plots = []
        # read extra plots from plainTextEdit_4
        extra_plots_str = self.get_extra_plots()
        for p in extra_plots_str:
            p = p.strip()
            s = calculate_extra_plot(p, self.data_file.file_name)
            if s is not None:
                self.extra_plots.append(s)
                self.logger.debug('Plot %s has been added' % s.name)
        if len(self.extra_plots) <= 0:
            self.logger.debug('No extra plots added')

    def sort_plots(self):
        plot_order = self.plainTextEdit_7.toPlainText().split('\n')
        hidden_plots = []
        ordered_plots = []
        signal_list = self.signal_list + self.extra_plots
        for p in plot_order:
            for s in signal_list:
                if s.name == p:
                    ordered_plots.append(signal_list.index(s))
                    break
        # build list of hidden plots
        for s in signal_list:
            if signal_list.index(s) not in ordered_plots:
                hidden_plots.append(s.name)
        hidden_plots.sort()
        text = ''
        for t in hidden_plots:
            text += t
            text += '\n'
        self.plainTextEdit_6.setPlainText(text)
        return ordered_plots

    def plot_signals(self, signals=None):
        if signals is None:
            self.calculate_extra_plots()
            self.signals = self.sort_plots()
            signals = self.signals
        # t0 = time.time()
        # self.logger.debug('Begin')
        layout = self.scrollAreaWidgetContents_3.layout()
        jj = 0
        col = 0
        row = 0
        col_count = self.conf['columns']
        l_count = layout.count()
        signal_list = self.signal_list + self.extra_plots
        plot_order = self.plainTextEdit_7.toPlainText().split('\n')
        ii = 0
        for c in signals:
            s = signal_list[c]
            # Use existing plot widgets or create new
            if jj < l_count:
                # use existing plot widget
                mplw = layout.itemAt(jj).widget()
            else:
                # create new plot widget
                mplw = MplWidget(height=self.conf['w_height'], width=self.conf['w_width'])
                mplw.ntb.setIconSize(QSize(18, 18))
                mplw.ntb.setFixedSize(self.conf['w_width'], 24)
                layout.addWidget(mplw, row, col)
                # mplw.getViewBox().my_menu.addAction('oooo')
            mplw.my_action = self
            mplw.my_name = s.name
            while plot_order[ii] != s.name:
                ii += 1
            mplw.my_index = ii
            col += 1
            if col >= col_count:
                col = 0
                row += 1
            # Show toolbar
            if self.show_toolbar:
                mplw.ntb.show()
            else:
                mplw.ntb.hide()
            # get axes
            axes = mplw.canvas.ax
            axes.clear()
            # Decorate the plot
            axes.grid(True)
            if math.isnan(s.value) or s.value is None:
                default_title = s.name
            else:
                default_title = '{0} = {1:5.2f} {2}'.format(s.name, s.value, s.unit)
            axes.set_title(self.from_params(b'title', s.params, default_title))
            axes.set_xlabel(self.from_params(b'xlabel', s.params, 'Time, ms'))
            axes.set_ylabel(self.from_params(b'ylabel', s.params, '%s, %s' % (s.name, s.unit)))
            # plot previous line
            if self.plot_previous_line and self.last_selection >= 0:
                for s1 in self.old_signal_list:
                    if s1.name == s.name:
                        axes.plot(s1.x, s1.y, color=self.previous_color)
                        break
            # plot main line
            y_min = float('inf')
            y_max = float('-inf')
            x_min = float('inf')
            x_max = float('-inf')
            try:
                y_min = float(self.from_params(b'plot_y_min', s.params, 'inf'))
                y_max = float(self.from_params(b'plot_y_max', s.params, '-inf'))
                if y_max > y_min:
                    mplw.setYRange(y_min, y_max)
            except:
                pass
            try:
                x_min = float(self.from_params(b'plot_x_min', s.params, 'inf'))
                x_max = float(self.from_params(b'plot_x_max', s.params, '-inf'))
                if x_max > x_min:
                    mplw.setXRange(x_min, x_max)
            except:
                pass
            if len(s.x) > 20:
                axes.plot(s.x, s.y, color=self.trace_color)
            else:
                axes.plot(s.x, s.y, color=self.trace_color, symbol='o')
            # plot 'mark' highlight
            if 'mark' in s.marks:
                m1 = s.marks['mark'][0]
                m2 = m1 + s.marks['mark'][1]
                axes.plot(s.x[m1:m2], s.y[m1:m2], color=self.mark_color)
            # Plot 'zero' highlight
            if 'zero' in s.marks:
                m1 = s.marks['zero'][0]
                m2 = m1 + s.marks['zero'][1]
                axes.plot(s.x[m1:m2], s.y[m1:m2], color=self.zero_color)
            # Show plot
            try:
                if self.checkBox_3.isChecked():
                    mplw.clearScaleHistory()
                    if not (y_max > y_min) and not (x_max > x_min):
                        mplw.autoRange()
            except:
                log_exception()
            # mplw.canvas.draw()
            jj += 1
        # Remove unused plot widgets
        while jj < layout.count():
            item = layout.takeAt(layout.count() - 1)
            if not item:
                continue
            w = item.widget()
            if w:
                layout.removeWidget(w)
                layout.removeItem(item)
                w.deleteLater()
                del w
        layout.update()
        # self.logger.debug('End %s', time.time() - t0)

    @property
    def plot_previous_line(self):
        return self.checkBox_2.isChecked()

    @property
    def show_toolbar(self):
        return self.checkBox_1.isChecked()

    @staticmethod
    def sort_text_edit_widget(widget):
        sorted_text = widget.toPlainText().split('\n')
        sorted_text.sort()
        text = ''
        for t in sorted_text:
            if t != '':
                text += t + '\n'
        widget.setPlainText(text)

    @staticmethod
    def from_params(name, source, default=''):
        result = ''
        try:
            if name in source:
                result = source[name]
            elif isinstance(name, str):
                result = source[name.encode()]
            elif isinstance(name, bytes):
                result = source[name.decode('ascii')]
            if isinstance(result, bytes):
                result = result.decode('ascii')
            return result
        except:
            return default

    def change_background(self, row=None, column=0, color=YELLOW):
        self.restore_background()
        try:
            if row is None:
                row = self.last_selection
            self.last_cell_background = self.tableWidget_3.item(row, column).background()
            self.last_cell_row = row
            self.last_cell_column = column
            self.tableWidget_3.item(row, column).setBackground(color)
        except:
            pass

    def restore_background(self, row=None, column=None, color=None):
        try:
            if row is None:
                row = self.last_cell_row
            if column is None:
                column = self.last_cell_column
            if color is None:
                color = self.last_cell_background
            if row >= 0 and column >= 0:
                self.tableWidget_3.item(row, column).setBackground(color)
        except:
            pass

    def update_status_bar(self):
        if self.log_file_name is not None and self.log_table is not None:
            self.sb_text.setText('File: %s' % self.log_file_name)
            if self.last_selection >= 0:
                self.change_background()
                last_sel_time = self.log_table(self.last_selection, "Time")['text']
                self.sb_prev_shot_time.setVisible(True)
                self.sb_prev_shot_time.setText(last_sel_time)
            else:
                self.restore_background()
                self.sb_prev_shot_time.setVisible(False)
                self.sb_prev_shot_time.setText("**:**:**")
            if self.current_selection >= 0:
                green_time = self.log_table(self.current_selection, "Time")['text']
                self.sb_green_time.setVisible(True)
                self.sb_green_time.setText(green_time)
            else:
                self.sb_green_time.setVisible(False)
                self.sb_green_time.setText('**:**:**')
        else:
            self.sb_text.setText('Data file not found')
            self.sb_prev_shot_time.setVisible(False)
            self.sb_green_time.setVisible(False)
            self.sb_prev_shot_time.setText('**:**:**')
            self.sb_green_time.setText('**:**:**')

    def file_selection_changed(self, m):
        self.logger.debug('File selection changed to %s' % m)
        if m < 0:
            return
        new_log_file = str(self.comboBox_2.currentText())
        new_log_file = os.path.abspath(new_log_file)
        if not os.path.exists(new_log_file):
            self.logger.warning('File %s not found' % new_log_file)
            self.comboBox_2.removeItem(m)
            return
        if self.log_file_name != new_log_file:
            self.logger.debug('New file selected %s' % new_log_file)
            self.save_local_settings()
            self.log_file_name = new_log_file
            # clear signal list
            self.signal_list = []
            self.old_signal_list = []
            self.last_selection = -1
            self.current_selection = -1
            self.restore_local_settings()
            self.plainTextEdit_3.setPlainText('')
            self.plainTextEdit_6.setPlainText('')
            if self.stackedWidget.currentIndex() == 0:
                self.parse_folder()

    def get_data_folder(self):
        if self.log_file_name is None:
            data_folder = "./"
        else:
            data_folder = os.path.dirname(self.log_file_name)
        return data_folder

    def restore_local_settings(self):
        if not self.checkBox_5.isChecked():
            return
        full_name = os.path.abspath(os.path.join(self.get_data_folder(), CONFIG_FILE))
        try:
            with open(full_name, 'r') as configfile:
                s = configfile.read()
            conf = json.loads(s)
            if 'included' in conf:
                self.plainTextEdit_2.setPlainText(conf['included'])
                self.conf['included'] = conf['included']
            if 'extra_plot' in conf:
                self.plainTextEdit_4.setPlainText(conf['extra_plot'])
                self.conf['extra_plot'] = conf['extra_plot']
            if 'extra_col' in conf:
                self.plainTextEdit_5.setPlainText(conf['extra_col'])
                self.conf['extra_col'] = conf['extra_col']
            if 'plot_order' in conf:
                self.plainTextEdit_7.setPlainText(conf['plot_order'])
                self.conf['plot_order'] = conf['plot_order']
            self.logger.info('Local configuration restored from %s' % full_name)
            return True
        except:
            log_exception('Local configuration restore error from %s' % full_name, level=logging.INFO)
            return False

    def save_local_settings(self):
        full_name = os.path.abspath(os.path.join(self.get_data_folder(), CONFIG_FILE))
        try:
            if not self.checkBox_5.isChecked():
                return
            conf = dict()
            conf['included'] = self.conf['included']
            conf['extra_plot'] = self.conf['extra_plot']
            conf['extra_col'] = self.conf['extra_col']
            conf['plot_order'] = self.conf['plot_order']
            with open(full_name, 'w') as configfile:
                configfile.write(json.dumps(conf, indent=4))
            self.logger.info('Local configuration saved to %s', full_name)
            return True
        except:
            log_exception('Local configuration save error to %s' % full_name)
            return False

    def log_level_index_changed(self, m: int) -> None:
        levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                  logging.WARNING, logging.ERROR, logging.CRITICAL]
        if m >= 0:
            self.logger.setLevel(levels[m])

    def on_quit(self):
        # save global settings
        # print(self.pos().x(), self.pos().y())
        self.save_local_settings()
        self.save_settings()
        timer.stop()

    def list_from_widget(self, widget):
        columns = widget.toPlainText().split('\n')
        return [col.strip() for col in columns if col.strip()]

    def get_displayed_columns(self):
        return self.list_from_widget(self.plainTextEdit_2)

    def sort_columns(self):
        included = self.get_displayed_columns()
        hidden = []
        columns = []
        # add from included
        for t in included:
            if t in self.log_table and t not in columns:
                columns.append(t)
        # create hidden columns list
        for t in self.log_table:
            if t not in columns:
                hidden.append(t)
        # sort hidden list
        hidden.sort()
        # set hidden columns text
        text = '\n'.join(hidden)
        self.plainTextEdit_3.setPlainText(text)
        return columns

    def get_extra_columns(self):
        return self.list_from_widget(self.plainTextEdit_5)

    def get_extra_plots(self):
        return self.list_from_widget(self.plainTextEdit_4)

    def parse_folder(self, file_name: str = None, append=False):
        try:
            if file_name is None:
                file_name = self.log_file_name
            if file_name is None:
                self.sb_text.setText('Data log file not found')
                self.logger.warning('Data log file not found')
                return
            file_name = os.path.abspath(file_name)
            self.sb_text.setText('Reading %s' % file_name)
            self.setCursor(QtCore.Qt.CursorShape.WaitCursor)
            self.logger.debug('Parsing %s', file_name)
            # get extra columns
            self.extra_cols = self.get_extra_columns()
            # process log table
            if self.log_table is None:
                self.logger.debug("Create new LogTable")
                self.log_table = LogTable()
                self.last_selection = -1
                self.current_selection = -1
            elif self.log_table.file_name == file_name:
                self.logger.debug("Appending to LogTable")
            else:
                self.logger.debug("Refill LogTable from new file")
                self.log_table.clear()
                self.last_selection = -1
                self.current_selection = -1
            n = self.log_table.read_file(file_name)
            if n is not None:
                self.log_table.add_extra_columns(self.extra_cols)
                self.log_file_name = file_name
                # Create displayed columns list
                self.fill_table_widget()
                self.logger.debug(f'{n} lines has been added to table')
                if n > 0:
                    # select last row of widget -> tableSelectionChanged will be fired
                    self.select_last_row()
                else:
                    self.tableWidget_3.selectRow(self.current_selection)
                    index = self.tableWidget_3.model().index(self.current_selection, 0)
                    self.tableWidget_3.scrollTo(index)
                    self.tableWidget_3.setFocus()
                    self.plot_signals()

        except KeyboardInterrupt:
            raise
        except:
            log_exception(self, 'Exception in parseFolder')
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self.update_status_bar()
        return

    def clear_table_widget(self):
        self.tableWidget_3.setUpdatesEnabled(False)
        self.tableWidget_3.itemSelectionChanged.disconnect(self.table_selection_changed)
        self.tableWidget_3.setRowCount(0)
        self.tableWidget_3.setColumnCount(0)
        self.tableWidget_3.setUpdatesEnabled(True)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)

    def create_table_widget_columns(self, columns):
        cln = 0
        for column in columns:
            self.tableWidget_3.insertColumn(cln)
            self.tableWidget_3.setHorizontalHeaderItem(cln, QTableWidgetItem(column))
            cln += 1

    def insert_column(self, label, index=-1):
        if index < 0:
            index = self.tableWidget_3.columnCount()
        self.tableWidget_3.insertColumn(index)
        self.tableWidget_3.setHorizontalHeaderItem(index, QTableWidgetItem(label))

    def fill_table_widget(self, append=-1):
        if append == 0:
            return
        # disable table widget update events
        self.tableWidget_3.setUpdatesEnabled(False)
        try:
            self.tableWidget_3.itemSelectionChanged.disconnect(self.table_selection_changed)
        except:
            log_exception(self)
        self.columns = self.sort_columns()
        if append < 0:
            # clear table widget
            self.tableWidget_3.setRowCount(0)
            self.tableWidget_3.setColumnCount(0)
        for column in self.columns[self.tableWidget_3.columnCount():]:
            index = self.tableWidget_3.columnCount()
            self.tableWidget_3.insertColumn(index)
            self.tableWidget_3.setHorizontalHeaderItem(index, QTableWidgetItem(column))
        row_range = range(self.tableWidget_3.rowCount(), self.log_table.rows)
        # insert and fill rows
        for row in row_range:
            self.tableWidget_3.insertRow(row)
            n = 0
            for column in self.columns:
                if column not in self.log_table:
                    continue
                try:
                    fmt = CONFIG['format'][column]
                    txt = fmt % (self.log_table.value(row, column), self.log_table.units(row, column))
                except:
                    txt = self.log_table.text(row, column)
                txt = txt.replace('none', '').replace('None', '')
                item = QTableWidgetItem(txt)
                item.setFont(CELL_FONT)
                # mark changed values
                if row > 0:
                    v = self.log_table.value(row, column)
                    v1 = self.log_table.value(row - 1, column)
                    bold_font_flag = True
                    if math.isnan(v) or math.isnan(v1):
                        bold_font_flag = False
                    else:
                        try:
                            thr = CONFIG['thresholds'][column]
                        except:
                            thr = 0.03
                        if thr > 0.0:
                            bold_font_flag = (v != 0.0) and (abs((v1 - v) / v) > thr)
                        elif thr < 0.0:
                            bold_font_flag = abs(v1 - v) > -thr
                    if bold_font_flag:
                        item.setFont(CELL_FONT_BOLD)
                self.tableWidget_3.setItem(row, n, item)
                n += 1
        # resize Columns
        self.tableWidget_3.resizeColumnsToContents()
        #
        # self.tableWidget_3.scrollToBottom()
        self.tableWidget_3.setFocus()
        # enable table widget update events
        self.tableWidget_3.setUpdatesEnabled(True)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)

    def save_settings(self, folder: str = '', file_name=None, config=None):
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
            # log file history
            config['folder'] = self.log_file_name
            config['history'] = [str(self.comboBox_2.itemText(count)) for count in
                                 range(min(self.comboBox_2.count(), 10))]
            config['history_index'] = min(self.comboBox_2.currentIndex(), 9)
            # other settings
            config['log_level'] = self.logger.level
            config['included'] = str(self.plainTextEdit_2.toPlainText())
            config['excluded'] = str(self.plainTextEdit_3.toPlainText())
            config['extra_plot'] = str(self.plainTextEdit_4.toPlainText())
            config['extra_col'] = str(self.plainTextEdit_5.toPlainText())
            config['exclude_plots'] = str(self.plainTextEdit_6.toPlainText())
            config['plot_order'] = str(self.plainTextEdit_7.toPlainText())
            config['cb_1'] = self.checkBox_1.isChecked()
            config['cb_2'] = self.checkBox_2.isChecked()
            config['cb_3'] = self.checkBox_3.isChecked()
            config['cb_4'] = self.checkBox_4.isChecked()
            config['cb_5'] = self.checkBox_5.isChecked()
            config['cb_6'] = self.checkBox_6.isChecked()
            # convert to json and write
            with open(full_name, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.debug('Configuration saved to %s' % full_name)
            return True
        except:
            log_exception('Error configuration save to %s' % full_name)
            return False

    # def resizeEvent(self, *args):
    #     print('resize', args, args[0].size())
    #     super().resizeEvent(*args)
    def restore_settings(self, folder='', file_name=None):
        self.conf = {
            'columns': 3,
            'w_height': 300,
            'w_width': 300
        }
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
                levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                          logging.WARNING, logging.ERROR, logging.CRITICAL]
                mm = 0
                for m in range(len(levels)):
                    if v <= levels[m]:
                        mm = m
                        break
                self.comboBox_1.setCurrentIndex(mm)
            # Restore window size and position
            if 'main_window' in self.conf:
                self.setMinimumSize(640, 480)  # resize hook
                self.resize(QSize(self.conf['main_window']['size'][0], self.conf['main_window']['size'][1]))
                self.move(QPoint(self.conf['main_window']['position'][0], self.conf['main_window']['position'][1]))
            # colors
            if 'colors' in self.conf:
                self.trace_color = self.conf['colors'].get('trace', self.trace_color)
                self.previous_color = self.conf['colors'].get('previous', self.previous_color)
                self.mark_color = self.conf['colors'].get('mark', self.mark_color)
                self.zero_color = self.conf['colors'].get('zero', self.zero_color)
            # Last folder
            if 'folder' in self.conf:
                self.log_file_name = self.conf['folder']
            if 'included' in self.conf:
                self.plainTextEdit_2.setPlainText(self.conf['included'])
            if 'excluded' in self.conf:
                self.plainTextEdit_3.setPlainText(self.conf['excluded'])
            if 'extra_plot' in self.conf:
                self.plainTextEdit_4.setPlainText(self.conf['extra_plot'])
            if 'extra_col' in self.conf:
                self.plainTextEdit_5.setPlainText(self.conf['extra_col'])
            if 'exclude_plots' in self.conf and hasattr(self, 'plainTextEdit_6'):
                self.plainTextEdit_6.setPlainText(self.conf['exclude_plots'])
            if 'plot_order' in self.conf and hasattr(self, 'plainTextEdit_7'):
                self.plainTextEdit_7.setPlainText(self.conf['plot_order'])
            if 'cb_1' in self.conf:
                self.checkBox_1.setChecked(self.conf['cb_1'])
            if 'cb_2' in self.conf:
                self.checkBox_2.setChecked(self.conf['cb_2'])
            if 'cb_3' in self.conf:
                self.checkBox_3.setChecked(self.conf['cb_3'])
            if 'cb_4' in self.conf:
                self.checkBox_4.setChecked(self.conf['cb_4'])
            if 'cb_5' in self.conf:
                self.checkBox_5.setChecked(self.conf['cb_5'])
            if 'cb_6' in self.conf:
                self.checkBox_6.setChecked(self.conf['cb_6'])
            if 'history' in self.conf:
                self.comboBox_2.currentIndexChanged.disconnect(self.file_selection_changed)
                self.comboBox_2.clear()
                self.comboBox_2.addItems(self.conf['history'])
                self.comboBox_2.currentIndexChanged.connect(self.file_selection_changed)
            if 'history_index' in self.conf:
                self.comboBox_2.setCurrentIndex(self.conf['history_index'])
            self.cut_long_names = self.conf.get('cut_long_names', True)
            self.conf['cut_long_names'] = self.cut_long_names
            self.fill_empty_lists = self.conf.get('fill_empty_lists', True)
            self.conf['fill_empty_lists'] = self.fill_empty_lists
            #
            if 'right_mouse_button' in self.conf:
                self.rmb = self.conf['right_mouse_button']
            #
            self.logger.debug('Configuration restored from %s' % full_name)
            return True
        except:
            log_exception('Configuration restore error from %s' % full_name)
            return False

    def config_selection_changed(self, index):
        global CONFIG_FILE
        old_config_file = CONFIG_FILE
        self.save_settings()
        self.save_local_settings()
        CONFIG_FILE = str(self.sb_combo.currentText())
        if not self.restore_settings():
            self.logger.error('Wrong config file %s - ignored' % CONFIG_FILE)
            CONFIG_FILE = old_config_file
            self.restore_settings()
            return
        self.restore_local_settings()

        layout = self.scrollAreaWidgetContents_3.layout()
        jj = 0
        # Remove unused plot widgets
        while jj < layout.count():
            item = layout.takeAt(layout.count() - 1)
            if not item:
                continue
            w = item.widget()
            if w:
                layout.removeWidget(w)
                layout.removeItem(item)
                w.deleteLater()
                del w
        layout.update()
        self.parse_folder()
        # self.table_selection_changed(True)

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
        self.save_local_settings()
        self.save_settings()
        a0.accept()

    def save_and_exit(self) -> None:
        self.save_local_settings()
        self.save_settings()
        QApplication.exit()
        # QApplication.quit()

    def timer_handler(self):
        # if self.resize_hook:
        #     w1 = self.conf['main_window']['size'][0]
        #     h1 = self.conf['main_window']['size'][1]
        #     self.resize(QSize(self.conf['main_window']['size'][0], self.conf['main_window']['size'][1]))
        #     s = self.size()
        #     p = self.pos()
        #     w = s.width()
        #     h = s.height()
        #     x = p.x()
        #     y = p.y()
        #     print('resize', w1, h1, w, h)
        #     # self.resize_hook = False
        t = time.strftime('%H:%M:%S')
        self.sb_clock.setText(t)
        # check if in parameters edit mode
        if self.stackedWidget.currentIndex() != 0:
            return
        # check if data file locked
        if self.is_locked():
            return
        # check if data file exists
        if not (os.path.exists(self.log_file_name) and os.path.isfile(self.log_file_name)):
            # self.logger.debug('Data file does not exist')
            return
        self.old_size = self.log_table.file_size
        self.new_size = os.path.getsize(self.log_file_name)
        if self.new_size <= self.old_size:
            return
        self.logger.debug('New shot detected')
        self.parse_folder()

    def select_last_row(self):
        # select last row
        if self.checkBox_4.isChecked() or self.current_selection < 0:
            self.logger.debug('Selection will be switched to last row')
            n = self.tableWidget_3.rowCount() - 1
            self.tableWidget_3.selectRow(n)
            self.tableWidget_3.scrollToBottom()
            self.tableWidget_3.setFocus()
        else:
            self.tableWidget_3.selectRow(self.current_selection)
            self.tableWidget_3.setFocus()
            self.logger.debug('Selection switch to last row rejected')


class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QFrame.Shape.VLine)


class Signal:
    def __init__(self, x=None, y=numpy.zeros(1), params: dict = None, name='empty_signal',
                 unit='', scale=1.0, value=float('nan'), marks: dict = None):
        self.logger = config_logger()
        self.data_name = name
        self.x = x
        self.y = y
        self.params = params
        self.name = name
        self.unit = unit
        self.scale = scale
        self.value = value
        self.marks = marks
        if x is None:
            x = numpy.zeros(1)
        elif isinstance(x, Signal):
            self.data_name = x.data_name
            marks = x.marks.copy()
            value = x.value
            scale = x.scale
            unit = x.unit
            name = x.name
            params = x.params.copy()
            y = x.y.copy()
            x = x.x.copy()

        if params is None:
            params = {}
        self.params = params

        if marks is None:
            marks = {}
        self.marks = marks

        self.name = name
        self.unit = unit
        self.scale = scale
        self.value = value

        self.x = x
        self.y = y
        self.trim()

        self.code = ''
        self.file = ''

    def __copy__(self):
        result = Signal()
        result.data_name = self.data_name
        result.marks = self.marks.copy()
        result.value = self.value
        result.scale = self.scale
        result.unit = self.unit
        result.name = self.name
        result.params = self.params.copy()
        result.y = self.y.copy()
        result.x = self.x.copy()
        return result

    def __str__(self):
        return f'Signal:<{self.data_name} = {self.name}; length = {len(self.x)}; value={self.value} {self.unit}>'

    def set_name(self, name: str):
        self.name = name
        return self

    def set_marks(self, marks: dict):
        self.marks = marks
        return self

    def set_value(self, value):
        self.value = value
        return self

    def set_unit(self, unit: str):
        self.unit = unit
        return self

    def set_data(self, x, y):
        self.x = x
        self.y = y
        self.trim()
        return self

    def trim(self):
        n = min(len(self.x), len(self.y))
        self.x = self.x[:n]
        self.y = self.y[:n]

    def calculate_marks(self):
        signal = self
        # find marks
        for k in signal.params:
            if k.endswith(b"_start"):
                mark_name = k.replace(b"_start", b'').decode('ascii')
                mark_length = k.replace(b"_start", b'_length')
                try:
                    if signal.params[k] != b'':
                        mark_start_value = float(signal.params[k].replace(b',', b'.'))
                        mark_end_value = mark_start_value + float(signal.params[mark_length].replace(b',', b'.'))
                        index = numpy.where(numpy.logical_and(signal.x >= mark_start_value, signal.x <= mark_end_value))
                        index = index[0]
                        if len(index) > 0:
                            mark_value = signal.y[index].mean()
                            mark_start = int(index[0])
                            mark_length = int(index[-1] - index[0]) + 1
                            signal.marks[mark_name] = (mark_start, mark_length, mark_value)
                            # self.logger.debug('%s(%s:%s) = %s', mark_name, mark_start, mark_start+mark_length, mark_value)
                except:
                    log_exception(self, 'Mark %s value can not be computed for %s' % (mark_name, signal.name),
                                  level=logging.INFO)

    def calculate_value(self):
        # calculate value
        s = self
        try:
            if math.isnan(s.value) and 'mark' in s.marks:
                mark = s.marks['mark']
                mark_value = s.y[mark[0]: mark[0] + mark[1]].mean()
                if 'zero' in s.marks:
                    zero = s.marks['zero']
                    zero_value = s.y[zero[0]: zero[0] + zero[1]].mean()
                else:
                    zero_value = 0.0
                v = mark_value - zero_value
                s.value = v
        except:
            self.value = float('nan')
            # self.logger.debug(f'No signal value for {s.name}')
        return self.value

    def __add__(self, other):
        result = Signal(self)
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result.x = args[0].x
            result.y = args[0].y + args[1].y
            result.value = self.value + other.value
            result.name = self.name + '+' + other.name
            result.data_name = self.data_name + '+' + other.data_name
        elif isinstance(other, int) or isinstance(other, float):
            result.y = self.y + other
            result.value = self.value + other
            result.name = self.name + '+' + str(other)
            result.data_name = self.data_name + '+' + str(other)
        result.calculate_value()
        result.calculate_marks()
        return result

    def __sub__(self, other):
        result = Signal(self)
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result.x = args[0].x
            result.y = args[0].y - args[1].y
            result.value = self.value - other.value
            result.name = self.name + '-' + other.name
            result.data_name = self.data_name + '-' + other.data_name
        elif isinstance(other, int) or isinstance(other, float):
            result.y = self.y - other
            result.value = self.value - other
            result.name = self.name + '-' + str(other)
            result.data_name = self.data_name + '-' + str(other)
        result.calculate_value()
        result.calculate_marks()
        return result

    def __mul__(self, other):
        result = Signal(self)
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result.x = args[0].x
            result.y = args[0].y * args[1].y
            result.value = self.value * other.value
            result.scale = self.scale * other.scale
            result.unit = self.unit + '*' + other.unit
            result.name = self.name + '*' + other.name
            result.data_name = self.data_name + '*' + other.data_name
        elif isinstance(other, int) or isinstance(other, float):
            result.y = self.y * other
            result.value = self.value * other
            result.name = self.name + '*' + str(other)
            result.data_name = self.data_name + '+' + str(other)
        result.calculate_value()
        result.calculate_marks()
        return result

    def __truediv__(self, other):
        result = Signal(self)
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result.x = args[0].x
            result.y = args[0].y / args[1].y
            result.value = self.value / other.value
            result.scale = self.scale / other.scale
            result.unit = self.unit + '/' + other.unit
            result.name = self.name + '/' + other.name
            result.data_name = self.data_name + '/' + other.data_name
        elif isinstance(other, int) or isinstance(other, float):
            result.y = self.y / other
            result.value = self.value / other
            result.name = self.name + '/' + str(other)
            result.data_name = self.data_name + '/' + str(other)
        result.calculate_value()
        result.calculate_marks()
        return result

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, key, value):
        self.params[key] = value

    def read_from_file(self, signal_name: str, file_name: str):
        if file_name.endswith('.zip'):
            with zipfile.ZipFile(file_name, 'r') as zipobj:
                buf = zipobj.read(signal_name)
                param_name = signal_name.replace('chan', 'paramchan')
                pbuf = zipobj.read(param_name)
        else:
            with open(file_name, 'rb') as datafile:
                buf = datafile.read()
                pbuf = b''
        signal = self
        if b'\r\n' in buf:
            endline = b"\r\n"
        else:
            buf = buf.replace(b'\r', b'\n')
            endline = b'\n'
        lines = buf.split(endline)
        n = len(lines)
        if n < 2:
            # self.logger.debug("%s Not a signal" % signal_name)
            return None
        signal.x = numpy.zeros(n, dtype=numpy.float64)
        signal.y = numpy.zeros(n, dtype=numpy.float64)
        error_lines = False
        xy = []
        for i, line in enumerate(lines):
            xy = line.replace(b',', b'.').split(b'; ')
            if len(xy) > 1:
                try:
                    signal.x[i] = float(xy[0])
                except:
                    signal.x[i] = numpy.nan
                    error_lines = True
                try:
                    signal.y[i] = float(xy[1])
                except:
                    signal.y[i] = numpy.nan
                    error_lines = True
            elif len(xy) > 0:
                signal.x[i] = i
                try:
                    signal.y[i] = float(xy[0])
                except:
                    signal.y[i] = numpy.nan
                    error_lines = True
        if len(xy) < 2:
            signal.params[b'xlabel'] = 'Index'
        # read parameters
        signal.params = {}
        lines = pbuf.split(endline)
        error_lines = False
        kv = ''
        for line in lines:
            if line != b'':
                kv = line.split(b'=')
                if len(kv) >= 2:
                    signal.params[kv[0].strip()] = kv[1].strip()
                else:
                    error_lines = kv
        # scale to units
        try:
            signal.scale = float(signal.params[b'display_unit'])
        except:
            signal.scale = 1.0
        signal.y *= signal.scale
        # name of the signal
        if b"label" in signal.params:
            signal.name = signal.params[b"label"].decode('ascii')
        elif b"name" in signal.params:
            signal.name = signal.params[b"name"].decode('ascii')
        else:
            signal.name = signal_name
        signal.data_name = signal_name
        if b'unit' in signal.params:
            signal.unit = signal.params[b'unit'].decode('ascii')
        else:
            signal.unit = ''
        # find marks
        signal.calculate_marks()
        # calculate value
        signal.calculate_value()
        signal.file = file_name
        signal.code = ''
        return signal

    def decode_data(self, buf: bytes):
        signal = self
        if b'\r\n' in buf:
            endline = b"\r\n"
        else:
            buf = buf.replace(b'\r', b'\n')
            endline = b'\n'
        lines = buf.split(endline)
        n = len(lines)
        if n < 2:
            # self.logger.debug("%s Not a signal" % signal_name)
            return None
        signal.x = numpy.zeros(n, dtype=numpy.float64)
        signal.y = numpy.zeros(n, dtype=numpy.float64)
        xy = []
        for i, line in enumerate(lines):
            xy = line.replace(b',', b'.').split(b'; ')
            if len(xy) > 1:
                try:
                    signal.x[i] = float(xy[0])
                except:
                    signal.x[i] = numpy.nan
                    error_lines = True
                try:
                    signal.y[i] = float(xy[1])
                except:
                    signal.y[i] = numpy.nan
                    error_lines = True
            elif len(xy) > 0:
                signal.x[i] = i
                try:
                    signal.y[i] = float(xy[0])
                except:
                    signal.y[i] = numpy.nan
        if len(xy) < 2:
            signal.params[b'xlabel'] = 'Index'
        return signal

    def decode_parameters(self, buf: bytes):
        signal = self
        if b'\r\n' in buf:
            endline = b"\r\n"
        else:
            buf = buf.replace(b'\r', b'\n')
            endline = b'\n'
        signal.params = {}
        lines = buf.split(endline)
        for line in lines:
            if line != b'':
                kv = line.split(b'=')
                if len(kv) >= 2:
                    signal.params[kv[0].strip()] = kv[1].strip()
        return signal


@lru_cache()
def read_signal_list(file_name: str):
    # print('Reading from', file_name)
    with zipfile.ZipFile(file_name, 'r') as zipobj:
        files = zipobj.namelist()
    return files


@lru_cache(maxsize=512)
def read_signal(signal_name: str, file_name: str):
    # print('Reading', signal_name, 'from', file_name)
    files = read_signal_list(file_name)
    signal = Signal()
    with zipfile.ZipFile(file_name, 'r') as zipobj:
        buf = zipobj.read(signal_name)
    # if b'\r\n' in buf:
    #     endline = b"\r\n"
    # else:
    #     buf = buf.replace(b'\r', b'\n')
    #     endline = b'\n'
    # lines = buf.split(endline)
    if len(buf) < 2:
        return None
    lines = buf.splitlines()
    n = len(lines)
    if n < 2:
        # log("%s Not a signal" % signal_name)
        return None
    if lines[-1].strip() == '':
        return None
    signal.x = numpy.zeros(n, dtype=numpy.float64)
    signal.y = numpy.zeros(n, dtype=numpy.float64)
    xy = []
    error_lines = []
    for i, line in enumerate(lines):
        xy = line.replace(b',', b'.').split(b';')
        if len(xy) > 1:
            try:
                signal.x[i] = float(xy[0])
            except:
                signal.x[i] = numpy.nan
                error_lines.append(i)
            try:
                signal.y[i] = float(xy[1])
            except:
                signal.y[i] = numpy.nan
                error_lines.append(i)
        elif len(xy) > 0:
            signal.x[i] = i
            try:
                signal.y[i] = float(xy[0])
            except:
                signal.y[i] = numpy.nan
                error_lines.append(i)
        else:
            error_lines.append(i)
            # signal.x[i] = numpy.nan
            # signal.y[i] = numpy.nan
    # read parameters
    signal.params = {}
    if len(xy) < 2:
        signal.params[b'xlabel'] = 'Index'
    param_name = signal_name.replace('chan', 'paramchan')
    if param_name == signal_name or param_name not in files:
        param_name = signal_name.replace('.txt', '_parameters.txt')
    if param_name == signal_name or param_name not in files:
        param_name = signal_name.replace('/', '/param')
    if param_name != signal_name and param_name in files:
        with zipfile.ZipFile(file_name, 'r') as zipobj:
            pbuf = zipobj.read(param_name)
        lines = pbuf.splitlines()
        for line in lines:
            if line.strip() != b'':
                kv = line.split(b'=')
                if len(kv) >= 2:
                    signal.params[kv[0].strip()] = kv[1].strip()
                else:
                    error_lines.append(kv)
    # scale to units
    try:
        signal.scale = float(signal.params[b'display_unit'])
    except:
        signal.scale = 1.0
    signal.y *= signal.scale
    # name of the signal
    if b"label" in signal.params:
        signal.name = signal.params[b"label"].decode('ascii')
    elif b"name" in signal.params:
        signal.name = signal.params[b"name"].decode('ascii')
    else:
        signal.name = signal_name
    signal.data_name = signal_name
    if b'unit' in signal.params:
        signal.unit = signal.params[b'unit'].decode('ascii')
    else:
        signal.unit = ''
    # find marks
    signal.calculate_marks()
    # calculate value
    signal.calculate_value()
    signal.file = file_name
    signal.code = ''
    return signal


class DataFile:
    signals = {}
    files = {}

    def __init__(self, file_name, folder="", logger=None, plot_cache=None):
        if logger is None:
            self.logger = config_logger()
        else:
            self.logger = logger
        self.plot_cache = plot_cache
        self.file_name = None
        self.files = []
        self.signals = []
        full_name = os.path.abspath(os.path.join(folder, file_name))
        try:
            self.files = read_signal_list(full_name)
        except:
            log_exception('Corrupt zip file %s', full_name)
            self.files = []
        self.signals = self.find_signals()
        self.file_name = full_name

    def find_signals(self):
        signals = []
        for f in self.files:
            if 'param' not in f:
                if f not in self.signals:
                    signals.append(f)
        return signals

    def read_signal(self, signal_name: str):
        signal = read_signal(signal_name, self.file_name)
        return signal

    def read_all_signals(self):
        signals = []
        # signal_names = []
        for s in self.signals:
            sig = self.read_signal(s)
            if sig:
                signals.append(sig)
        return signals


def justify_signals(first: Signal, other: Signal):
    if len(first.x) == len(other.x) and \
            first.x[0] == other.x[0] and first.x[-1] == other.x[-1]:
        return first, other
    xmin = max(first.x.min(), other.x.min())
    xmax = min(first.x.max(), other.x.max())
    index1 = numpy.logical_and(first.x >= xmin, first.x <= xmax).nonzero()[0]
    index2 = numpy.logical_and(other.x >= xmin, other.x <= xmax).nonzero()[0]
    result = (Signal(first), Signal(other))
    if len(index1) >= len(index2):
        x = first.x[index1].copy()
        result[1].y = numpy.interp(x, other.x, other.y)
        result[0].x = x
        result[0].y = first.y[index1].copy()
        result[1].x = x
    else:
        x = other.x[index2].copy()
        result[0].y = numpy.interp(x, first.x, first.y)
        result[0].x = x
        result[1].y = other.y[index2].copy()
        result[1].x = x
    return result


def common_marks(first: Signal, other: Signal):
    result = {}
    for mark in first.marks:
        if mark in other.marks:
            fi = first.marks[mark]
            ot = other.marks[mark]
            m1 = max(fi[0], ot[0])
            m2 = min(fi[0] + fi[1], ot[0] + ot[1])
            if m2 > m1:
                v = float('nan')
                result[mark] = (m1, m2 - m1, v)
    return result


def unify_marks(first: Signal, other: Signal):
    result = {}
    cm = common_marks(first, other)
    for mark in first.marks:
        if mark in other.marks:
            result[mark] = cm[mark]
        else:
            result[mark] = first.marks[mark]
    for mark in other.marks:
        if mark not in result:
            result[mark] = other.marks[mark]
    return result


class LogTable:
    EMTPY_CELL = {'text': '', 'value': float('nan'), 'units': ''}

    def __init__(self, file_name: str = None, extra_cols=None, logger=None, **kwargs):
        if logger is None:
            self.logger = config_logger()
        else:
            self.logger = logger
        self.columns = {}
        self.rows = 0
        self.decode = lambda x: bytes.decode(x, 'cp1251')
        self.file_name = None
        self.file_size = 0
        if file_name is not None:
            self.read_file(file_name)
        self.exrta_columns = {}
        if extra_cols is not None:
            self.add_extra_columns(extra_cols)

    def clear(self):
        self.columns = {}
        self.rows = 0
        self.file_size = 0
        self.file_name = None
        self.exrta_columns = {}

    def keys(self):
        return self.columns.keys()

    def get_column(self, col):
        return self.columns[col]

    def get_row(self, n):
        return {key: val[n] for (key, val) in self.columns}

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            a0 = args[0]
            if isinstance(a0, str):
                return self.get_column(a0)
            elif isinstance(a0, int):
                return self.get_row(a0)
        elif len(args) == 2:
            a0 = args[0]
            a1 = args[1]
            return self.columns[a1][a0]
        raise ValueError('Wrong arguments')

    def __len__(self):
        return len(self.columns)

    def add_column(self, key, data=None):
        if key not in self.columns:
            if not data:
                self.columns[key] = [self.EMTPY_CELL] * self.rows
            else:
                if len(data) != self.rows:
                    raise ValueError(f"Wrong insert data for {key}")
                self.columns[key] = data
        return self.columns[key]

    def remove_column(self, key):
        del self.columns[key]

    def decode_line(self, line):
        row = {}
        #  detect DO_NOT_SHOW tag
        if 'DO_NOT_SHOW_LINE' in line or 'DO_NOT_SHOW = True' in line or 'DO_NOT_SHOW=True' in line:
            # self.logger.info(f'DO_NOT_SHOW tag detected in {line[11:20]}')
            row[-1] = True
        else:
            row[-1] = False
        # Split line to fields
        fields = line.split("; ")
        # First field "date time" should be longer than 18 symbols
        if len(fields) < 2 or len(fields[0]) < 19:
            # Wrong line format, skip to next line
            self.logger.info('Wrong data format in "%s", line skipped' % line[11:20])
            return None
        # split time and date
        tm = fields[0].split(" ")[1].strip()
        # preserve only time
        fields[0] = "Time=" + tm
        # iterate rest fields for key=value pairs
        keys_with_errors = []
        dup_flag = True
        for field in fields:
            kv = field.split("=")
            key = kv[0].strip()
            val = kv[1].strip()
            if key in row:
                if dup_flag:
                    self.logger.warning('Duplicate key "%s" in line "%s ..."', key, line[:25])
                    dup_flag = False
                keys_with_errors.append(key)
            else:
                row[key] = {'text': val}
                # split value and units
                vu = val.split(" ")
                # value
                try:
                    v = float(vu[0].strip().replace(',', '.'))
                    if key in keys_with_errors:
                        keys_with_errors.remove(key)
                except:
                    v = float('nan')
                    if key != 'Time' and key != 'File' and key not in keys_with_errors:
                        self.logger.debug('Non float value in "%s"' % field)
                        keys_with_errors.append(key)
                row[key]['value'] = v
                # units
                try:
                    u = vu[1].strip()
                except:
                    u = ''
                row[key]['units'] = u
            row[-2] = keys_with_errors
        return row

    def append_lines(self, buf):
        if not buf or len(buf) <= 0:
            self.logger.debug('Empty buffer')
            return 0
        lines = buf.split('\n')
        # loop for lines
        n = 0
        for line in lines:
            line = line.strip()
            if line != '':
                row = self.decode_line(line)
                if row:
                    self.add_row(row)
                    n += 1
        self.logger.debug('%d of %d lines has been appended' % (n, len(lines)))
        return n

    def add_row(self, row: dict):
        for key in row:
            self.add_column(key)
        for key in self.columns:
            if key in row:
                self.columns[key].append(row[key])
            else:
                self.columns[key].append(self.EMTPY_CELL)
        self.rows += 1
        return self.rows

    def remove_row(self, index: int):
        for key in self.columns:
            del self.columns[key][index]
        self.rows -= 1
        return self.rows

    def update_row(self, index: int, row: dict):
        self.columns[index].update(row)
        return self.rows

    def text(self, row, col, fmt=None):
        v = self.columns[col][row]
        if not fmt:
            return v['text']
        else:
            return fmt % (v['value'], v['units'])

    def value(self, row, col):
        return self.columns[col][row]['value']

    def units(self, row, col):
        return self.columns[col][row]['units']

    def get_cell(self, row, col):
        return self.columns[col][row]

    def set_cell(self, row, col, value):
        self.columns[col][row] = value

    def show_line_flag(self, row: int):
        return self.columns[-1][row]

    def __contains__(self, item):
        return item in self.columns

    def __iter__(self):
        return [key for key in self.columns if isinstance(key, str)].__iter__()

    def read_file(self, file_name: str = None):
        if file_name is None:
            file_name = self.file_name
        if file_name is None:
            self.logger.warning(f'None file can not be opened')
            return None
        fn = os.path.abspath(file_name)
        if not os.path.exists(fn):
            self.logger.warning('File %s does not exist' % fn)
            return None
        fs = os.path.getsize(fn)
        if fs < 20:
            self.logger.warning('Wrong file size for %s' % fn)
            return None
        if self.file_name == fn and fs == self.file_size:
            self.logger.debug('Nothing to read from %s' % fn)
            return 0
        self.logger.debug(f'File {fn} {fs} bytes will be processed')
        # read file to buf
        try:
            with open(fn, "rb") as stream:
                if self.file_name == fn:
                    self.logger.debug(f'Positioning to {self.file_size}')
                    stream.seek(self.file_size)
                buf = stream.read()
            self.logger.debug(f'{len(buf)} bytes has been red')
            bufd = self.decode(buf)
            if self.file_name != fn:
                self.clear()
            self.file_name = fn
            self.file_size = fs
            n = self.append_lines(bufd)
            return n
        except:
            log_exception(self.logger, 'Data file %s can not be opened' % fn)
            return None

    def add_extra_columns(self, extra_cols):

        def value(x, y=None):
            if y is None:
                y = row
            return self.value(y, x)

        #
        rows_with_error = []
        for column in extra_cols:
            if not column or column.strip() == '':
                continue
            h = column.__hash__()
            n = 0
            key0 = None
            if h in self.exrta_columns:
                key0 = self.exrta_columns[h]['name']
            key = ''
            for row in range(0, self.rows):
                try:
                    key, v, u = eval(column)
                    if not key or not isinstance(key, str):
                        self.logger.info('Wrong name for column %s' % column)
                        break
                    if key0 is None:
                        if key in self.columns:
                            self.logger.debug(f'Column {key} will be overwritten by {column}')
                        #     break
                        key0 = key
                        self.add_column(key0)
                    if key != key0:
                        raise KeyError('Wrong name for column %s' % column)
                    else:
                        self.columns[key0][row] = {'text': str(v), 'value': float(v), 'units': str(u)}
                        n += 1
                except:
                    if not rows_with_error:
                        log_exception(self.logger, 'Column eval() error in "%s ..."\n', column[:20], level=logging.INFO)
                    rows_with_error.append(row)
            self.exrta_columns[h] = {'name': key0, 'code': column, 'length': n, 'errors': rows_with_error}
            self.exrta_columns[key0] = h
            if rows_with_error:
                self.logger.warning(f'Errors creation extra column for "{column[:20]} ..."')
            else:
                self.logger.debug(f'Extra column {key} has been added {n} lines')


if __name__ == '__main__':
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    if len(sys.argv) >= 2:
        CONFIG_FILE = sys.argv[1]
    # import matplotlib
    # matplotlib.rcParams['path.simplify'] = True
    # matplotlib.rcParams['path.simplify_threshold'] = 1.0
    # import matplotlib.style as mplstyle
    # mplstyle.use('fast')
    # create the GUI application
    app = QApplication(sys.argv)
    # app.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    # app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    # app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    # app.setAttribute(QtCore.Qt.AA_Use96Dpi)
    # instantiate the main window
    dmw = MainWindow()
    # connect quit processing code
    # app.aboutToQuit.connect(dmw.on_quit)
    # show main window
    dmw.show()
    # defile and start timer task
    timer = QTimer()
    timer.timeout.connect(dmw.timer_handler)
    timer.start(1000)
    # dmw.resize(QSize(dmw.conf['main_window']['size'][0], dmw.conf['main_window']['size'][1]))

    # start the Qt main loop execution,
    exec_result = app.exec_()
    # exiting from this script with the same return code of Qt application
    sys.exit(exec_result)
