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
import copy

from PyQt5.QtWidgets import QMainWindow, QHeaderView
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QLabel
from PyQt5 import uic
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QFont
import PyQt5.QtGui as QtGui

import numpy as np
from mplwidget import MplWidget

from devices import *

def config_logger(name: str=__name__, level: int=logging.DEBUG):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.propagate = False
        logger.setLevel(level)
        f_str = '%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s'
        log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
    return logger


ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'LoggerPlotterPy'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '_4_4'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

# Configure logging
logger = config_logger(level=logging.INFO)

# Global configuration dictionary
config = {}


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        # Initialization of the superclass
        super(MainWindow, self).__init__(parent)
        # Class members definition
        self.refresh_flag = False
        self.last_selection = -1
        self.sig_list = []
        self.old_sig_list = []
        self.signals = []
        self.extra_cols = []
        # Load the UI
        uic.loadUi(UI_FILE, self)
        # Configure logging
        self.logger = logger
        # Connect signals with the slots
        self.pushButton_2.clicked.connect(self.select_log_file)
        self.comboBox_2.currentIndexChanged.connect(self.fileSelectionChanged)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
        self.comboBox_1.currentIndexChanged.connect(self.logLevelIndexChanged)
        self.plainTextEdit_2.textChanged.connect(self.refresh_on)
        self.plainTextEdit_3.textChanged.connect(self.refresh_on)
        self.plainTextEdit_4.textChanged.connect(self.refresh_on)
        self.plainTextEdit_5.textChanged.connect(self.refresh_on)
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionOpen.triggered.connect(self.select_log_file)
        self.actionPlot.triggered.connect(self.show_plot_pane)
        self.actionLog.triggered.connect(self.show_log_pane)
        self.actionParameters.triggered.connect(self.show_param_pane)
        self.actionAbout.triggered.connect(self.show_about)
        # Additional configuration
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        header = self.tableWidget_3.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # QHeaderView.Stretch QHeaderView.ResizeToContents
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
        # Disable text wrapping in log window
        self.plainTextEdit.setLineWrapMode(0)
        # Clock label at status bar
        self.clock = QLabel(" ")
        self.clock.setFont(QFont('Open Sans Bold', 16, weight=QFont.Bold))
        self.statusBar().addPermanentWidget(self.clock)
        # default settings
        self.setDefaultSettings()
        print(APPLICATION_NAME + APPLICATION_VERSION + ' started')
        # Restore settings
        self.restoreSettings()
        # Additional decorations
        # self.tableWidget_3.horizontalHeader().
        # Read data files
        self.parseFolder()

    def refresh_on(self):
        self.refresh_flag = True

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + ' Version ' + APPLICATION_VERSION +
                                '\nPlot Logger saved shot logs and traces.', QMessageBox.Ok)

    def show_plot_pane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(False)
        self.saveSettings()
        self.table_selection_changed()
        if self.refresh_flag:
            self.refresh_flag = False
            self.parseFolder()
    
    def show_log_pane(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(True)
        self.actionParameters.setChecked(False)

    def show_param_pane(self):
        self.stackedWidget.setCurrentIndex(2)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(True)
        # ##self.tableWidget.horizontalHeader().setVisible(True)
        # Decode global config
        # clear table
        self.tableWidget.setRowCount(0)
        n = 0
        for key in config:
            self.tableWidget.insertRow(n)
            item = QTableWidgetItem(str(key))
            self.tableWidget.setItem(n, 0, item)
            item = QTableWidgetItem(str(config[key]))
            self.tableWidget.setItem(n, 1, item)
            n += 1

    def select_log_file(self):
        """Opens a file select dialog"""
        # define current dir
        if self.log_file_name is None:
            d = "./"
        else:
            d = os.path.dirname(self.log_file_name)
        fileOpenDialog = QFileDialog(caption='Select Log File', directory=d)
        # open file selection dialog
        fn = fileOpenDialog.getOpenFileName()
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

    def table_selection_changed(self):
        def sig(name):
            for sg in self.sig_list:
                if sg.name == name:
                    return sg
            return None

        try:
            # if selection is empty
            if len(self.tableWidget_3.selectedRanges()) < 1:
                return
            row = self.tableWidget_3.selectedRanges()[0].topRow()
            # if selected the same row
            if self.last_selection == row:
                return
            # different row selected
            self.logger.log(logging.DEBUG, 'Selection changed to row %i' % row)
            if row < 0:
                return
            folder = os.path.dirname(self.log_file_name)
            zipFileName = self.log_table.column("File")[row]
            self.logger.log(logging.DEBUG, 'Used zip File %s' % zipFileName)
            # read zip file listing
            self.dataFile = DataFile(zipFileName, folder=folder)
            # read signals from zip file
            self.old_sig_list = self.sig_list
            self.sig_list = self.dataFile.read_all_signals()
            # reorder plots according to columns order in the table
            self.signals = []
            for c in self.columns:
                for s in self.sig_list:
                    if s.name == c:
                        self.signals.append(self.sig_list.index(s))
                        break
            # add extra plots from plainTextEdit_4
            extra_plots = self.plainTextEdit_4.toPlainText().split('\n')
            for p in extra_plots:
                if p.strip() != "":
                    try:
                        result = eval(p)
                        if isinstance(result, Signal):
                            s = result
                        else:
                            key, x_val, y_val = result
                            if key != '':
                                s = Signal()
                                s.x = x_val
                                s.y = y_val
                                s.name = key
                        self.sig_list.append(s)
                        self.signals.append(self.sig_list.index(s))
                    except:
                        self.logger.info('Plot eval() error in %s' % p)
                        self.logger.debug('Exception:', exc_info=True)
            # plot signals
            layout = self.scrollAreaWidgetContents_3.layout()
            jj = 0
            col = 0
            row = 0
            col_count = 3
            for c in self.signals:
                s = self.sig_list[c]
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
                    for s1 in self.old_sig_list:
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
                #axes.legend(loc='best') 
                # Show plot
                mplw.canvas.draw()
                jj += 1
            # Remove unused plot widgets
            while jj < layout.count() :
                item = layout.takeAt(layout.count()-1)
                if not item:
                    continue
                w = item.widget()
                if w:
                    w.deleteLater()
            self.last_selection = row
        except:
            self.logger.log(logging.WARNING, 'Exception in tableSelectionChanged')
            self.logger.debug('Exception:', exc_info=True)

    def fileSelectionChanged(self, m):
        self.logger.debug('Selection changed to %s' % str(m))
        if m < 0:
            return
        newLogFile = str(self.comboBox_2.currentText())
        if not os.path.exists(newLogFile):
            self.logger.warning('File %s not found' % newLogFile)
            self.comboBox_2.removeItem(m)
            return
        if self.log_file_name != newLogFile:
            self.log_file_name = newLogFile
            self.parseFolder()

    def logLevelIndexChanged(self, m):
        levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                  logging.WARNING, logging.ERROR, logging.CRITICAL]
        if m >= 0:
            self.logger.setLevel(levels[m])
 
    def onQuit(self) :
        # save global settings
        self.saveSettings()
        timer.stop()
        
    def sortedColumns(self):
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

    def parseFolder(self, file_name=None):
        #self.logger.log(logging.DEBUG, 'parseFolder')
        try:
            if file_name is None:
                file_name = self.log_file_name
            if file_name is None:
                return
            self.logger.log(logging.DEBUG, 'Reading log file %s' % file_name)
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
            for t in self.included:
                if t in self.log_table.headers:
                    self.columns.append(t)
            for t in self.log_table.headers:
                if t not in self.excluded and t not in self.columns:
                    self.columns.append(t)
            # disable table update events
            self.tableWidget_3.itemSelectionChanged.disconnect(self.table_selection_changed)
            # clear table
            self.tableWidget_3.setRowCount(0)
            self.tableWidget_3.setColumnCount(0)
            # refill table widget
            # insert columns
            row = 0
            for column in self.columns:
                self.tableWidget_3.insertColumn(row)
                self.tableWidget_3.setHorizontalHeaderItem(row, QTableWidgetItem(column))
                row += 1
            # insert and fill rows
            for row in range(self.log_table.rows):
                self.tableWidget_3.insertRow(row)
                n = 0
                for column in self.columns:
                    col = self.log_table.find_col(column)
                    try:
                        fmt = config['format'][self.log_table.headers[col]]
                        txt = fmt % (self.log_table.val[col][row], self.log_table.unit[col][row])
                    except:
                        txt = self.log_table.data[col][row]
                    item = QTableWidgetItem(txt)
                    if row > 0:
                        v = self.log_table.val[col][row]
                        if v is None:
                            v = 0.0
                        v1 = self.log_table.val[col][row - 1]
                        if v1 is None:
                            v1 = 0.0
                        try:
                            thr = 0.03
                            thr = config['threshold']
                            thr = config['thresholds'][self.log_table.headers[col]]
                        except:
                            pass
                        flag = True
                        if thr > 0.0:
                            flag = (v != 0.0) and (abs((v1-v)/v) > thr)
                        elif thr < 0.0:
                            flag = abs(v1 - v) > -thr
                        if flag:
                            item.setFont(QFont('Open Sans Bold', weight=QFont.Bold))
                        else:
                            item.setFont(QFont('Open Sans', weight=QFont.Normal))
                    self.tableWidget_3.setItem(row, n, item)
                    n += 1
            # enable table update events
            self.tableWidget_3.itemSelectionChanged.connect(self.table_selection_changed)
            self.tableWidget_3.resizeColumnsToContents()
            # select last row of widget -> tableSelectionChanged will be fired
            self.last_selection = -1
            self.tableWidget_3.scrollToBottom()
            self.tableWidget_3.setFocus()
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount()-1)
        except:
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.logger.debug('Exception:', exc_info=True)
        return
    
    def saveSettings(self, folder='', fileName=CONFIG_FILE) :
        fullName = os.path.join(str(folder), fileName)
        try:
            # save window size and position
            p = self.pos()
            s = self.size()
            self.conf['main_window'] = {'size':(s.width(), s.height()), 'position':(p.x(), p.y())}
            self.conf['folder'] = self.log_file_name
            self.conf['history'] = [str(self.comboBox_2.itemText(count)) for count in range(min(self.comboBox_2.count(), 10))]
            self.conf['history_index'] = self.comboBox_2.currentIndex()
            self.conf['log_level'] = self.logger.level
            self.conf['included'] = str(self.plainTextEdit_2.toPlainText())
            self.conf['excluded'] = str(self.plainTextEdit_3.toPlainText())
            self.conf['cb_1'] = self.checkBox_1.isChecked()
            self.conf['cb_2'] = self.checkBox_2.isChecked()
            self.conf['extra_plot'] = str(self.plainTextEdit_4.toPlainText())
            self.conf['extra_col'] = str(self.plainTextEdit_5.toPlainText())
            if os.path.exists(fullName):
                # try to read old config to confirm correct syntax
                with open(fullName, 'r') as configfile:
                    s = configfile.read()
            with open(fullName, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.info('Configuration saved to %s'%fullName)
            return True
        except :
            self.logger.log(logging.WARNING, 'Configuration save error to %s'%fullName)
            self.logger.debug('Exception:', exc_info=True)
            return False
        
    def restoreSettings(self, folder='', fileName=CONFIG_FILE) :
        fullName = os.path.join(str(folder), fileName)
        try :
            with open(fullName, 'r') as configfile:
                s = configfile.read()
            self.conf = json.loads(s)
            global config
            config = self.conf
            # Log level restore
            if 'log_level' in self.conf:
                v = self.conf['log_level']
                self.logger.setLevel(v)
                levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                          logging.WARNING, logging.ERROR, logging.CRITICAL, logging.CRITICAL+10]
                mm = 0
                for m in range(len(levels)):
                    if v < levels[m]:
                        mm = 0
                        break
                self.comboBox_1.setCurrentIndex(mm-1)
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
            if 'cb_1' in self.conf:
                self.checkBox_1.setChecked(self.conf['cb_1'])
            if 'cb_2' in self.conf:
                self.checkBox_2.setChecked(self.conf['cb_2'])
            if 'history' in self.conf:
                self.comboBox_2.currentIndexChanged.disconnect(self.fileSelectionChanged)
                self.comboBox_2.clear()
                self.comboBox_2.addItems(self.conf['history'])
                self.comboBox_2.currentIndexChanged.connect(self.fileSelectionChanged)
            if 'history_index' in self.conf:
                self.comboBox_2.setCurrentIndex(self.conf['history_index'])
            self.logger.log(logging.INFO, 'Configuration restored from %s' % fullName)
            return True
        except :
            self.logger.log(logging.WARNING, 'Configuration restore error from %s' % fullName)
            self.logger.debug('Exception:', exc_info=True)
            return False

    def setDefaultSettings(self):
        try :
            # some class variables
            self.previous_color = '#ffff00'
            self.trace_color = '#00ff00'
            self.mark_color = '#ff0000'
            self.zero_color = '#0000ff'
            # window size and position
            self.resize(QSize(640, 480))
            self.move(QPoint(0, 0))
            self.log_file_name = None
            self.conf = {}
            #self.logger.log(logging.DEBUG, 'Default configuration set.')
            return True
        except :
            # print error info    
            self.logger.log(logging.WARNING, 'Default configuration error.')
            self.logger.debug('Exception:', exc_info=True)
            return False

    def printExceptionInfo(self, level=logging.ERROR):
        #excInfo = sys.exc_info()
        #(tp, value) = sys.exc_info()[:2]
        #self.logger.log(level, 'Exception %s %s'%(str(tp), str(value)))
        self.logger.log(level, "Exception ", exc_info=True)

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

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)
        # check if lock file exists
        if self.is_locked():
            return
        oldSize = self.log_table.file_size
        newSize = os.path.getsize(self.log_file_name)
        if newSize <= oldSize:
            return
        self.parseFolder()


class LogTable():
    def __init__(self, file_name: str, folder: str = "", extra_cols=None):
        if extra_cols is None:
            extra_cols = []
        self.logger = config_logger()
        self.data = [[],]
        self.val = [[],]
        self.unit = [[],]
        self.headers = []
        self.file_name = None
        self.file_size = -1
        self.file_lines = -1
        self.rows = 0
        self.columns = 0

        # Full file name
        fn = os.path.join(folder, file_name)
        if not os.path.exists(fn) :
            self.logger.info('File %s does not exist' % file_name)
            return
        # read file to buf
        with open(fn, "r") as stream:
            buf = stream.read()
        if len(buf) <= 0 :
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
            self.logger.info('Wrong date/time format "%s", line skipped' % flds[0])
            return
        # split time and date
        tm = flds[0].split(" ")[1].strip()
        # preserv only time
        flds[0] = "Time=" + tm
        # sdd row to table
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
                self.logger.debug('Non float value "%s"' % vu[0])
            self.val[j][self.rows - 1] = v
            # units
            try:
                u = vu[1].strip()
            except:
                u = ''
            self.unit[j][self.rows - 1] = u

    def add_extra_columns(self, extra_cols):
        for row in range(self.rows):
            for column in extra_cols:
                if column.strip() != "":
                    try:
                        key, value, units = eval(column)
                        if (key is not None) and (key != ''):
                            j = self.add_column(key)
                            self.data[j][row] = str(value) + ' ' + str(units)
                            self.val[j][row] = float(value)
                            self.unit[j][row] = str(units)
                    except:
                        self.logger.log(logging.INFO, 'Column eval() error in \n              %s' % column)

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
            self.logger.debug('%d additional lines in %s' % (len(lines)-self.file_lines, self.file_name))
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
        for item in self.val:
            item.append(0.0)
        for item in self.unit:
            item.append("")
        self.rows += 1
    
    def remove_row(self, row):
        for item in self.data:
            del item[row]
        for item in self.val:
            del item[row]
        for item in self.unit:
            del item[row]
        self.rows -= 1

    def col_number(self, col):
        coln = col
        if isinstance(col, str):
            if col not in self.headers:
                return None
            coln = self.headers.index(col)
        return coln

    def remove_column(self, col):
        coln = self.col_number(col)
        if coln is None:
            return
        del self.data[coln]
        del self.val[coln]
        del self.unit[coln]
        del self.headers[coln]
        self.columns -= 1

    def item(self, *args):
        if len(args) >= 2:
            col = args[1]
            row = args[0]
        else:
            col = args[0]
            row = -1
        coln = self.col_number(col)
        if col is None:
            return ''
        return self.data[coln][row]

    def value(self, *args):
        if len(args) >= 2:
            col = args[1]
            row = args[0]
        else:
            col = args[0]
            row = -1
        coln = self.col_number(col)
        #if coln is None or coln >= len(self.val):
        #    return 0.0
        return self.val[coln][row]

    def get_item(self, row, col):
        return self.item(row, col)

    def set_item(self, row, col, val):
        coln = self.col_number(col)
        self.data[coln][row] = val
        vu = val.split(" ")
        try:
            v = float(vu[0].strip().replace(',', '.'))
        except:
            v = 0.0
        self.val[coln][row] = v
        try:
            u = vu[1].strip()
        except:
            u = ''
        self.unit[coln][row] = u
        return True

    def column(self, col):
        coln = self.col_number(col)
        return self.data[coln]

    def row(self, row):
        return [self.data[n][row] for n in range(len(self.headers))]

    def add_column(self, col_name):
        if col_name is None or col_name == '':
            return -1
        # skip if column exists
        if col_name in self.headers:
            return self.headers.index(col_name)
        self.headers.append(col_name)
        new_col = [""] * self.rows
        self.data.append(new_col)
        new_col = [0.0] * self.rows
        self.val.append(new_col)
        new_col = [""] * self.rows
        self.unit.append(new_col)
        self.columns += 1
        return self.headers.index(col_name)
        
    def find_col(self, col_name):
        if col_name in self.headers:
            return self.headers.index(col_name)
        else:
            return -1

    def __contains__(self, item):
        return item in self.headers

    def __len__(self):
        return len(self.headers)

    def __getitem__(self, item):
        return self.column[item]
    

class Signal:
    def __init__(self, *args, **kwargs):
        #self.logger = logging.getLogger(__name__)
        # Default settings
        self.x = np.zeros(1)
        self.y = np.zeros(1)
        self.params = {}
        self.name = ''
        self.unit = ''
        self.scale = 1.0
        self.value = 0.0
        self.marks = {}
        # From kwargs
        if 'x' in kwargs:
            self.x = kwargs['x']
        if 'y' in kwargs:
            self.y = kwargs['y']
        if 'params' in kwargs:
            self.params = kwargs['params']
        if 'name' in kwargs:
            self.name = kwargs['name']
        if 'unit' in kwargs:
            self.unit = kwargs['unit']
        if 'scale' in kwargs:
            self.scale = kwargs['scale']
        if 'value' in kwargs:
            self.value = kwargs['value']
        if 'marks' in kwargs:
            self.marks = kwargs['marks']


class DataFile:
    def __init__(self, fileName, folder=""):
        #self.logger = logging.getLogger(__name__)
        self.logger = config_logger()
        self.file_name = None
        self.files = []
        self.signals = []
        fn = os.path.join(folder, fileName)
        with zipfile.ZipFile(fn, 'r') as zipobj:
            self.files = zipobj.namelist()
        self.file_name = fn
        for f in self.files:
            if f.find("chan") >= 0 and f.find("param") < 0:
                self.signals.append(f)
        
    def read_signal(self, signal_name: str) -> Signal:
        signal = Signal()
        if signal_name not in self.signals:
            self.logger.log(logging.INFO, "No signal %s in the file %s" % (signal_name, self.file_name))
            return signal
        with zipfile.ZipFile(self.file_name, 'r') as zipobj:
            buf = zipobj.read(signal_name)
            pf = signal_name.replace('chan', 'paramchan')
            pbuf = zipobj.read(pf)
        lines = buf.split(b"\r\n")
        n = len(lines)
        if n < 2:
            self.logger.log(logging.ERROR, "No data for signal %s" % signal_name)
            return signal
        signal.x = np.empty(n)
        signal.y = np.empty(n)
        ii = 0
        for ln in lines:
            xy = ln.split(b'; ')
            try:
                signal.x[ii] = float(xy[0].replace(b',', b'.'))
                signal.y[ii] = float(xy[1].replace(b',', b'.'))
            except:
                self.logger.log(logging.ERROR, "Wrong data for signal %s" % signal_name)
                #return signal
                signal.x[ii] = 0.0
                signal.y[ii] = 0.0
            ii += 1
        # read parameters        
        signal.params = {}
        lines = pbuf.split(b"\r\n")
        for ln in lines:
            kv = ln.split(b'=')
            if len(kv) >= 2:
                signal.params[kv[0].strip()] = kv[1].strip()
        # scale to units
        if b'display_unit' in signal.params:
            signal.scale = float(signal.params[b'display_unit'])
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
                    ms = int((float(signal.params[k]) - x0) / dx)
                    ml = int(float(signal.params[k.replace(b"_start", b'_length')]) / dx)
                    mv = signal.y[ms:ms+ml].mean()
                except:
                    self.logger.log(logging.WARNING, 'Mark %s value can not be computed for %s' % (k, signal_name))
                    ms = 0
                    ml = 0
                    mv = 0.0
                signal.marks[k.replace(b"_start", b'').decode('ascii')] = (ms, ml, mv)
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
    # instantiate the main window
    dmw = MainWindow()
    app.aboutToQuit.connect(dmw.onQuit)
    # show it
    dmw.show()
    # defile and start timer task
    timer = QTimer()
    timer.timeout.connect(dmw.timer_handler)
    timer.start(1000)
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())
