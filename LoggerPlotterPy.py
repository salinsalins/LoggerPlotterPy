# coding: utf-8
"""
Created on Jul 2, 2017

@author: sanin
"""

import gc
import json
import logging
import math
import os
import os.path
import sys
import time
import zipfile
import datetime

import numpy

# os.environ['QT_API'] = 'pyqt5'
# os.environ['QT_API'] = 'pyside6'
# from qt import *

import PyQt5
from PyQt5 import QtGui
from PyQt5.QtGui import QFont
from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, QSize
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QFrame, QMenu
from PyQt5.QtWidgets import QLabel, QComboBox, QMessageBox
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView

from QtUtils import WidgetLogHandler
# from mplwidget import MplWidget
from pyqtgraphwidget import MplWidget

sys.path.append('../TangoUtils')
from Configuration import Configuration
from config_logger import config_logger, LOG_FORMAT_STRING_SHORT
from log_exception import log_exception

np = numpy

# print(QtCore.QT_VERSION_STR)

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'Plotter for Signals from Dumper'
APPLICATION_NAME_SHORT = 'LoggerPlotterPy'
APPLICATION_VERSION = '9.5'
VERSION_DATE = "17-11-2022"
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'
# fonts
CELL_FONT = QFont('Open Sans', 14)
CELL_FONT_BOLD = QFont('Open Sans', 14, weight=QFont.Bold)
STATUS_BAR_FONT = CELL_FONT
CLOCK_FONT = CELL_FONT_BOLD
# colors
WHITE = QtGui.QColor(255, 255, 255)
YELLOW = QtGui.QColor(255, 255, 0)
GREEN = QtGui.QColor(0, 255, 0)
PREVIOUS_COLOR = '#ffff00'
TRACE_COLOR = '#00ff00'
MARK_COLOR = '#ff0000'
ZERO_COLOR = '#0000ff'

# Global configuration dictionary
config = Configuration(CONFIG_FILE)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # colors
        self.previous_color = PREVIOUS_COLOR
        self.trace_color = TRACE_COLOR
        self.mark_color = MARK_COLOR
        self.zero_color = ZERO_COLOR
        #
        self.log_file_name = None
        self.data_root = None
        self.conf = {}
        self.refresh_flag = False
        self.last_selection = -1
        self.current_selection = -1
        self.signal_list = []
        self.old_signal_list = []
        self.signals = []
        self.extra_cols = []
        self.data_file = None
        self.old_size = 0
        self.new_size = 0
        self.included = []
        self.excluded = []
        self.columns = []
        self.last_cell_background = None
        self.last_cell_row = None
        self.last_cell_column = None
        self.log_table = None
        # Configure logging
        self.logger = config_logger(level=logging.INFO, format_string=LOG_FORMAT_STRING_SHORT)
        # Load the UI
        uic.loadUi(UI_FILE, self)
        # Connect signals with the slots
        self.pushButton_2.clicked.connect(self.select_log_file)
        self.comboBox_2.currentIndexChanged.connect(self.file_selection_changed)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
        # self.tableWidget_3.focusChanged.connect(self.set_focus)
        self.comboBox_1.currentIndexChanged.connect(self.log_level_index_changed)
        # Menu actions connection
        self.actionQuit.triggered.connect(self.save_and_exit)
        self.actionToday.triggered.connect(self.select_today_file)
        self.actionOpen.triggered.connect(self.select_log_file)
        self.actionPlot.triggered.connect(self.show_plot_pane)
        self.actionParameters.triggered.connect(self.show_param_pane)
        self.actionAbout.triggered.connect(self.show_about)
        # main window decoration
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.setWindowTitle(APPLICATION_NAME + APPLICATION_VERSION)
        # table: header
        header = self.tableWidget_3.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(QHeaderView.Interactive)
        # table: header right click menu
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
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
        # status bar
        self.statusBar().reformat()
        self.statusBar().setStyleSheet('border: 0;')
        self.statusBar().setStyleSheet("QStatusBar::item {border: none;}")
        # status bar: font
        self.statusBar().setFont(STATUS_BAR_FONT)
        # status bar: previous shot time
        self.sb_prev_shot_time = QLabel("**:**:**")
        self.sb_prev_shot_time.setFont(STATUS_BAR_FONT)
        self.sb_prev_shot_time.setStyleSheet('border: 0; color:  black; background: yellow;')
        self.sb_prev_shot_time.setText("**:**:**")
        self.sb_prev_shot_time.setVisible(False)
        self.statusBar().addWidget(self.sb_prev_shot_time)
        self.statusBar().addWidget(VLine())  # <---
        # status bar: green trace time
        self.sb_green_time = QLabel("**:**:**")
        self.sb_green_time.setFont(STATUS_BAR_FONT)
        self.sb_green_time.setStyleSheet('border: 0; color:  black; background: green;')
        self.sb_green_time.setText("**:**:**")
        self.sb_green_time.setVisible(False)
        self.statusBar().addWidget(self.sb_green_time)
        self.statusBar().addWidget(VLine())  # <---
        # status bar: config select combo
        self.sb_combo = QComboBox(self.statusBar())
        self.sb_combo.setFont(STATUS_BAR_FONT)
        self.statusBar().addWidget(self.sb_combo)
        self.statusBar().addWidget(VLine())  # <---
        self.sb_combo.disconnect()
        self.sb_combo.clear()
        arr = os.listdir()
        jsonarr = [x for x in arr if x.endswith('.json')]
        for x in jsonarr:
            if CONFIG_FILE in x:
                jsonarr.pop(jsonarr.index(x))
                jsonarr.insert(0, x)
        self.sb_combo.addItems(jsonarr)
        self.sb_combo.currentIndexChanged.connect(self.config_selection_changed)
        # status bar: clock label
        self.statusBar().addPermanentWidget(VLine())  # <---
        self.sb_clock = QLabel(" ")
        self.sb_clock.setFont(CLOCK_FONT)
        self.statusBar().addPermanentWidget(self.sb_clock)
        # status bar: message with data file name
        self.sb_text = QLabel("")
        self.sb_text.setFont(STATUS_BAR_FONT)
        self.statusBar().addWidget(self.sb_text)
        self.statusBar().addWidget(VLine())  # <---
        self.sb_text.setText("Starting...")
        # status bar: log show widget and connect logger to status bar
        self.sb_log = QLabel("")
        self.sb_log.setFont(STATUS_BAR_FONT)
        self.sb_log.time = time.time()
        self.statusBar().addWidget(self.sb_log)
        sbhandler = WidgetLogHandler(self.sb_log)
        sbhandler.setLevel(logging.INFO)
        self.logger.addHandler(sbhandler)
        # status bar: END

        # default settings
        self.set_default_settings()
        #
        print(APPLICATION_NAME, 'version', APPLICATION_VERSION, 'started')

        # restore settings
        self.restore_settings()
        self.restore_local_settings()
        # additional decorations
        self.tableWidget_3.horizontalHeader().setVisible(True)

        self.extra_cols = self.plainTextEdit_5.toPlainText().split('\n')
        self.log_table = LogTable(self.log_file_name, extra_cols=self.extra_cols,
                                  show_line_flag=self.checkBox_6.isChecked())
        if self.log_table.file_name is None:
            return
        self.log_file_name = self.log_table.file_name
        # Create displayed columns list
        self.columns = self.sort_columns()
        self.fill_table_widget()
        # select last row of widget -> tableSelectionChanged will be fired
        self.select_last_row()

    def set_focus(self, n):
        self.logger.debug('******** Enter %s', n)

    def table_header_right_click_menu(self, n):
        # print('menu', n)
        cursor = QtGui.QCursor()
        position = cursor.pos()
        # position = n
        menu = QMenu()
        hide_action = menu.addAction("Hide column")
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
        if action == hide_action:
            # print("Hide", n)
            # remove from shown columns list
            t = self.tableWidget_3.horizontalHeaderItem(n).text()
            text = self.plainTextEdit_2.toPlainText()
            t1 = '\n' + t
            t2 = t + '\n'
            t3 = t1 + '\n'
            if t3 in text:
                text = text.replace(t3, '\n')
            elif text.startswith(t2):
                text = text.replace(t2, '')
            elif text.endswith(t1):
                text = text.replace(t1, '')
            else:
                text = text.replace(t, '')
            text = text.replace('\n\n', '\n')
            self.plainTextEdit_2.setPlainText(text)
            # add to hidden columns list (unsorted!)
            text = self.plainTextEdit_3.toPlainText()
            self.plainTextEdit_3.setPlainText(text + t + '\n')
            # hide column
            self.tableWidget_3.hideColumn(n)
        if n > 1 and action == left_action:
            # print("Move Left", n)
            t1 = self.tableWidget_3.horizontalHeaderItem(n).text()
            t2 = self.tableWidget_3.horizontalHeaderItem(n - 1).text()
            text = self.plainTextEdit_2.toPlainText()
            text = text.replace(t1, '*+-=*')
            text = text.replace(t2, t1)
            text = text.replace('*+-=*', t2)
            self.plainTextEdit_2.setPlainText(text)
            self.columns = self.sort_columns()
            self.fill_table_widget()
            self.tableWidget_3.selectRow(self.current_selection)
            self.change_background()
        if n < self.tableWidget_3.columnCount() - 1 and action == right_action:
            # print("Move Right", n)
            t1 = self.tableWidget_3.horizontalHeaderItem(n).text()
            t2 = self.tableWidget_3.horizontalHeaderItem(n + 1).text()
            text = self.plainTextEdit_2.toPlainText()
            text = text.replace(t1, '****')
            text = text.replace(t2, t1)
            text = text.replace('****', t2)
            self.plainTextEdit_2.setPlainText(text)
            self.columns = self.sort_columns()
            self.fill_table_widget()
            self.tableWidget_3.selectRow(self.current_selection)
            self.change_background()

    def table_header_right_click_menu_wrap(self, a, *args):
        # i = self.tableWidget_3.horizontalHeader().currentIndex()
        # print('test', a, args)
        # h = self.tableWidget_3.horizontalHeader()
        # mouse_state = app.mouseButtons()
        # print(int(mouse_state))
        n = self.tableWidget_3.columnAt(a.x())
        if n > 0:
            self.table_header_right_click_menu(n)

    def refresh_on(self):
        self.refresh_flag = True

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + 'version ' + APPLICATION_VERSION +
                                '\nShows saved shot logs and plot traces.', QMessageBox.Ok)

    def show_plot_pane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionParameters.setChecked(False)
        self.save_local_settings()
        self.save_settings()
        # self.table_selection_changed(True)
        self.refresh_flag = False
        self.parse_folder()

    def show_param_pane(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionParameters.setChecked(True)
        self.sort_text_edit_widget(self.plainTextEdit_3)
        self.sort_text_edit_widget(self.plainTextEdit_6)

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
        # if it is the same file as being used
        if self.log_file_name == fn:
            return
        # different file selected
        i = self.comboBox_2.findText(fn)
        if i < 0:
            # add file name to history
            self.comboBox_2.insertItem(-1, fn)
            i = 0
            self.comboBox_2.setCurrentIndex(i)
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
        if self.last_selection == row_s:
            self.logger.debug('Selection unchanged')
            return row_s
        # different row selected
        self.logger.debug('Selection changed to row %i', row_s)
        return row_s

    def sig(self, name):
        for sg in self.signal_list:
            if sg.name == name:
                return sg
        raise ValueError('Signal %s not found' % name)
        # return None

    def table_selection_changed(self, force=False):
        sig = self.sig
        row_s = self.get_selected_row(self.tableWidget_3)
        if row_s < 0:
            return
        if force or self.current_selection != row_s:
            gc.collect()
            self.scrollAreaWidgetContents_3.setUpdatesEnabled(False)
            self.tableWidget_3.setUpdatesEnabled(False)
            self.restore_background()
            self.last_selection = self.current_selection
            try:
                # read signals from zip file
                folder = os.path.dirname(self.log_file_name)
                zip_file_name = self.log_table.column("File")[row_s]
                self.logger.debug('Using zip File %s', zip_file_name)
                self.data_file = DataFile(zip_file_name, folder=folder)
                self.old_signal_list = self.signal_list
                self.signal_list = self.data_file.read_all_signals()
                # add extra plots
                self.calculate_extra_plots()
                self.signals = self.sort_plots()
                self.plot_signals()
                self.current_selection = row_s
                self.update_status_bar()
            except:
                log_exception(self)
            finally:
                self.tableWidget_3.setUpdatesEnabled(True)
                self.scrollAreaWidgetContents_3.setUpdatesEnabled(True)
                # self.update_status_bar()

    def calculate_extra_plots(self):
        def sig(name):
            for sg in self.signal_list:
                if sg.name == name:
                    return sg
            raise ValueError('Signal %s not found' % name)
            # return None

        # add extra plots from plainTextEdit_4
        extra_plots = self.plainTextEdit_4.toPlainText().split('\n')
        for p in extra_plots:
            p = p.strip()
            if p != "":
                try:
                    s = None
                    result = eval(p)
                    if isinstance(result, Signal):
                        s = result
                    elif isinstance(result, dict):
                        key = result['name']
                        x = result['x']
                        y = result['y']
                        if key != '':
                            marks = result.get('marks', None)
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
                    if s is not None:
                        try:
                            if math.isnan(s.value) and 'mark' in s.marks and 'zero' in s.marks:
                                mark = s.marks['mark']
                                mark_value = s.y[mark[0], mark[0] + mark[1]].mean()
                                zero = s.marks['mark']
                                zero_value = s.y[zero[0], zero[0] + zero[1]].mean()
                                v = mark_value - zero_value
                                s.value = v
                        except:
                            pass
                        self.signal_list.append(s)
                    else:
                        self.logger.info('Can not calculate signal for "%s ..."', p[:10])
                except:
                    log_exception(self, 'Plot eval() error in "%s ..."' % p[:10], level=logging.INFO)

    def sort_plots(self):
        plot_order = self.plainTextEdit_7.toPlainText().split('\n')
        hidden_plots = []
        ordered_plots = []
        for p in plot_order:
            for s in self.signal_list:
                if s.name == p:
                    ordered_plots.append(self.signal_list.index(s))
                    break
        # build list of hidden plots
        for s in self.signal_list:
            if self.signal_list.index(s) not in ordered_plots:
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
            signals = self.signals
        # plot signals
        # t0 = time.time()
        # self.logger.debug('Begin')
        layout = self.scrollAreaWidgetContents_3.layout()
        jj = 0
        col = 0
        row = 0
        col_count = 3
        for c in signals:
            s = self.signal_list[c]
            # Use existing plot widgets or create new
            if jj < layout.count():
                # use existing plot widget
                mplw = layout.itemAt(jj).widget()
            else:
                # create new plot widget
                mplw = MplWidget(height=300, width=300)
                mplw.ntb.setIconSize(QSize(18, 18))
                mplw.ntb.setFixedSize(300, 24)
                layout.addWidget(mplw, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1
            # Show toolbar
            if self.checkBox_1.isChecked():
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
            axes.set_title(self.from_params('title', s.params, default_title))
            axes.set_xlabel(self.from_params('xlabel', s.params, 'Time, ms'))
            axes.set_ylabel(self.from_params('ylabel', s.params, '%s, %s' % (s.name, s.unit)))
            # plot previous line
            if self.checkBox_2.isChecked() and self.last_selection >= 0:
                for s1 in self.old_signal_list:
                    if s1.name == s.name:
                        axes.plot(s1.x, s1.y, color=self.previous_color)
                        break
            # plot main line
            try:
                y_min = float(self.from_params(b'plot_y_min', s.params, 'inf'))
                y_max = float(self.from_params(b'plot_y_max', s.params, '-inf'))
                if y_max > y_min:
                    axes.item.setYRange(y_min, y_max)
            except:
                pass
            axes.plot(s.x, s.y, color=self.trace_color)
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
                    # mplw.autoRange()
            except:
                pass
            # mplw.canvas.draw()
            jj += 1
        # Remove unused plot widgets
        while jj < layout.count():
            item = layout.takeAt(layout.count() - 1)
            if not item:
                continue
            w = item.widget()
            if w:
                w.deleteLater()
        # self.logger.debug('End %s', time.time() - t0)

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
            self.tableWidget_3.item(row, column).setBackground(color)
        except:
            pass

    def update_status_bar(self):
        if self.log_file_name is not None:
            self.sb_text.setText('File: %s' % self.log_file_name)
            if self.checkBox_2.isChecked() and self.last_selection >= 0:
                self.change_background()
                # self.tableWidget_3.item(self.last_selection, 0).setBackground(YELLOW)
                last_sel_time = self.log_table.column("Time")[self.last_selection]
                self.sb_prev_shot_time.setVisible(True)
                self.sb_prev_shot_time.setText(last_sel_time)
                # self.sblbl2.setText('File: %s;    Previous: %s' % (self.log_file_name, last_sel_time))
            else:
                self.sb_prev_shot_time.setVisible(False)
                self.sb_prev_shot_time.setText("**:**:**")
            green_time = self.log_table.column("Time")[self.current_selection]
            self.sb_green_time.setVisible(True)
            self.sb_green_time.setText(green_time)
        else:
            self.sb_text.setText('Data file not found')
            self.sb_prev_shot_time.setVisible(False)
            self.sb_green_time.setVisible(False)
            self.sb_prev_shot_time.setText('**:**:**')
            self.sb_green_time.setText('**:**:**')

    def file_selection_changed(self, m):
        # self.logger.debug('Selection changed to %s' % str(m))
        if m < 0:
            return
        new_log_file = str(self.comboBox_2.currentText())
        if not os.path.exists(new_log_file):
            self.logger.warning('File %s not found' % new_log_file)
            self.comboBox_2.removeItem(m)
            return
        if self.log_file_name != new_log_file:
            self.log_file_name = new_log_file
            # clear signal list
            self.signal_list = []
            self.old_signal_list = []
            self.last_selection = -1
            self.current_selection = -1
            self.restore_local_settings()
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
            log_exception('Local configuration restore error from %s' % full_name)
            return False

    def save_local_settings(self):
        full_name = os.path.join(self.get_data_folder(), CONFIG_FILE)
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

    def sort_columns(self):
        included = self.plainTextEdit_2.toPlainText().split('\n')
        hidden = []
        columns = []
        # add from included
        for t in included:
            if t in self.log_table.headers and t not in columns:
                columns.append(t)
        # create hidden columns list
        for t in self.log_table.headers:
            if t not in columns:
                hidden.append(t)
        # sort hidden list
        hidden.sort()
        # set hidden columns text
        text = '\n'.join(hidden)
        # for t in hidden:
        #     text += t
        #     text += '\n'
        self.plainTextEdit_3.setPlainText(text)
        return columns

    def parse_folder(self, file_name: str = None, append=False):
        try:
            if file_name is None:
                file_name = self.log_file_name
            if file_name is None:
                self.sb_text.setText('Data file not found')
                self.logger.info('Data file not found')
                return
            self.sb_text.setText('Reading %s' % file_name)
            self.logger.info('Reading data file %s', file_name)
            # get extra columns
            self.extra_cols = self.plainTextEdit_5.toPlainText().split('\n')
            if self.log_table.file_name == file_name:
                self.logger.debug("Appending from log file")
                # append
                buf = self.log_table.read_log_to_buf()
                n = self.log_table.append(buf, extra_cols=self.extra_cols)
                # Create displayed columns list
                self.columns = self.sort_columns()
                self.fill_table_widget(-1)
                # select last row of widget -> tableSelectionChanged will be fired
                self.select_last_row()
            else:
                self.logger.debug("Clean log table and refill from new log file")
                self.log_table.__init__(self.log_file_name, extra_cols=self.extra_cols,
                                        show_line_flag=self.checkBox_6.isChecked())
                if self.log_table.file_name is None:
                    return
                self.log_file_name = self.log_table.file_name
                # Create displayed columns list
                self.columns = self.sort_columns()
                self.fill_table_widget(-1)
                # select last row of widget -> tableSelectionChanged will be fired
                self.select_last_row()
        except:
            log_exception(self, 'Exception in parseFolder')
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

    # def insert_columns(self):
    #     cln = 0
    #     for column in self.columns:
    #         #n = self.tableWidget_3.columnCount()
    #         #i = self.tableWidget_3.horizontalHeaderItem(n)
    #         #i = self.tableWidget_3.setHorizontalHeaderLabels(labels)
    #         self.tableWidget_3.insertColumn(cln)
    #         self.tableWidget_3.setHorizontalHeaderItem(cln, QTableWidgetItem(column))
    #         cln += 1
    #         self.tableWidget_3.horizontalHeaderItem(0).text()

    def fill_table_widget(self, append=-1):
        # disable table widget update events
        self.tableWidget_3.setUpdatesEnabled(False)
        try:
            self.tableWidget_3.itemSelectionChanged.disconnect(self.table_selection_changed)
        except:
            log_exception()
        if append == 0:
            return
        elif append < 0:
            # clear table widget
            self.tableWidget_3.setRowCount(0)
            self.tableWidget_3.setColumnCount(0)
            # insert columns
            cln = 0
            for column in self.columns:
                self.tableWidget_3.insertColumn(cln)
                self.tableWidget_3.setHorizontalHeaderItem(cln, QTableWidgetItem(column))
                cln += 1
            row_range = range(self.log_table.rows)
        else:
            # insert columns
            for column in self.columns[self.tableWidget_3.columnCount():]:
                self.insert_column(column)
            row_range = range(self.log_table.rows - append, self.log_table.rows)
        # insert and fill rows
        for row in row_range:
            self.tableWidget_3.insertRow(row)
            n = 0
            for column in self.columns:
                col = self.log_table.find_column(column)
                if col < 0:
                    continue
                try:
                    fmt = self.config['format'][column]
                    txt = fmt % (self.log_table.values[col][row], self.log_table.units[col][row])
                except:
                    txt = self.log_table.data[col][row]
                txt = txt.replace('none', '')
                txt = txt.replace('None', '')
                item = QTableWidgetItem(txt)
                item.setFont(CELL_FONT)
                # mark changed values
                if row > 0:
                    v = self.log_table.values[col][row]
                    v1 = self.log_table.values[col][row - 1]
                    flag = True
                    if math.isnan(v) or math.isnan(v1):
                        flag = False
                    else:
                        try:
                            thr = config['thresholds'][column]
                        except:
                            thr = 0.03
                        if thr > 0.0:
                            flag = (v != 0.0) and (abs((v1 - v) / v) > thr)
                        elif thr < 0.0:
                            flag = abs(v1 - v) > -thr
                    if flag:
                        item.setFont(CELL_FONT_BOLD)
                self.tableWidget_3.setItem(row, n, item)
                n += 1
        # resize Columns
        self.tableWidget_3.resizeColumnsToContents()
        # enable table widget update events
        self.tableWidget_3.setUpdatesEnabled(True)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
        #
        self.tableWidget_3.scrollToBottom()
        self.tableWidget_3.setFocus()

    def save_settings(self, folder='', file_name=None, config=None):
        global CONFIG_FILE
        if file_name is None:
            file_name = CONFIG_FILE
        if config is None:
            config = self.conf
        full_name = os.path.join(str(folder), file_name)
        try:
            # save window size and position
            p = self.pos()
            s = self.size()
            config['main_window'] = {'size': (s.width(), s.height()), 'position': (p.x(), p.y())}
            config['folder'] = self.log_file_name
            config['history'] = [str(self.comboBox_2.itemText(count)) for count in
                                 range(min(self.comboBox_2.count(), 10))]
            config['history_index'] = min(self.comboBox_2.currentIndex(), 9)
            config['log_level'] = self.logger.level
            config['included'] = str(self.plainTextEdit_2.toPlainText())
            config['excluded'] = str(self.plainTextEdit_3.toPlainText())
            config['cb_1'] = self.checkBox_1.isChecked()
            config['cb_2'] = self.checkBox_2.isChecked()
            config['cb_3'] = self.checkBox_3.isChecked()
            config['cb_4'] = self.checkBox_4.isChecked()
            config['cb_6'] = self.checkBox_6.isChecked()
            config['extra_plot'] = str(self.plainTextEdit_4.toPlainText())
            config['extra_col'] = str(self.plainTextEdit_5.toPlainText())
            config['exclude_plots'] = str(self.plainTextEdit_6.toPlainText())
            config['plot_order'] = str(self.plainTextEdit_7.toPlainText())
            with open(full_name, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.info('Configuration saved to %s' % full_name)
            return True
        except:
            log_exception('Error configuration save to %s' % full_name)
            return False

    def restore_settings(self, folder='', file_name=None):
        global CONFIG_FILE
        if file_name is None:
            file_name = CONFIG_FILE
        full_name = os.path.join(str(folder), file_name)
        try:
            with open(full_name, 'r') as configfile:
                s = configfile.read()
            self.conf = json.loads(s)
            global config
            config = self.conf
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
                self.resize(QSize(self.conf['main_window']['size'][0], self.conf['main_window']['size'][1]))
                self.move(QPoint(self.conf['main_window']['position'][0], self.conf['main_window']['position'][1]))
            # colors
            try:
                self.trace_color = config['colors']['trace']
            except:
                pass
            try:
                self.previous_color = config['colors']['previous']
            except:
                pass
            try:
                self.mark_color = config['colors']['mark']
            except:
                pass
            try:
                self.zero_color = config['colors']['zero']
            except:
                pass
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
            if 'cb_6' in self.conf:
                self.checkBox_6.setChecked(self.conf['cb_6'])
            if 'history' in self.conf:
                self.comboBox_2.currentIndexChanged.disconnect(self.file_selection_changed)
                self.comboBox_2.clear()
                self.comboBox_2.addItems(self.conf['history'])
                self.comboBox_2.currentIndexChanged.connect(self.file_selection_changed)
            if 'history_index' in self.conf:
                self.comboBox_2.setCurrentIndex(self.conf['history_index'])
            self.logger.log(logging.INFO, 'Configuration restored from %s' % full_name)
            return True
        except:
            log_exception('Configuration restore error from %s' % full_name)
            return False

    def config_selection_changed(self, index):
        global CONFIG_FILE
        CONFIG_FILE = str(self.sb_combo.currentText())
        self.restore_settings()
        self.restore_local_settings()
        self.table_selection_changed(True)
        self.refresh_flag = False
        self.parse_folder()

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
        file = os.path.join(folder, "lock.lock")
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

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.save_local_settings()
        self.save_settings()
        a0.accept()

    def save_and_exit(self) -> None:
        self.save_local_settings()
        self.save_settings()
        QApplication.exit()
        # QApplication.quit()

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.sb_clock.setText(t)
        if (time.time() - self.sb_log.time) > 10.0:
            self.sb_log.setText('')
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
        # self.select_last_row()
        # self.restore_background()
        # self.last_selection = self.log_table.rows - 1
        self.parse_folder()

    def select_last_row(self):
        # select last row
        if self.checkBox_4.isChecked():
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount() - 1)
            self.last_selection = self.tableWidget_3.rowCount() - 1
            self.logger.debug('Selection has been switched to last row')
        else:
            self.logger.debug('Selection switch to last row rejected')


class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(self.VLine | self.Sunken)


class LogTable:
    def __init__(self, file_name: str, folder: str = "", extra_cols=None, logger=None, show_line_flag=False):
        if extra_cols is None:
            extra_cols = []
        if logger is None:
            self.logger = config_logger()
        else:
            self.logger = logger
        self.headers = []
        self.data = [[], ]
        self.values = [[], ]
        self.units = [[], ]
        self.file_name = None
        self.old_file_name = None
        self.folder = folder
        self.file_size = -1
        self.old_file_size = -1
        self.rows = 0
        self.columns = 0
        self.columns_with_error = []
        self.keys_with_errors = []
        self.show_line_flag = show_line_flag

        buf = self.read_log_to_buf(file_name, folder)
        self.append(buf, extra_cols)

    def read_log_to_buf(self, file_name: str = None, folder: str = None):
        if folder is None:
            folder = self.folder
        if file_name is None:
            file_name = self.file_name
        fn = os.path.abspath(os.path.join(folder, file_name))
        if not os.path.exists(fn):
            self.logger.warning('File %s does not exist' % fn)
            return None
        # if self.old_file_name == fn:
        #     pass
        fs = os.path.getsize(fn)
        self.logger.info(f'File {fn} {fs} bytes will be processed')
        if fs < 20 or (self.file_name == fn and fs <= self.file_size):
            self.logger.warning('Wrong file size for %s' % fn)
            return None
        # read file to buf
        try:
            # with open(fn, "r", encoding='windows-1251') as stream:
            with open(fn, "rb") as stream:
                if self.file_name == fn:
                    self.logger.debug(f'Positioning to {self.file_size}')
                    stream.seek(self.file_size)
                    # buf = stream.read(fs - self.old_file_size)
                # else:
                buf = stream.read()
            self.logger.debug(f'{len(buf)} bytes has been red')
            buf1 = buf.decode('cp1251')
            self.old_file_name = self.file_name
            self.file_name = fn
            self.folder = folder
            self.old_file_size = self.file_size
            self.file_size = fs
            return buf1
        except:
            log_exception(self.logger, 'Data file %s can not be opened' % fn)
            return None

    def append(self, buf, extra_cols=None):
        if not buf:
            self.logger.debug('Empty buffer')
            return 0
        if extra_cols is None:
            extra_cols = []
        lines = buf.split('\n')
        # loop for lines
        n = 0
        self.keys_with_errors = []
        for line in lines:
            if line != '' and self.decode_line(line):
                n += 1
        # add extra columns
        self.add_extra_columns(extra_cols)
        self.logger.debug('%d of %d lines has been appended' % (n, len(lines)))
        return n

    def decode_line(self, line):
        if self.show_line_flag and ('DO_NOT_SHOW_LINE' in line or
                                    'DO_NOT_SHOW = True' in line or
                                    'DO_NOT_SHOW=True' in line):
            self.logger.info(f'DO_NOT_SHOW tag detected in {line[11:20]}, line skipped')
            return False
        # Split line to fields
        fields = line.split("; ")
        # First field "date time" should be longer than 18 symbols
        if len(fields) < 2 or len(fields[0]) < 19:
            # Wrong line format, skip to next line
            self.logger.info('Wrong data format in "%s", line skipped' % line[11:20])
            return False
        # split time and date
        tm = fields[0].split(" ")[1].strip()
        # preserve only time
        fields[0] = "Time=" + tm
        # add row to table
        self.add_row()
        # iterate rest fields for key=value pairs
        added_columns = []
        for field in fields:
            kv = field.split("=")
            key = kv[0].strip()
            val = kv[1].strip()
            if key in added_columns:
                self.logger.warning('Duplicate columns in row %s)', self.rows)
            else:
                added_columns.append(key)
            j = self.add_column(key)
            self.data[j][self.rows - 1] = val
            # split value and units
            vu = val.split(" ")
            try:
                v = float(vu[0].strip().replace(',', '.'))
                if key in self.keys_with_errors:
                    self.keys_with_errors.remove(key)
            except:
                v = float('nan')
                if key != 'Time' and key != 'File' and key not in self.keys_with_errors:
                    self.logger.debug('Non float value in "%s"' % field)
                    self.keys_with_errors.append(key)
            self.values[j][self.rows - 1] = v
            # units
            try:
                u = vu[1].strip()
            except:
                u = ''
            self.units[j][self.rows - 1] = u
        return True

    def add_row(self):
        for item in self.data:
            item.append("")
        for item in self.values:
            item.append(float('nan'))
        for item in self.units:
            item.append("")
        self.rows += 1

    def add_column(self, col_name):
        if col_name is None or col_name == '':
            return -1
        # skip if column exists
        if col_name in self.headers:
            return self.headers.index(col_name)
        self.headers.append(col_name)
        new_col = [""] * self.rows
        self.data.append(new_col)
        new_col = [float('nan')] * self.rows
        self.values.append(new_col)
        new_col = [""] * self.rows
        self.units.append(new_col)
        self.columns += 1
        return self.headers.index(col_name)

    def add_extra_columns(self, extra_cols):
        self.columns_with_error = []
        for row in range(self.rows):
            for column in extra_cols:
                if column.strip() != "":
                    try:
                        key, value, units = eval(column)
                        if (key is not None) and (key != ''):
                            j = self.add_column(key)
                            self.data[j][row] = str(value) + ' ' + str(units)
                            self.values[j][row] = float(value)
                            self.units[j][row] = str(units)
                        if column in self.columns_with_error:
                            self.columns_with_error.remove(column)
                    except:
                        if column not in self.columns_with_error:
                            log_exception(self.logger, 'eval() error in "%s ..."', column[:10], level=logging.INFO)
                            self.columns_with_error.append(column)
        for column in self.columns_with_error:
            self.logger.warning('Can not create extra column for "%s ..."', column[:10])

    def remove_row(self, row):
        for item in self.data:
            del item[row]
        for item in self.values:
            del item[row]
        for item in self.units:
            del item[row]
        self.rows -= 1

    def column_number(self, col):
        try:
            if isinstance(col, str):
                return self.headers.index(col)
            icol = int(col)
            if 0 <= icol < self.columns:
                return icol
            else:
                return -1
        except:
            return -1

    def remove_column(self, col):
        coln = self.column_number(col)
        if coln < 0:
            return
        del self.data[coln]
        del self.values[coln]
        del self.units[coln]
        del self.headers[coln]
        self.columns -= 1

    def row_col(self, *args):
        if isinstance(args[0], str):
            col = args[0]
            row = -1
        else:
            col = args[1]
            row = int(args[0])
        coln = self.column_number(col)
        if coln < 0 or row < -1 or coln > self.columns - 1 or row > self.rows - 1:
            raise ValueError('Log Table index out of bounds (%s, %s)' % (row, col))
        return row, coln

    def data_item(self, *args):
        try:
            row, col = self.row_col(*args)
            return self.data[col][row]
        except:
            return ''

    def value_item(self, *args):
        try:
            row, col = self.row_col(*args)
            return self.values[col][row]
        except:
            return float('nan')

    def value(self, *args):
        return self.value_item(*args)

    def unit_item(self, *args):
        try:
            row, col = self.row_col(*args)
            return self.units[col][row]
        except:
            return ''

    def get_item(self, *args):
        try:
            row, col = self.row_col(*args)
            return self.data[col][row], self.values[col][row], self.units[col][row]
        except:
            return '', float('nan'), ''

    def set_item(self, *args):
        try:
            row, col = self.row_col(*args)
            vu = str(args[2]).split(" ")
            v = float(vu[0].strip().replace(',', '.'))
            if len(vu) > 1:
                u = vu[1].strip()
            else:
                u = ''
            self.data[col][row] = str(args[2])
            self.values[col][row] = v
            self.units[col][row] = u
            return True
        except:
            return False

    def column(self, col):
        coln = self.column_number(col)
        if coln < 0 or coln > self.columns - 1:
            return None
        return self.data[coln]

    def row(self, r):
        return [self.data[n][r] for n in range(self.columns)]

    def find_column(self, col_name):
        try:
            return self.headers.index(col_name)
        except:
            return -1

    def __contains__(self, item):
        return item in self.headers

    def __len__(self):
        return len(self.headers)


class Signal:
    def __init__(self, x=numpy.zeros(1), y=numpy.zeros(1), params=None, name='empty',
                 unit='', scale=1.0, value=float('nan'), marks=None):
        if params is None:
            params = {}
        if marks is None:
            marks = {}
        n = min(len(x), len(y))
        self.x = x[:n]
        self.y = y[:n]
        self.params = params
        self.name = name
        self.unit = unit
        self.scale = scale
        self.value = value
        self.marks = marks

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

    def trim(self):
        n = min(len(self.x), len(self.y))
        self.x = self.x[:n]
        self.y = self.y[:n]

    def __add__(self, other):
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result = Signal(args[0].x, args[0].y + args[1].y)
            result.value = self.value + other.value
            result.name = self.name + '+' + other.name
        else:
            result = Signal(self.x, self.y + other)
            if isinstance(other, int) or isinstance(other, float):
                result.value = self.value + other
        return result

    def __sub__(self, other):
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result = Signal(args[0].x, args[0].y - args[1].y)
            result.value = self.value - other.value
            result.name = self.name + '-' + other.name
        else:
            result = Signal(self.x, self.y - other)
            if isinstance(other, int) or isinstance(other, float):
                result.value = self.value - other
        return result

    def __mul__(self, other):
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result = Signal(args[0].x, args[0].y * args[1].y)
            result.value = self.value * other.value
            result.name = self.name + '*' + other.name
        else:
            result = Signal(self.x, self.y * other)
        if isinstance(other, int) or isinstance(other, float):
            result.value = self.value * other
        return result

    def __truediv__(self, other):
        if isinstance(other, Signal):
            args = justify_signals(self, other)
            result = Signal(args[0].x, args[0].y / args[1].y)
            result.value = self.value / other.value
            result.name = self.name + '/' + other.name
        else:
            result = Signal(self.x, self.y / other)
        if isinstance(other, int) or isinstance(other, float):
            result.value = self.value / other
        return result


class DataFile:
    def __init__(self, file_name, folder="", logger=None):
        if logger is None:
            self.logger = config_logger()
        else:
            self.logger = logger
        self.file_name = None
        self.files = []
        self.signals = []
        full_name = os.path.join(folder, file_name)
        with zipfile.ZipFile(full_name, 'r') as zip_file:
            self.files = zip_file.namelist()
        self.file_name = full_name
        for f in self.files:
            if f.find("chan") >= 0 > f.find("paramchan"):
                self.signals.append(f)

    def read_signal(self, signal_name: str) -> Signal:
        signal = Signal()
        if signal_name not in self.signals:
            self.logger.info("No signal %s in the file %s" % (signal_name, self.file_name))
            return signal
        with zipfile.ZipFile(self.file_name, 'r') as zipobj:
            buf = zipobj.read(signal_name)
            param_name = signal_name.replace('chan', 'paramchan')
            pbuf = zipobj.read(param_name)
        if b'\r\n' in buf:
            endline = b"\r\n"
        elif b'\n' in buf:
            endline = b"\n"
        elif b'\r' in buf:
            endline = b"\r"
        else:
            self.logger.warning("Incorrect data format for %s" % signal_name)
            return signal
        lines = buf.split(endline)
        n = len(lines)
        if n < 2:
            self.logger.warning("No data for %s" % signal_name)
            return signal
        signal.x = numpy.zeros(n, dtype=numpy.float64)
        signal.y = numpy.zeros(n, dtype=numpy.float64)
        error_lines = False
        for i, line in enumerate(lines):
            xy = line.replace(b',', b'.').split(b'; ')
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
        if error_lines:
            self.logger.debug("Some lines with wrong data in %s", signal_name)
        # read parameters
        signal.params = {}
        lines = pbuf.split(endline)
        error_lines = False
        for line in lines:
            if line != b'':
                kv = line.split(b'=')
                if len(kv) >= 2:
                    signal.params[kv[0].strip()] = kv[1].strip()
                else:
                    error_lines = True
        if error_lines:
            self.logger.debug("Wrong parameter for %s" % signal_name)
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
        if b'unit' in signal.params:
            signal.unit = signal.params[b'unit'].decode('ascii')
        else:
            signal.unit = ''
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
                except:
                    log_exception(self, 'Mark %s value can not be computed for %s' % (mark_name, signal_name))
        # calculate value
        if 'zero' in signal.marks:
            zero = signal.marks["zero"][2]
        else:
            zero = 0.0
        if 'mark' in signal.marks:
            signal.value = signal.marks["mark"][2] - zero
        else:
            signal.value = float('nan')
        return signal

    def read_all_signals(self):
        signals = []
        for s in self.signals:
            signals.append(self.read_signal(s))
        return signals


def justify_signals(first: Signal, other: Signal):
    if len(first.x) == len(other.x) and \
            first.x[0] == other.x[0] and first.x[-1] == other.x[-1]:
        return first, other
    xmin = max(first.x[0], other.x[0])
    xmax = min(first.x[-1], other.x[-1])
    index1 = np.logical_and(first.x >= xmin, first.x <= xmax).nonzero()[0]
    index2 = np.logical_and(other.x >= xmin, other.x <= xmax).nonzero()[0]
    result = (Signal(name=first.name, marks=first.marks, value=first.value),
              Signal(name=other.name, marks=other.marks, value=other.value))
    if len(index1) >= len(index2):
        x = first.x[index1].copy()
        result[1].y = numpy.interp(x, other.x[index2], other.y[index2])
        result[0].x = x
        result[0].y = first.y[index1].copy()
        result[1].x = x
    else:
        x = first.x[index2].copy()
        result[0].y = numpy.interp(x, first.x[index1], first.y[index1])
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
    # start the Qt main loop execution,
    exec_result = app.exec_()
    # exiting from this script with the same return code of Qt application
    sys.exit(exec_result)
