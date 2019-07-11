# coding: utf-8
'''
Created on Jul 2, 2017

@author: sanin
''' 
# used to parse files more easily
#from __future__ import with_statement
#from __future__ import print_function

import os.path
import sys
import json
import logging
import zipfile
import time

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QLabel
from PyQt5 import uic
from PyQt5.QtCore import QPoint, QSize
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QFont

import numpy as np
from mplwidget import MplWidget

progName = 'LoggerPlotterPy'
progVersion = '_4_3'
settingsFile = progName + '.json'

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                                       datefmt='%H:%M:%S')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

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
        uic.loadUi('LoggerPlotter.ui', self)

        # Configure logging
        self.logger = logger
        self.text_edit_handler = TextEditHandler(self.plainTextEdit)
        self.text_edit_handler.setFormatter(log_formatter)
        self.logger.addHandler(self.text_edit_handler)

        # Connect signals with the slots
        self.pushButton_2.clicked.connect(self.selectLogFile)
        self.comboBox_2.currentIndexChanged.connect(self.fileSelectionChanged)
        self.tableWidget_3.itemSelectionChanged.connect(self.table_sel_changed)
        self.comboBox_1.currentIndexChanged.connect(self.logLevelIndexChanged)
        self.plainTextEdit_2.textChanged.connect(self.refresh_on)
        self.plainTextEdit_3.textChanged.connect(self.refresh_on)
        self.plainTextEdit_4.textChanged.connect(self.refresh_on)
        self.plainTextEdit_5.textChanged.connect(self.refresh_on)
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionOpen.triggered.connect(self.selectLogFile)
        self.actionPlot.triggered.connect(self.showPlotPane)
        self.actionLog.triggered.connect(self.show_log_pane)
        self.actionParameters.triggered.connect(self.show_param_pane)
        self.actionAbout.triggered.connect(self.showAbout)

        # Additional configuration
        # Disable text wrapping in log window
        self.plainTextEdit.setLineWrapMode(0)
        # Clock label at status bar
        self.clock = QLabel(" ")
        self.clock.setFont(QFont('Open Sans Bold', 16, weight=QFont.Bold))
        self.statusBar().addPermanentWidget(self.clock)
        
        self.setDefaultSettings()

        print(progName + progVersion + ' started')

        # Restore settings from default config file
        self.restoreSettings()
        
        # Additional decorations
        #self.tableWidget_3.horizontalHeader().
        
        # Read data files
        self.parseFolder()
        
        # Connect mouse button press event
        #self.cid = self.mplWidget.canvas.mpl_connect('button_press_event', self.onclick)
        #self.mplWidget.canvas.mpl_disconnect(cid)

    def refresh_on(self):
        self.refresh_flag = True

    def showAbout(self):
        QMessageBox.information(self, 'About', progName + ' Version ' + progVersion + 
                                '\nPlot Logger traces and save shot logs.', QMessageBox.Ok)

    def showPlotPane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(False)
        self.table_sel_changed()
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
        self.tableWidget.horizontalHeader().setVisible(True)
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

    def selectLogFile(self):
        """Opens a file select dialog"""
        # define current dir
        if self.logFileName is None:
            d = "./"
        else:
            d = os.path.dirname(self.logFileName)
        fileOpenDialog = QFileDialog(caption='Select log file', directory = d)
        # open file selection dialog
        fn = fileOpenDialog.getOpenFileName()
        # if a fn is not empty
        if fn:
            # Qt4 and Qt5 compatibility workaround
            if len(fn[0]) > 1:
                fn = fn[0]
            # different file selected
            if self.logFileName == fn:
                return
            i = self.comboBox_2.findText(fn)
            if i < 0:
                # add item to history
                self.comboBox_2.insertItem(-1, fn)
                i = 0
            # change selection and fire callback
            self.comboBox_2.setCurrentIndex(i)
    
    def table_sel_changed(self):
        def sig(name):
            for s in self.sig_list:
                if s.name == name:
                    return s
            return None
        self.logger.log(logging.DEBUG, 'Table selection changed')
        try:
            if len(self.tableWidget_3.selectedRanges()) < 1:
                return
            row = self.tableWidget_3.selectedRanges()[0].topRow()
            if self.last_selection == row:
                return
            self.logger.log(logging.DEBUG, 'Table selection changed to row %i'%row)
            if row < 0:
                return
            folder = os.path.dirname(self.logFileName)
            #self.logger.log(logging.DEBUG, 'Folder %s'%folder)
            zipFileName = self.logTable.column("File")[row]
            self.logger.log(logging.DEBUG, 'Zip File %s'%zipFileName)
            # read zip file listing
            self.dataFile = DataFile(zipFileName, folder = folder)
            # read signals from zip file
            self.old_sig_list = self.sig_list
            self.sig_list = self.dataFile.read_all_signals()
            layout = self.scrollAreaWidgetContents_3.layout()
            # reorder plots according to columns order in the table
            self.signals = []
            for c in self.columns:
                for s in self.sig_list:
                    if s.name == c:
                        self.signals.append(self.sig_list.index(s))
                        break
            # Add extra plots from plainTextEdit_4
            extra_plots = self.plainTextEdit_4.toPlainText().split('\n')
            for p in extra_plots:
                if p.strip() != "":
                    try:
                        key, x_val, y_val = eval(p)
                        if key != '':
                            s = Signal()
                            s.x = x_val
                            s.y = y_val
                            s.name = key
                            self.sig_list.append(s)
                            self.signals.append(self.sig_list.index(s))
                    except:
                        self.logger.log(logging.DEBUG, 'eval() error in %s' % p)
            # Plot signals
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
                # Plot previous line
                if self.checkBox_2.isChecked():
                    for s1 in self.old_sig_list:
                        if s1.name == s.name:
                            axes.plot(s1.x, s1.y, "y-")
                            break
                # Plot main line
                axes.plot(s.x, s.y)
                # Plot 'mark' highlight
                if 'mark' in s.marks:
                    m1 = s.marks['mark'][0]
                    m2 = m1 + s.marks['mark'][1]
                    axes.plot(s.x[m1:m2], s.y[m1:m2], 'r')
                # Plot 'zero' highlight
                if 'zero' in s.marks:
                    m1 = s.marks['zero'][0]
                    m2 = m1 + s.marks['zero'][1]
                    axes.plot(s.x[m1:m2], s.y[m1:m2], 'r')
                # Decorate the plot
                axes.grid(True)
                axes.set_title('{0} = {1:5.2f} {2}'.format(s.name, s.value, s.unit))
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
            self.printExceptionInfo(level=logging.DEBUG)
 
    def fileSelectionChanged(self, i):
        self.logger.debug('File selection changed to %s'%str(i))
        if i < 0:
            return
        newLogFile = str(self.comboBox_2.currentText())
        if not os.path.exists(newLogFile):
            self.logger.warning('File %s is not found'%newLogFile)
            self.comboBox_2.removeItem(i)
            return
        if self.logFileName != newLogFile:
            self.logFileName = newLogFile
            self.parseFolder()

    def logLevelIndexChanged(self, m):
        #self.logger.debug('Selection changed to %s'%str(m))
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
            if t in self.logTable.headers:
                columns.append(self.logTable.headers.index(t))
        for t in self.logTable.headers:
            if t not in excluded and t not in columns:
                columns.append(self.logTable.headers.index(t))
        return columns

    def parseFolder(self, file_name=None):
        self.logger.log(logging.DEBUG, 'parseFolder')
        try:
            if file_name is None:
                file_name = self.logFileName
            if file_name is None:
                return
            self.logger.log(logging.DEBUG, 'Reading log file %s' % file_name)
            self.extra_cols = self.plainTextEdit_5.toPlainText().split('\n')
            # Read log file content to logTable
            self.logTable = LogTable(file_name, extra_cols=self.extra_cols)
            if self.logTable.file_name is None:
                return
            self.logFileName = self.logTable.file_name
            # Create sorted displayed columns list
            self.included = self.plainTextEdit_2.toPlainText().split('\n')
            self.excluded = self.plainTextEdit_3.toPlainText().split('\n')
            self.columns = []
            for t in self.included:
                if t in self.logTable.headers:
                    self.columns.append(t)
            for t in self.logTable.headers:
                if t not in self.excluded and t not in self.columns:
                    self.columns.append(t)
            # disable table update events
            self.tableWidget_3.itemSelectionChanged.disconnect(self.table_sel_changed)
            # clear table
            self.tableWidget_3.setRowCount(0)
            self.tableWidget_3.setColumnCount(0)
            # refill table widget
            # insert columns
            k = 0
            for c in self.columns:
                self.tableWidget_3.insertColumn(k)
                self.tableWidget_3.setHorizontalHeaderItem(k, QTableWidgetItem(c))
                k += 1
            # insert and fill rows 
            for k in range(self.logTable.rows):
                self.tableWidget_3.insertRow(k)
                n = 0
                for c in self.columns:
                    m = self.logTable.find_col(c)
                    v = self.logTable.val[m][k]
                    try:
                        txt = config['format'][self.logTable.headers[m]]%(self.logTable.val[m][k], self.logTable.unit[m][k])
                    except:
                        txt = self.logTable.data[m][k]
                    item = QTableWidgetItem(txt)
                    if k > 0:
                        v1 = self.logTable.val[m][k-1]
                        if v!=0.0 and abs(v1-v)/abs(v) > 0.03:
                            #item.setForeground(QBrush(QColor(255, 0, 0)))
                            item.setFont(QFont('Open Sans Bold', weight=QFont.Bold))
                        else:
                            #item.setForeground(QBrush(QColor(0, 0, 0)))
                            item.setFont(QFont('Open Sans', weight=QFont.Normal))
                    self.tableWidget_3.setItem(k, n, item)
                    n += 1
            # enable table update events
            self.tableWidget_3.itemSelectionChanged.connect(self.table_sel_changed)
            self.tableWidget_3.resizeColumnsToContents()
            # select last row of widget -> tableSelectionChanged will be fired
            self.last_selection = -1
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount()-1)
            ##self.tableWidget_3.scrollToBottom()
        except:
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.printExceptionInfo(level=logging.DEBUG)
        return
    
    def saveSettings(self, folder='', fileName=settingsFile) :
        try:
            fullName = os.path.join(str(folder), fileName)
            # save window size and position
            p = self.pos()
            s = self.size()
            self.conf['main_window'] = {'size':(s.width(), s.height()), 'position':(p.x(), p.y())}
            self.conf['folder'] = self.logFileName
            self.conf['history'] = [str(self.comboBox_2.itemText(count)) for count in range(min(self.comboBox_2.count(), 10))]
            self.conf['history_index'] = self.comboBox_2.currentIndex()
            self.conf['log_level'] = self.logger.level
            self.conf['included'] = str(self.plainTextEdit_2.toPlainText())
            self.conf['excluded'] = str(self.plainTextEdit_3.toPlainText())
            self.conf['cb_1'] = self.checkBox_1.isChecked()
            self.conf['cb_2'] = self.checkBox_2.isChecked()
            self.conf['extra_plot'] = str(self.plainTextEdit_4.toPlainText())
            self.conf['extra_col'] = str(self.plainTextEdit_5.toPlainText())
            with open(fullName, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.info('Configuration saved to %s'%fullName)
            return True
        except :
            self.logger.log(logging.WARNING, 'Configuration save error to %s'%fullName)
            self.printExceptionInfo(level=logging.DEBUG)
            return False
        
    def restoreSettings(self, folder='', fileName=settingsFile) :
        try :
            fullName = os.path.join(str(folder), fileName)
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
                for m in range(len(levels)):
                    if v < levels[m]:
                        break
                self.comboBox_1.setCurrentIndex(m-1)
            # Restore window size and position
            if 'main_window' in self.conf:
                self.resize(QSize(self.conf['main_window']['size'][0], self.conf['main_window']['size'][1]))
                self.move(QPoint(self.conf['main_window']['position'][0], self.conf['main_window']['position'][1]))
            # Last folder
            if 'folder' in self.conf:
                self.logFileName = self.conf['folder']
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

            self.logger.log(logging.INFO, 'Configuration restored from %s'%fullName)
            return True
        except :
            self.logger.log(logging.WARNING, 'Configuration restore error from %s'%fullName)
            self.printExceptionInfo(level=logging.DEBUG)
            return False

    def setDefaultSettings(self) :
        try :
            # some class variables
            # window size and position
            self.resize(QSize(640, 480))
            self.move(QPoint(0, 0))
            self.logFileName = None
            self.conf = {}
            #self.logger.log(logging.DEBUG, 'Default configuration set.')
            return True
        except :
            # print error info    
            self.logger.log(logging.WARNING, 'Default configuration error.')
            self.printExceptionInfo(level=logging.DEBUG)
            return False

    def printExceptionInfo(self, level=logging.ERROR):
        #excInfo = sys.exc_info()
        #(tp, value) = sys.exc_info()[:2]
        #self.logger.log(level, 'Exception %s %s'%(str(tp), str(value)))
        self.logger.log(level, "Exception ", exc_info=True)

    def is_locked(self):
        if self.logFileName is None:
            return True
        folder = os.path.dirname(self.logFileName)
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
        oldSize = self.logTable.file_size
        newSize = os.path.getsize(self.logFileName)
        if newSize <= oldSize:
            return
        self.parseFolder()
        
    def onClick(self, event):
        print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              ('double' if event.dblclick else 'single', event.button,
               event.x, event.y, event.xdata, event.ydata))
        #a = event.canvas.getParent()
        #ntb = NavigationToolbar(event.canvas, a)
        #a.addWidget(ntb)


class LogTable():
    def __init__(self, file_name: str, folder: str = "", extra_cols: list = []) -> None:
        """

            Create LogTable object from file f_name

        :param file_name: str The name of log file containing table
        :param folder: str Folder to add in front file name
        """
        def value(s):
            return float(self.item(s).split(' ')[0].replace(',', '.'))
        self.logger = logger
        self.data = [[],]
        self.val = [[],]
        self.unit = [[],]
        self.headers = []
        self.file_name = None
        self.file_size = 0
        self.buf = None
        self.rows = 0
        self.columns = 0
        self.order = []
        
        fn = os.path.join(folder, file_name)
        if not os.path.exists(fn) :
            self.logger.info('File %s does not exist' % file_name)
            return
        with open(fn, "r") as stream:
            self.buf = stream.read()
        if len(self.buf) <= 0 :
            self.logger.info('Nothing to process in %s' % file_name)
            return
        self.file_name = fn
        self.file_size = os.path.getsize(fn)
        # Split buf to lines
        lns = self.buf.split('\n')
        self.logger.debug('%d lines in %s' % (len(lns), self.file_name))
        # loop for lines
        for ln in lns:
            # split line to fields
            flds = ln.split("; ")
            # First field should be "date time" longer than 18 symbols
            if len(flds[0]) < 19:
                # wrong line format, skip to next line
                #self.logger.debug('%d lines in %s' % (len(lns), self.file_name))
                continue
            tm = flds[0].split(" ")[1].strip()
            #tv = time.strftime()
            flds[0] = "Time=" + tm
            # add row to table
            self.add_row()
            # Iterate for key=value pairs
            for fld in flds:
                kv = fld.split("=")
                key = kv[0].strip()
                val = kv[1].strip()
                j = self.add_column(key)
                self.data[j][self.rows-1] = val
                vu = val.split(" ")
                try:
                    v = float(vu[0].strip().replace(',', '.'))
                except:
                    v = 0.0
                self.val[j][self.rows-1] = v
                try:
                    u = vu[1].strip()
                except:
                    u = ''
                self.unit[j][self.rows-1] = u
            for c in extra_cols:
                if c.strip() != "":
                    try:
                        key, val = eval(c)
                        if key != '':
                            j = self.add_column(key)
                            self.data[j][self.rows - 1] = str(val)
                            self.val[j][self.rows - 1] = float(val)
                            #self.unit[j][self.rows - 1] = ""
                    except:
                        self.logger.log(logging.DEBUG, 'eval() error in %s' % c)

    def add_row(self):
        for item in self.data:
            item.append("")
        for item in self.val:
            item.append(None)
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
        if isinstance(col, str):
            if col not in self.headers:
                return None
            col = self.headers.index(col)
        return col

    def remove_column(self, col):
        col = self.col_number(col)
        del self.data[col]
        del self.val[col]
        del self.unit[col]
        del self.headers[col]
        self.columns -= 1

    def item(self, *args):
        if len(args) >= 2:
            col = args[1]
            row = args[0]
        else:
            col = args[0]
            row = -1
        col = self.col_number(col)
        return self.data[col][row]

    def get_item(self, row, col):
        return self.item(row, col)

    def set_item(self, row, col, val):
        col = self.col_number(col)
        self.data[col][row] = val
        return True

    def column(self, col):
        col = self.col_number(col)
        return self.data[col]

    def row(self, row):
        return [self.data[n][row] for n in range(len(self.headers))]

    def add_column(self, col_name):
        if col_name is None:
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
    def __init__(self) -> None:
        #self.logger = logging.getLogger(__name__)
        self.x = np.zeros(1)
        self.y = np.zeros(1)
        self.params = {}
        self.name = ''
        self.unit = ''
        self.scale = 1.0
        self.value = 0.0
        self.marks = {}


class DataFile:
    def __init__(self, fileName, folder=""):
        #self.logger = logging.getLogger(__name__)
        self.logger = logger
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
        signal.x = np.empty(n)
        signal.y = np.empty(n)
        ii = 0
        for ln in lines:
            xy = ln.split(b'; ')
            signal.x[ii] = float(xy[0].replace(b',', b'.'))
            signal.y[ii] = float(xy[1].replace(b',', b'.'))
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
