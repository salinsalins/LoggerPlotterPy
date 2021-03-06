# coding: utf-8
"""
Created on Jul 2, 2017

@author: sanin
"""

import os.path
import sys
import json
import logging
import zipfile
import time
import gc

from PyQt5.QtWidgets import QMainWindow, QHeaderView, QFrame, QAction, QMenu
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QLabel
from PyQt5 import uic, QtCore
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QFont
import PyQt5.QtGui as QtGui

import numpy

np = numpy
#from mplwidget import MplWidget
from pyqtgraphdget import MplWidget

import imports


def config_logger(name=__name__, level=logging.DEBUG):
    lgr = logging.getLogger(name)
    if not lgr.hasHandlers():
        lgr.propagate = False
        lgr.setLevel(level)
        f_str = '%(asctime)s,%(msecs)03d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s'
        log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        lgr.addHandler(console_handler)
    return lgr


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if te - ts > 0.01:
            print('%r %2.2f sec' % (method.__name__, te-ts))
        return result
    return timed


ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'LoggerPlotterPy'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '_4_5'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

CELL_BOLD_FONT = QFont('Open Sans Bold', weight=QFont.Bold)
CELL_NORMAL_FONT = QFont('Open Sans', weight=QFont.Normal)

# Configure logging
logger = config_logger(level=logging.INFO)

# Global configuration dictionary
config = {}


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        # Initialization of the superclass
        super().__init__(parent)
        # class members definition
        # colors
        self.previous_color = '#ffff00'
        self.trace_color = '#00ff00'
        self.mark_color = '#ff0000'
        self.zero_color = '#0000ff'

        self.log_file_name = None
        self.root = None
        self.conf = {}
        self.refresh_flag = False
        self.last_selection = -1
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
        self.new_shot = True

        # initial actions
        # Load the UI
        uic.loadUi(UI_FILE, self)
        # Configure logging
        self.logger = logger
        # Connect signals with the slots
        self.pushButton_2.clicked.connect(self.select_log_file)
        self.comboBox_2.currentIndexChanged.connect(self.file_selection_changed)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
        self.comboBox_1.currentIndexChanged.connect(self.log_level_index_changed)
        self.plainTextEdit_2.textChanged.connect(self.refresh_on)
        self.plainTextEdit_3.textChanged.connect(self.refresh_on)
        self.plainTextEdit_4.textChanged.connect(self.refresh_on)
        self.plainTextEdit_5.textChanged.connect(self.refresh_on)
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionOpen.triggered.connect(self.select_log_file)
        self.actionPlot.triggered.connect(self.show_plot_pane)
        self.actionParameters.triggered.connect(self.show_param_pane)
        self.actionAbout.triggered.connect(self.show_about)
        # Additional configuration
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        header = self.tableWidget_3.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.Stretch)  # QHeaderView.Stretch QHeaderView.ResizeToContents
        header.setSectionResizeMode(QHeaderView.ResizeToContents)  # QHeaderView.Stretch QHeaderView.ResizeToContents
        header.setSectionResizeMode(0)
        header.sectionDoubleClicked.connect(self.test)
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
        # brushes, colors, fonts
        self.yellow_brush = QBrush(QColor('#FFFF00'))
        self.clock_font = QFont('Open Sans Bold', 16, weight=QFont.Bold)
        self.statusbar_font = QFont('Open Sans', 14)
        # clock label at status bar
        self.clock = QLabel(" ")
        self.clock.setFont(self.clock_font)
        self.statusbar_font = QFont('Open Sans', 14)
        self.statusBar().setFont(self.statusbar_font)
        # another widgets for status bar
        self.sblbl1 = QLabel("")
        self.sblbl1.setFont(self.statusbar_font)
        self.sblbl1.setStyleSheet('border: 0; color:  black; background: yellow;')
        self.sblbl1.setText("        ")
        self.sblbl2 = QLabel("")
        self.sblbl2.setFont(self.statusbar_font)
        # add widgets to status bar
        self.statusBar().reformat()
        self.statusBar().setStyleSheet('border: 0; background-color: #FFF8DC;')
        self.statusBar().setStyleSheet("QStatusBar::item {border: none;}")
        self.statusBar().addWidget(self.sblbl1)
        self.statusBar().addWidget(VLine())  # <---
        self.statusBar().addWidget(self.sblbl2)
        self.statusBar().addWidget(VLine())  # <---
        self.statusBar().addPermanentWidget(VLine())  # <---
        self.statusBar().addPermanentWidget(self.clock)
        self.sblbl2.setText("Starting...")
        #self.statusBar().showMessage('Starting...')

        # default settings
        self.set_default_settings()
        print(APPLICATION_NAME + APPLICATION_VERSION + ' started')
        # restore settings
        self.restore_settings()

        # additional decorations
        self.tableWidget_3.horizontalHeader().setVisible(True)
        #self.tableWidget_3.customContextMenuRequested.connect(self.openMenu)
        #self.tableWidget_3.setContextMenuPolicy(Qt.ActionsContextMenu)
        #quitAction = QAction("Quit", None)
        #quitAction.triggered.connect(self.test)
        #self.tableWidget_3.addAction(quitAction)

        # read data files
        self.parse_folder()

    def openMenu(self, n):
        menu = QMenu()
        quitAction = menu.addAction("Hide")
        cursor = QtGui.QCursor()
        position = cursor.pos()
        #position = self.tableWidget_3.mapFromGlobal(position)
        #action = menu.exec_(self.tableWidget_3.mapToGlobal(position))
        action = menu.exec_(position)
        if action == quitAction:
            #print("Hide")
            excluded = self.plainTextEdit_3.toPlainText()
            t = self.tableWidget_3.horizontalHeaderItem(n).text()
            excluded += '\n' + t
            self.plainTextEdit_3.setPlainText(excluded)
            self.tableWidget_3.hideColumn(n)
            #qApp.quit()

    def test(self, a):
        #h = self.tableWidget_3.horizontalHeader()
        #print('test', a)
        self.openMenu(a)

    def refresh_on(self):
        self.refresh_flag = True

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + ' Version ' + APPLICATION_VERSION +
                                '\nShow saved shot logs and plot traces.', QMessageBox.Ok)

    def show_plot_pane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionParameters.setChecked(False)
        self.save_settings()
        self.table_selection_changed()
        if self.refresh_flag:
            self.refresh_flag = False
            self.parse_folder()

    def show_param_pane(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionParameters.setChecked(True)

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
        # change selection and fire callback
        self.comboBox_2.setCurrentIndex(i)

    @timeit
    def table_selection_changed(self):
        def sig(name):
            for sg in self.signal_list:
                if sg.name == name:
                    return sg
            return None

        self.logger.debug('Entry')
        t0 = time.time()
        gc.collect()
        try:
            # if selection is empty
            if len(self.tableWidget_3.selectedRanges()) < 1:
                return
            row_s = self.tableWidget_3.selectedRanges()[0].topRow()
            # if selected the same row
            if self.last_selection == row_s:
                return
            # different row selected
            self.logger.log(logging.DEBUG, 'Selection changed to row %i' % row_s)
            if row_s < 0:
                return
            folder = os.path.dirname(self.log_file_name)
            zip_file_name = self.log_table.column("File")[row_s]
            self.logger.log(logging.DEBUG, 'Using zip File %s' % zip_file_name)
            # read zip file listing
            self.data_file = DataFile(zip_file_name, folder=folder)
            # read signals from zip file
            self.old_signal_list = self.signal_list
            self.signal_list = self.data_file.read_all_signals()
            # reorder plots according to columns order in the table
            self.signals = []
            for c in self.columns:
                for s in self.signal_list:
                    if s.name == c:
                        self.signals.append(self.signal_list.index(s))
                        break
            # add extra plots from plainTextEdit_4
            extra_plots = self.plainTextEdit_4.toPlainText().split('\n')
            for p in extra_plots:
                if p.strip() != "":
                    try:
                        s = Signal(name='undefined')
                        result = eval(p)
                        if isinstance(result, Signal):
                            s = result
                        elif len(result) == 3:
                            key, x_val, y_val = result
                            if key != '':
                                s = Signal(name='undefined')
                                s.x = x_val
                                s.y = y_val
                                s.name = key
                        elif len(result) == 2:
                            if isinstance(result[1], Signal):
                                s = result[1]
                                s.name = result[0]
                        self.signal_list.append(s)
                        self.signals.append(self.signal_list.index(s))
                    except:
                        self.logger.info('Plot eval() error in %s' % p)
                        self.logger.debug('Exception:', exc_info=True)
            # reorder signals to plot order and exclude not necessary
            plot_order = self.plainTextEdit_7.toPlainText().split('\n')
            excluded_plots = self.plainTextEdit_6.toPlainText().split('\n')
            ordered_signals = []
            for p in plot_order:
                for s in self.signal_list:
                    if s.name == p:
                        ordered_signals.append(self.signal_list.index(s))
                        break
            for p in self.signals:
                if p not in ordered_signals:
                    if self.signal_list[p].name not in excluded_plots:
                        ordered_signals.append(p)
            self.signals = ordered_signals
            # plot signals
            self.logger.debug('Plot signals begin %s', time.time()-t0)
            self.scrollAreaWidgetContents_3.setUpdatesEnabled(False)
            layout = self.scrollAreaWidgetContents_3.layout()
            jj = 0
            col = 0
            row = 0
            col_count = 3
            for c in self.signals:
                s = self.signal_list[c]
                # Use existing plot widgets or add new
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
                # plot previous line
                if self.checkBox_2.isChecked():
                    for s1 in self.old_signal_list:
                        if s1.name == s.name:
                            axes.plot(s1.x, s1.y, color=self.previous_color)
                            break
                # plot main line
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
                # Decorate the plot
                axes.grid(True)
                axes.set_title('{0} = {1:5.2f} {2}'.format(s.name, s.value, s.unit))
                if b"xlabel" in s.params:
                    axes.set_xlabel(s.params[b"xlabel"].decode('ascii'))
                elif "xlabel" in s.params:
                    axes.set_xlabel(s.params["xlabel"].decode('ascii'))
                else:
                    axes.set_xlabel('Time, ms')
                axes.set_ylabel(s.name + ', ' + s.unit)
                # axes.legend(loc='best')
                # Show plot
                mplw.canvas.draw()
                try:
                    if self.new_shot and self.checkBox_3.isChecked():
                        mplw.clearScaleHistory()
                        mplw.autoRange()
                except:
                    pass
                jj += 1
            # Remove unused plot widgets
            while jj < layout.count():
                item = layout.takeAt(layout.count() - 1)
                if not item:
                    continue
                w = item.widget()
                if w:
                    w.deleteLater()
            if self.checkBox_2.isChecked() and self.last_selection >= 0:
                #self.tableWidget_3.item(self.last_selection, 0).setBackground(self.yellow_brush)
                last_sel_time = self.log_table.column("Time")[self.last_selection]
                self.sblbl1.setText(last_sel_time)
                self.sblbl2.setText('File: %s;    Previous: %s' % (self.log_file_name, last_sel_time))
            else:
                self.sblbl1.setText("        ")
                self.sblbl2.setText('File: %s' % self.log_file_name)
            self.last_selection = row_s
            self.scrollAreaWidgetContents_3.setUpdatesEnabled(True)
            self.logger.debug('Plot signals end %s', time.time()-t0)
        except:
            self.scrollAreaWidgetContents_3.setUpdatesEnabled(True)
            self.logger.log(logging.WARNING, 'Exception in tableSelectionChanged')
            self.logger.debug('Exception:', exc_info=True)
        finally:
            self.new_shot = False

    def file_selection_changed(self, m):
        self.logger.debug('Selection changed to %s' % str(m))
        if m < 0:
            return
        new_log_file = str(self.comboBox_2.currentText())
        if not os.path.exists(new_log_file):
            self.logger.warning('File %s not found' % new_log_file)
            self.comboBox_2.removeItem(m)
            return
        if self.log_file_name != new_log_file:
            self.log_file_name = new_log_file
            self.signal_list = []
            self.parse_folder()

    def log_level_index_changed(self, m: int) -> None:
        levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                  logging.WARNING, logging.ERROR, logging.CRITICAL]
        if m >= 0:
            self.logger.setLevel(levels[m])

    def on_quit(self):
        # save global settings
        self.save_settings()
        timer.stop()

    def sort_columns(self):
        # create sorted displayed columns list
        included = self.plainTextEdit_2.toPlainText().split('\n')
        excluded = self.plainTextEdit_3.toPlainText().split('\n')
        columns = []
        for t in included:
            if t in self.log_table.headers:
                columns.append(self.log_table.headers.index(t))
        for t in self.log_table.headers:
            if t not in excluded and t not in columns:
                columns.append(self.log_table.headers.index(t))
        return columns

    @staticmethod
    def sort_list(initial, included=None, excluded=None):
        if included is None:
            included = []
        if excluded is None:
            excluded = []
        result = []
        for t in included:
            if t in initial:
                result.append(t)
        for t in initial:
            if t not in excluded and t not in result:
                result.append(t)
        return result

    @timeit
    def parse_folder(self, file_name=None):
        self.new_shot = True
        self.last_selection = -1
        try:
            if file_name is None:
                file_name = self.log_file_name
            if file_name is None:
                return
            #self.statusBar().showMessage('Reading %s' % file_name)
            self.sblbl2.setText('Reading %s' % file_name)
            self.logger.debug('Reading log file %s', file_name)
            # get extra columns
            self.extra_cols = self.plainTextEdit_5.toPlainText().split('\n')
            # read log file content to logTable
            self.log_table = LogTable(file_name, extra_cols=self.extra_cols)
            if self.log_table.file_name is None:
                return
            self.log_file_name = self.log_table.file_name
            # Create sorted displayed columns list
            self.included = self.plainTextEdit_2.toPlainText().split('\n')
            self.excluded = self.plainTextEdit_3.toPlainText().split('\n')
            self.columns = []
            # add included columns if present
            for t in self.included:
                if t in self.log_table.headers:
                    self.columns.append(t)
            # add other columns if not excluded
            for t in self.log_table.headers:
                if t not in self.excluded and t not in self.columns:
                    self.columns.append(t)
            # disable table widget update events
            self.tableWidget_3.setUpdatesEnabled(False)
            self.tableWidget_3.itemSelectionChanged.disconnect(self.table_selection_changed)
            # clear table widget
            self.tableWidget_3.setRowCount(0)
            self.tableWidget_3.setColumnCount(0)
            # refill table widget
            # insert columns
            cln = 0
            for column in self.columns:
                self.tableWidget_3.insertColumn(cln)
                self.tableWidget_3.setHorizontalHeaderItem(cln, QTableWidgetItem(column))
                cln += 1
            # insert and fill rows
            # numbers = self.columns.copy
            # formats = self.columns.copy
            # for i in range(len(self.columns)):
            #     numbers[i] = self.log_table.find_column(self.columns[i])
            #     fmt = config['format'][self.log_table.headers[i]]
            #     formats[i] = self.log_table.find_column(self.columns[i])
            for row in range(self.log_table.rows):
                self.tableWidget_3.insertRow(row)
                n = 0
                for column in self.columns:
                    col = self.log_table.find_column(column)
                    try:
                        fmt = config['format'][self.log_table.headers[col]]
                        txt = fmt % (self.log_table.values[col][row], self.log_table.units[col][row])
                    except:
                        txt = self.log_table.data[col][row]
                    item = QTableWidgetItem(txt)
                    # mark changed values
                    if row > 0:
                        v = self.log_table.values[col][row]
                        if v is None:
                            v = 0.0
                        v1 = self.log_table.values[col][row - 1]
                        if v1 is None:
                            v1 = 0.0
                        thr = 0.03
                        try:
                            thr = config['thresholds'][self.log_table.headers[col]]
                        except:
                            pass
                        flag = True
                        if thr > 0.0:
                            flag = (v != 0.0) and (abs((v1 - v) / v) > thr)
                        elif thr < 0.0:
                            flag = abs(v1 - v) > -thr
                        if flag:
                            item.setFont(CELL_BOLD_FONT)
                        else:
                            item.setFont(CELL_NORMAL_FONT)
                    self.tableWidget_3.setItem(row, n, item)
                    n += 1
            # enable table widget update events
            self.tableWidget_3.setUpdatesEnabled(True)
            self.tableWidget_3.resizeColumnsToContents()
            self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
            # select last row of widget -> tableSelectionChanged will be fired
            self.last_selection = -1
            self.tableWidget_3.scrollToBottom()
            self.tableWidget_3.setFocus()
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount() - 1)
        except:
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.logger.debug('Exception:', exc_info=True)
        #self.statusBar().showMessage('File: %s' % file_name)
        self.sblbl2.setText('File: %s' % file_name)
        return

    def save_settings(self, folder='', file_name=CONFIG_FILE):
        def attr2conf(attr, name):
            try:
                self.conf[name] = str(attr)
            except:
                pass

        full_name = os.path.join(str(folder), file_name)
        try:
            # save window size and position
            p = self.pos()
            s = self.size()
            self.conf['main_window'] = {'size': (s.width(), s.height()), 'position': (p.x(), p.y())}
            self.conf['folder'] = self.log_file_name
            self.conf['history'] = [str(self.comboBox_2.itemText(count)) for count in
                                    range(min(self.comboBox_2.count(), 10))]
            self.conf['history_index'] = self.comboBox_2.currentIndex()
            self.conf['log_level'] = self.logger.level
            self.conf['included'] = str(self.plainTextEdit_2.toPlainText())
            self.conf['excluded'] = str(self.plainTextEdit_3.toPlainText())
            self.conf['cb_1'] = self.checkBox_1.isChecked()
            self.conf['cb_2'] = self.checkBox_2.isChecked()
            self.conf['cb_3'] = self.checkBox_3.isChecked()
            self.conf['extra_plot'] = str(self.plainTextEdit_4.toPlainText())
            self.conf['extra_col'] = str(self.plainTextEdit_5.toPlainText())
            attr2conf(self.plainTextEdit_6.toPlainText(), 'exclude_plots')
            attr2conf(self.plainTextEdit_7.toPlainText(), 'plot_order')
            if os.path.exists(full_name):
                # try to read old config to confirm correct syntax
                with open(full_name, 'r') as configfile:
                    s = configfile.read()
            with open(full_name, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.info('Configuration saved to %s' % full_name)
            return True
        except:
            self.logger.log(logging.WARNING, 'Configuration save error to %s' % full_name)
            self.logger.debug('Exception:', exc_info=True)
            return False

    def restore_settings(self, folder='', file_name=CONFIG_FILE):
        def conf2attr(attr, name):
            try:
                attr(self.conf[name])
            except:
                pass
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
            self.logger.log(logging.WARNING, 'Configuration restore error from %s' % full_name)
            self.logger.debug('Exception:', exc_info=True)
            return False

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

    def get_root(self):
        a = os.path.dirname(self.log_file_name)
        a = os.path.dirname(a)
        a = os.path.dirname(a)
        a = os.path.dirname(a)
        if os.path.isfile('filename.txt'):
            pass
        return a

    @timeit
    def timer_handler(self):
        # self.logger.debug('Timer handler enter')
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)
        # check if in parameters edit mode
        if self.stackedWidget.currentIndex() != 0:
            return
        # check if lock file exists
        if self.is_locked():
            return
        # check if log file exists
        if not os.path.exists(self.log_file_name):
            return
        self.old_size = self.log_table.file_size
        self.new_size = os.path.getsize(self.log_file_name)
        if self.new_size <= self.old_size:
            return
        self.new_shot = True
        self.parse_folder()


class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(self.VLine|self.Sunken)


class LogTable:
    def __init__(self, file_name: str, folder: str = "", extra_cols=None):
        if extra_cols is None:
            extra_cols = []
        self.logger = config_logger()
        self.data = [[], ]
        self.values = [[], ]
        self.units = [[], ]
        self.headers = []
        self.file_name = None
        self.file_size = -1
        self.file_lines = -1
        self.rows = 0
        self.columns = 0
        # Full file name
        fn = os.path.join(folder, file_name)
        if not os.path.exists(fn):
            self.logger.info('File %s does not exist' % file_name)
            return
        # read file to buf
        with open(fn, "r") as stream:
            buf = stream.read()
        if len(buf) <= 0:
            self.logger.info('Nothing to process in %s' % file_name)
            return
        self.file_name = fn
        self.file_size = os.path.getsize(fn)
        # split buf to lines
        lines = buf.split('\n')
        self.logger.debug('%d lines in %s' % (len(lines), self.file_name))
        self.file_lines = len(lines)
        # loop for lines
        for line in lines:
            self.decode_line(line)
        # add extra columns
        self.add_extra_columns(extra_cols)

    def decode_line(self, line):
        # Split line to fields
        flds = line.split("; ")
        # First field "date time" should be longer than 18 symbols
        if len(flds[0]) < 19:
            # Wrong line format, skip to next line
            self.logger.info('Wrong date/time format in "%s", line skipped' % flds[0])
            return
        # split time and date
        tm = flds[0].split(" ")[1].strip()
        # preserve only time
        flds[0] = "Time=" + tm
        # add row to table
        self.add_row()
        # iterate for key=value pairs
        for fld in flds:
            kv = fld.split("=")
            key = kv[0].strip()
            val = kv[1].strip()
            j = self.add_column(key)
            self.data[j][self.rows - 1] = val
            # split value and units
            vu = val.split(" ")
            try:
                v = float(vu[0].strip().replace(',', '.'))
            except:
                v = float('nan')
                if key != 'Time' and key != 'File':
                    self.logger.debug('Non float value in "%s"' % fld)
            self.values[j][self.rows - 1] = v
            # units
            try:
                u = vu[1].strip()
            except:
                u = ''
            self.units[j][self.rows - 1] = u

    def add_extra_columns(self, extra_cols):
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
                    except:
                        self.logger.log(logging.INFO, 'Column eval() error in \n   %s' % column)
                        self.logger.debug('Exception:', exc_info=True)

    def refresh(self, extra_cols):
        try:
            # if file size increased
            new_size = os.path.getsize(self.file_name)
            if new_size <= self.file_size:
                return
            # read file to buf
            with open(self.file_name, "r") as stream:
                buf = stream.read()
            if len(buf) <= 0:
                return
            self.file_size = new_size
            # split buf to lines
            lines = buf.split('\n')
            if len(lines) <= self.file_lines:
                return
            self.logger.debug('%d additional lines in %s' % (len(lines) - self.file_lines, self.file_name))
            # Loop for added lines
            for line in lines[self.file_lines:]:
                self.decode_line(line)
            self.file_lines = len(lines)
            # Add extra columns
            self.add_extra_columns(extra_cols)
        except:
            self.logger.warning('Error refreshing %s' % self.file_name)

    def add_row(self):
        for item in self.data:
            item.append("")
        for item in self.values:
            item.append(0.0)
        for item in self.units:
            item.append("")
        self.rows += 1

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
            return int(col)
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

    def item(self, *args):
        if len(args) >= 2:
            col = args[1]
            row = args[0]
        else:
            col = args[0]
            row = -1
        coln = self.column_number(col)
        if coln < 0:
            return ''
        return self.data[coln][row]

    def value(self, *args):
        if len(args) >= 2:
            col = args[1]
            row = args[0]
        else:
            col = args[0]
            row = -1
        coln = self.column_number(col)
        try:
            return self.values[coln][row]
        except:
            return float('nan')

    def get_item(self, row, col):
        return self.item(row, col)

    def set_item(self, row: int, col, value: str):
        coln = self.column_number(col)
        if coln < 0:
            return False
        if row < 0 or row > len(self.data[coln]) - 1:
            return False
        self.data[coln][row] = value
        vu = value.split(" ")
        try:
            v = float(vu[0].strip().replace(',', '.'))
        except:
            v = float('nan')
        self.values[coln][row] = v
        try:
            u = vu[1].strip()
        except:
            u = ''
        self.units[coln][row] = u
        return True

    def column(self, col):
        coln = self.column_number(col)
        if coln < 0:
            return None
        return self.data[coln]

    def row(self, r):
        return [self.data[n][r] for n in range(len(self.headers))]

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
                 unit='', scale=1.0, value=0.0, marks=None):
        if params is None:
            params = {}
        if marks is None:
            marks = {}
        self.x = x
        self.y = y
        self.params = params
        self.name = name
        self.unit = unit
        self.scale = scale
        self.value = value
        self.marks = marks

    def __add__(self, other):
        if isinstance(other, Signal):
            args = self.justify(self, other)
            result = Signal(args[0].x, args[0].y + args[1].y)
        else:
            result = Signal(self.x, self.y + other)
        return result

    def __sub__(self, other):
        if isinstance(other, Signal):
            args = self.justify(self, other)
            result = Signal(args[0].x, args[0].y - args[1].y)
        else:
            result = Signal(self.x, self.y - other)
        return result

    def __mul__(self, other):
        if isinstance(other, Signal):
            args = self.justify(self, other)
            result = Signal(args[0].x, args[0].y * args[1].y)
        else:
            result = Signal(self.x, self.y * other)
        return result

    def __truediv__(self, other):
        if isinstance(other, Signal):
            args = self.justify(self, other)
            result = Signal(args[0].x, args[0].y / args[1].y)
        else:
            result = Signal(self.x, self.y / other)
        return result

    @staticmethod
    def justify(first, other):
        if len(first.x) == len(other.x) and \
                first.x[0] == other.x[0] and first.x[-1] == other.x[-1]:
            return first, other
        result = (Signal(), Signal())
        xmin = max(first.x[0], other.x[0])
        xmax = min(first.x[-1], other.x[-1])
        if xmax <= xmin:
            return result
        n = min(len(first.x), len(other.x))
        x = numpy.linspace(xmin, xmax, n)
        result[0].x = x
        result[1].x = x
        result[0].y = numpy.interp(x, first.x, first.y)
        result[1].y = numpy.interp(x, other.x, other.y)
        return result


class DataFile:
    def __init__(self, file_name, folder=""):
        # self.logger = logging.getLogger(__name__)
        self.logger = config_logger()
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
            self.logger.log(logging.INFO, "No signal %s in the file %s" % (signal_name, self.file_name))
            return signal
        with zipfile.ZipFile(self.file_name, 'r') as zipobj:
            buf = zipobj.read(signal_name)
            param_name = signal_name.replace('chan', 'paramchan')
            pbuf = zipobj.read(param_name)
        if b'\r\n' in buf:
            spltch = b"\r\n"
        elif b'\n' in buf:
            spltch = b"\n"
        elif b'\r' in buf:
            spltch = b"\r"
        else:
            self.logger.warning("Incorrect data format for %s" % signal_name)
            return signal
        lines = buf.split(spltch)
        n = len(lines)
        if n < 2:
            self.logger.warning("No data for %s" % signal_name)
            return signal
        signal.x = numpy.zeros(n, dtype=float)
        signal.y = numpy.zeros(n, dtype=float)
        for ii, ln in enumerate(lines):
            xy = ln.split(b'; ')
            try:
                signal.x[ii] = float(xy[0].replace(b',', b'.'))
                signal.y[ii] = float(xy[1].replace(b',', b'.'))
            except:
                signal.x[ii] = float('nan')
                signal.y[ii] = float('nan')
                self.logger.debug( "Wrong data in line %s for %s", ii, signal_name)
        # read parameters
        signal.params = {}
        lines = pbuf.split(spltch)
        for ln in lines:
            if ln != b'':
                kv = ln.split(b'=')
                if len(kv) >= 2:
                    signal.params[kv[0].strip()] = kv[1].strip()
                else:
                    self.logger.debug("Wrong parameter %s for %s" % (ln, signal_name))
        # scale to units
        if b'display_unit' in signal.params:
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
        x0 = signal.x[0]
        dx = signal.x[1] - signal.x[0]
        for k in signal.params:
            if k.endswith(b"_start"):
                try:
                    ms = int((float(signal.params[k].replace(b',', b'.')) - x0) / dx)
                    ml = int(float(signal.params[k.replace(b"_start", b'_length')].replace(b',', b'.')) / dx)
                    ml = min(len(signal.y) - ms, ml)
                    if ml <= 0 or ms < 0:
                        raise Exception('Wrong slice for mark ' + k.replace(b"_start", b''))
                    mv = signal.y[ms:ms + ml].mean()
                    signal.marks[k.replace(b"_start", b'').decode('ascii')] = (ms, ml, mv)
                except:
                    self.logger.log(logging.WARNING, 'Mark %s value can not be computed for %s' % (k, signal_name))
                    self.logger.debug('Exception:', exc_info=True)
        # zero mark
        if 'zero' in signal.marks:
            zero = signal.marks["zero"][2]
        else:
            zero = 0.0
        if 'mark' in signal.marks:
            signal.value = signal.marks["mark"][2] - zero
        else:
            signal.value = 0.0
        return signal

    def read_all_signals(self):
        signals = []
        for s in self.signals:
            signals.append(self.read_signal(s))
        return signals


# Logging to the text panel
class TextEditHandler(logging.Handler):
    widget = None

    def __init__(self, wdgt=None):
        logging.Handler.__init__(self)
        self.widget = wdgt

    def emit(self, record):
        log_entry = self.format(record)
        if self.widget is not None:
            self.widget.appendPlainText(log_entry)


class Config:
    def __init__(self):
        self.data = {}

    def __getitem__(self, item):
        return self.data[item]


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        CONFIG_FILE = sys.argv[1]
    # create the GUI application
    app = QApplication(sys.argv)
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    #app.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    #app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    #app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    #app.setAttribute(QtCore.Qt.AA_Use96Dpi)
    # instantiate the main window
    dmw = MainWindow()
    app.aboutToQuit.connect(dmw.on_quit)
    # show it
    dmw.show()
    # defile and start timer task
    timer = QTimer()
    timer.timeout.connect(dmw.timer_handler)
    timer.start(1000)
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())
