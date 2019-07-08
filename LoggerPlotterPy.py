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

try:
    from PyQt5 import QtWidgets as QtGui # @UnusedImport
    from PyQt5.QtWidgets import QMainWindow
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtWidgets import qApp
    from PyQt5.QtWidgets import QFileDialog
    from PyQt5.QtWidgets import QTableWidgetItem
    from PyQt5.QtWidgets import QTableWidget
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5 import uic
    from PyQt5.QtCore import QPoint, QSize
    from PyQt5.QtCore import QTimer
except:
    from PyQt4 import QtGui  # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import QMainWindow # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import QApplication # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import qApp # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import QFileDialog # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import QTableWidgetItem # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import QTableWidget # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtGui import QMessageBox # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4 import uic # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtCore import QPoint, QSize # @UnresolvedImport @UnusedImport @Reimport
    from PyQt4.QtCore import QTimer # @UnresolvedImport @UnusedImport @Reimport

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


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        # Initialization of the superclass
        super(MainWindow, self).__init__(parent)

        # Load the UI
        uic.loadUi('LoggerPlotter.ui', self)

        # Configure logging
        #self.logger = logging.getLogger(__name__)
        #self.logger.setLevel(logging.DEBUG)
        #self.log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        #S                                       datefmt='%H:%M:%S')
        #self.console_handler = logging.StreamHandler()
        #self.console_handler.setFormatter(self.log_formatter)
        #self.logger.addHandler(self.console_handler)
        self.logger = logger
        self.text_edit_handler = TextEditHandler(self.plainTextEdit)
        self.text_edit_handler.setFormatter(log_formatter)
        self.logger.addHandler(self.text_edit_handler)

        # Connect signals with the slots
        self.pushButton_2.clicked.connect(self.selectLogFile)
        self.comboBox_2.currentIndexChanged.connect(self.fileSelectionChanged)
        self.tableWidget_3.itemSelectionChanged.connect(self.tableSelectionChanged)
        self.comboBox_1.currentIndexChanged.connect(self.logLevelIndexChanged)
        #self.plainTextEdit_2.textChanged.connect(self.parseFolder)
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionOpen.triggered.connect(self.selectLogFile)
        self.actionPlot.triggered.connect(self.showPlotPane)
        self.actionLog.triggered.connect(self.showLogPane)
        self.actionParameters.triggered.connect(self.showParametersPane)
        self.actionAbout.triggered.connect(self.showAbout)

        # Additional configuration
        # Disable text wrapping in log window
        self.plainTextEdit.setLineWrapMode(0)
        
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

    def showAbout(self):
        QMessageBox.information(self, 'About', progName + ' Version ' + progVersion + 
                                '\nPlot Logger traces and save shot logs.', QMessageBox.Ok)

    def showPlotPane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(False)
        self.tableSelectionChanged()
    
    def showLogPane(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(True)
        self.actionParameters.setChecked(False)

    def showParametersPane(self):
        self.stackedWidget.setCurrentIndex(2)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(True)
        self.tableWidget.horizontalHeader().setVisible(True)

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
    
    def tableSelectionChanged(self):
        try:
            if len(self.tableWidget_3.selectedRanges()) < 1:
                return
            row = self.tableWidget_3.selectedRanges()[0].topRow()
            self.logger.log(logging.DEBUG, 'Table selection changed to row %s'%str(row))
            if row < 0:
                return
            zipFileName = self.logTable.column("File")[row]
            self.logger.log(logging.DEBUG, 'ZipFile %s'%zipFileName)
            folder = os.path.dirname(self.logFileName)
            self.logger.log(logging.DEBUG, 'Folder %s'%folder)
            # read zip file listing
            self.dataFile = DataFile(zipFileName, folder = folder)
            # read signals from zip file
            self.signalsList = self.dataFile.readAllSignals()
            layout = self.scrollAreaWidgetContents_3.layout()
            # reorder plots according to columns order in the table
            self.signals = []
            for c in self.columns:
                for s in self.signalsList:
                    if s.name == c :
                        self.signals.append(self.signalsList.index(s))
            # plot signals to existing plots or add new
            jj = 0
            col = 0
            row = 0
            colCount = 3
            for c in self.signals:
                s = self.signalsList[c]
                if jj < layout.count():    
                    # use existing plot
                    mplw = layout.itemAt(jj).widget()
                else:
                    # create new signal plot
                    mplw = MplWidget()
                    mplw.setMinimumHeight(320)
                    mplw.setMinimumWidth(320)
                    #mplw.canvas.mpl_connect('button_press_event', self.onClick)
                    # add plots in colCount columns
                    layout.addWidget(mplw, row, col)
                col += 1
                if col >= colCount:
                    col = 0
                    row += 1
                # show toolbar
                if self.checkBox_1.isChecked():
                    mplw.ntb.show()
                else:
                    mplw.ntb.hide()
                # get axes
                axes = mplw.canvas.ax
                # previous traces list
                prevLines = axes.get_lines()
                # clear plot
                axes.clear()
                # plot previous line
                if len(prevLines) > 0 and self.checkBox_2.isChecked():
                    k = 0
                    if len(prevLines) == 4:
                        k = 1
                    axes.plot(prevLines[k].get_xdata(), prevLines[k].get_ydata(), "y-")
                #plot main line
                axes.plot(s.x, s.y)
                # add mark highlight
                if 'mark' in s.marks:
                    m1 = s.marks['mark'][0]
                    m2 = m1 + s.marks['mark'][1]
                    axes.plot(s.x[m1:m2], s.y[m1:m2])
                # add zero highlight
                if 'zero' in s.marks:
                    m1 = s.marks['zero'][0]
                    m2 = m1 + s.marks['zero'][1]
                    axes.plot(s.x[m1:m2], s.y[m1:m2], 'r')
                # decorate the plot
                axes.grid(True)
                axes.set_title('{0} = {1:5.2f} {2}'.format(s.name, s.value, s.unit))
                axes.set_xlabel('Time, ms')
                axes.set_ylabel(s.name + ', ' + s.unit)
                #axes.legend(loc='best') 
                # show plot
                mplw.canvas.draw()
                jj += 1
            # remove unused plots
            while jj < layout.count() :    
                item = layout.takeAt(layout.count()-1)
                if not item:
                    continue
                w = item.widget()
                if w:
                    w.deleteLater()
        except:
            self.printExceptionInfo()
 
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

    def parseFolder(self, fn=None):
        try:
            if fn is None:
                fn = self.logFileName
            if fn is None:
                return
            self.logger.log(logging.DEBUG, 'Reading log file %s'%fn)
            # read log file content to logTable
            self.logTable = LogTable(fn)
            if self.logTable.file_name is None:
                return
            self.logFileName = self.logTable.file_name
            # create sorted displayed columns list
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
            self.tableWidget_3.itemSelectionChanged.disconnect(self.tableSelectionChanged)
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
                    m = self.logTable.find(c)
                    self.tableWidget_3.setItem(k, n, QTableWidgetItem(self.logTable.data[m][k]))
                    n += 1
            # enable table update events
            self.tableWidget_3.itemSelectionChanged.connect(self.tableSelectionChanged)
            # select last row of widget -> fileSelectionChanged will be fired 
            self.tableWidget_3.resizeColumnsToContents()
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount()-1)
            ##self.tableWidget_3.scrollToBottom()
            return
        except :
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.printExceptionInfo()
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
            with open(fullName, 'w') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.info('Configuration saved to %s'%fullName)
            return True
        except :
            self.printExceptionInfo(level=logging.DEBUG)
            self.logger.log(logging.WARNING, 'Configuration save error to %s'%fullName)
            return False
        
    def restoreSettings(self, folder='', fileName=settingsFile) :
        try :
            fullName = os.path.join(str(folder), fileName)
            with open(fullName, 'r') as configfile:
                s = configfile.read()
            self.conf = json.loads(s)
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
            self.printExceptionInfo(level=logging.DEBUG)
            self.logger.log(logging.WARNING, 'Configuration restore error from %s'%fullName)
            return False

    def setDefaultSettings(self) :
        try :
            # some class variables
            self.my_counter = 0
            # window size and position
            self.resize(QSize(640, 480))
            self.move(QPoint(0, 0))
            self.logFileName = None
            self.conf = {}
            #self.logger.log(logging.DEBUG, 'Default configuration set.')
            return True
        except :
            # print error info    
            self.printExceptionInfo(level=logging.DEBUG)
            self.logger.log(logging.WARNING, 'Default configuration error.')
            return False

    def printExceptionInfo(self):
        #excInfo = sys.exc_info()
        #(tp, value) = sys.exc_info()[:2]
        #self.logger.log(level, 'Exception %s %s'%(str(tp), str(value)))
        self.logger.error("Exception ", exc_info=True)

    def timerHandler(self):
        #self.label_5.setText("Timer" + " %d tick" % self.my_counter)
        self.my_counter += 1
        # check if lock file exists
        if self.logFileName is None:
            return
        folder = os.path.dirname(self.logFileName)
        file = os.path.join(folder, "lock.lock")
        if os.path.exists(file):
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
    def __init__(self, f_name: str, folder: str = "") -> None:
        """

            Create LogTable object from file f_name

        :param f_name: str The name of log file containing table
        :param folder: str Folder to add in front file name
        """
        self.logger = logging.getLogger(__name__)
        self.data = [[],]
        self.headers = []
        self.file_name = None
        self.file_size = 0
        self.buf = None
        self.rows = 0
        self.columns = 0
        self.order = []
        
        fn = os.path.join(folder, f_name)
        if not os.path.exists(fn) :
            self.logger.info('File %s does not exist' % self.file_name)
            return
        with open(fn, "r") as stream:
            self.buf = stream.read()
        if len(self.buf) <= 0 :
            self.logger.info('Nothing to process in %s' % self.file_name)
            return
        self.file_name = fn
        self.file_size = os.path.getsize(fn)
        # split buf to lines
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
            flds[0] = "Time=" + tm
            # add row to table
            self.add_row()
            # Iterate for key=value pairs
            for fld in flds:
                kv = fld.split("=")
                key = kv[0].strip()
                val = kv[1].strip()
                if key not in self.headers:
                    self.add_column(key)
                j = self.headers.index(key)
                self.data[j][self.rows-1] = val

    def add_row(self):
        for item in self.data:
            item.append("")
        self.rows += 1
    
    def removeRow(self, row):
        for item in self.data:
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
        del self.headers[col]
        self.columns -= 1

    def item(self, row, col):
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
        self.columns += 1 
        return self.headers.index(col_name)
        
    def find(self, col_name):
        if col_name in self.headers:
            return self.headers.index(col_name)
        else:
            return -1

    def __contains__(self, item):
        return item in self.headers

    def __len__(self):
        return len(self.headers)

    def __getitem__(self, item):
        return self.data[self.headers.index(item)]
    

class Signal:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.x = np.zeros(1)
        self.y = self.x.copy()
        self.params = {}
        self.name = ''
        self.unit = ''
        self.scale = 1.0
        self.value = 0.0
        self.marks = {}

    def plot(self, widget = None):
        if widget is None:
            # create new signal plot
            widget = MplWidget()
            widget.setMinimumHeight(320)
            widget.setMinimumWidth(320)
        axes = widget.canvas.ax
        prevLines = axes.get_lines()
        axes.clear()
        # plot previous line
        if len(prevLines) > 0:
            k = 0
            if len(prevLines) == 4:
                k = 1
            axes.plot(prevLines[k].get_xdata(), prevLines[k].get_ydata(), "y-")
        #plot main line
        axes.plot(self.x, self.y)
        if 'mark' in self.marks:
            m1 = self.marks['mark'][0]
            m2 = m1 + self.marks['mark'][1]
            axes.plot(self.x[m1:m2], self.y[m1:m2])
        if 'zero' in self.marks:
            m1 = self.marks['zero'][0]
            m2 = m1 + self.marks['zero'][1]
            axes.plot(self.x[m1:m2], self.y[m1:m2], 'r')
        # decorate the plot
        axes.grid(True)
        axes.set_title('{0} = {1:5.2f} {2}'.format(self.name, self.value, self.unit))
        axes.set_xlabel('Time, ms')
        axes.set_ylabel(self.name + ', ' + self.unit)
        #axes.legend(loc='best')
        return widget 


class DataFile:
    def __init__(self, fileName, folder=""):
        self.logger = logging.getLogger(__name__)
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

    def readAllSignals(self):
        signalsList = []
        for s in self.signals:
            signalsList.append(self.read_signal(s))
        return signalsList


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
    timer.timeout.connect(dmw.timerHandler)
    timer.start(1000)
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())