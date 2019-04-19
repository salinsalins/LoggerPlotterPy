# coding: utf-8
'''
Created on Jul 2, 2017

@author: sanin
''' 
# used to parse files more easily
from __future__ import with_statement
from __future__ import print_function

import os.path
import sys
import json
import logging
import zipfile

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import uic
from PyQt5.QtCore import QPoint, QSize

import numpy as np
from mplwidget import MplWidget
# my imports

progName = 'LoggerPlotterPy'
progVersion = '_1_0'
settingsFile = progName + '.json'
logFile =  progName + '.log'

# logging to the text panel
class TextEditHandler(logging.Handler):
    widget = None
    
    def __init__(self, wdgt=None):
        logging.Handler.__init__(self)
        self.widget = wdgt

    def emit(self, record):
        log_entry = self.format(record)
        if self.widget is not None:
            self.widget.appendPlainText(log_entry)

class MainWindow(QMainWindow):
    """Customization for Qt Designer created window"""
    def __init__(self, parent=None):
        # initialization of the superclass
        super(MainWindow, self).__init__(parent)
        # load the UI 
        uic.loadUi('LoggerPlotter.ui', self)
        # connect the signals with the slots
        self.pushButton_2.clicked.connect(self.selectLogFile)
        self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
        self.tableWidget_3.itemSelectionChanged.connect(self.tableSelectionChanged)
        self.comboBox_1.currentIndexChanged.connect(self.logLevelIndexChanged)
        # menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionOpen.triggered.connect(self.selectLogFile)
        self.actionPlot.triggered.connect(self.showPlotPane)
        self.actionLog.triggered.connect(self.showLogPane)
        self.actionParameters.triggered.connect(self.showParametersPane)
        self.actionAbout.triggered.connect(self.showAbout)
        # additional configuration
        # disable text wrapping in log window
        self.plainTextEdit.setLineWrapMode(0)

        # class member variables definition
        self.logFileName = ''
        self.fleNames = []
        self.nx = 0
        self.data = None
        self.scanVoltage = None
        self.paramsAuto = None
        self.paramsManual = {}
        
        # configure logging
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        #self.log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
        self.console_handler = logging.StreamHandler()
        #self.console_handler.setLevel(logging.WARNING)
        self.console_handler.setFormatter(self.log_formatter)
        self.logger.addHandler(self.console_handler)
        #self.file_handler = logging.FileHandler(logFile)
        #self.file_handler.setFormatter(self.log_formatter)
        #self.logger.addHandler(self.file_handler)
        self.text_edit_handler = TextEditHandler(self.plainTextEdit)
        self.text_edit_handler.setFormatter(self.log_formatter)
        self.logger.addHandler(self.text_edit_handler)
        
        # welcome message
        self.logger.info(progName + progVersion + ' started')
        
        # restore global settings from default location
        self.restoreSettings()
        
        # additional decorations
        #self.tableWidget_3.horizontalHeader().
        
        # read data files
        self.parseFolder()
        
        # connect mouse button press event
        #self.cid = self.mplWidget.canvas.mpl_connect('button_press_event', self.onclick)
        #self.mplWidget.canvas.mpl_disconnect(cid)

    def showAbout(self):
        QMessageBox.information(self, 'About', progName + ' Version ' + progVersion + 
                                '\nPlot Logger traces.', QMessageBox.Ok)    

    def showPlotPane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(False)
    
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
        if self.logFileName is None:
            d = "./"
        else:
            d = os.path.dirname(self.logFileName)
        fileOpenDialog = QFileDialog(caption='Select log file', directory = d)
        # select fn, not file
        fn = fileOpenDialog.getOpenFileName()[0]
        # if a fn is selected
        if fn:
            if self.logFileName == fn:
                return
            i = self.comboBox_2.findText(fn)
            if i >= 0:
                self.comboBox_2.setCurrentIndex(i)
            else:
                # add item to history  
                self.comboBox_2.insertItem(-1, fn)
                self.comboBox_2.setCurrentIndex(0)
    
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
            # read zip file dir
            self.dataFile = DataFile(zipFileName, folder = folder)
            # read signals from zip file
            self.signalsList = self.dataFile.readAllSignals()
            # clean all signal plots
            layout = self.scrollAreaWidgetContents_3.layout()
            for k in range(layout.count()):
                layout.itemAt(k).widget().canvas.ax.clear()
                layout.itemAt(k).widget().canvas.draw()
            # reorder according to columns order in the table
            self.signals = []
            for c in self.columns:
                for s in self.signalsList:
                    if s.name == c :
                        self.signals.append(self.signalsList.index(s))
            # plot signals to existing plots or add new
            jj = 0
            col = 0
            row = 0
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
                    # add plots in colCount columns
                    layout.addWidget(mplw, row, col)
                    colCount = 3
                    col += 1
                    if col >= colCount:
                        col = 0
                        row += 1
                axes = mplw.canvas.ax
                axes.clear()
                axes.plot(s.x, s.y)
                # decorate the plot
                axes.grid(True)
                axes.set_title(s.name + ' = ' + str(s.value) + ' ' + s.unit)
                axes.set_xlabel('Time, ms')
                axes.set_ylabel(s.name + ', ' + s.unit)
                #axes.legend(loc='best') 
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
 
    def selectionChanged(self, i):
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
        levels = [logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
        self.logger.debug('Log selection changed to %s'%str(m))
        self.logger.setLevel(levels[m])
 
    def onQuit(self) :
        # save global settings
        self.saveSettings()

    def parseFolder(self, fn=None):
        try:
            if fn is None:
                fn = self.logFileName
            if fn is None:
                return
            self.logger.log(logging.DEBUG, 'Reading log file %s'%fn)
            # read log file content to logTable
            self.logTable = LogTable(fn)
            if self.logTable.fileName is None:
                return
            self.logFileName = self.logTable.fileName
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
            # clean table widget
            self.tableWidget_3.itemSelectionChanged.disconnect(self.tableSelectionChanged)
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
            # select last row of widget -> selectionChanged will be fired 
            self.tableWidget_3.itemSelectionChanged.connect(self.tableSelectionChanged)
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount()-1)
            ##self.tableWidget_3.scrollToBottom()
            return
        except :
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.printExceptionInfo()
            return
    
    def zoplot(self, value=0.0, color='k'):
        axes = self.mplWidget.canvas.ax
        xlim = axes.get_xlim()
        axes.plot(xlim, [value, value], color=color)
        axes.set_xlim(xlim)

    def voplot(self, value=0.0, color='k'):
        axes = self.mplWidget.canvas.ax
        ylim = axes.get_ylim()
        axes.plot([value, value], ylim, color=color)
        axes.set_ylim(ylim)

    def saveSettings(self, folder='', fileName=settingsFile) :
        try:
            fullName = os.path.join(str(folder), fileName)
            # save window size and position
            p = self.pos()
            s = self.size()
            self.conf['main_window'] = {'size':(s.width(), s.height()), 'position':(p.x(), p.y())}
            #
            self.conf['folder'] = self.logFileName
            #self.conf['smooth'] = int(self.spinBox.value())
            #self.conf['scan'] = int(self.spinBox_2.value())
            #self.conf['result'] = int(self.comboBox.currentIndex())
            self.conf['history'] = [str(self.comboBox_2.itemText(count)) for count in range(min(self.comboBox_2.count(), 10))]
            self.conf['history_index'] = self.comboBox_2.currentIndex()
            self.conf['log_level'] = logging.DEBUG
            self.conf['parameters'] = self.paramsManual
            with open(fullName, 'w', encoding='utf-8') as configfile:
                configfile.write(json.dumps(self.conf, indent=4))
            self.logger.info('Configuration saved to %s'%fullName)
            return True
        except :
            self.printExceptionInfo()
            self.logger.info('Configuration save error to %s'%fullName)
            return False
        
    def restoreSettings(self, folder='', fileName=settingsFile) :
        self.setDefaultSettings()
        try :
            fullName = os.path.join(str(folder), fileName)
            with open(fullName, 'r', encoding='utf-8') as configfile:
                s = configfile.read()
            self.conf = json.loads(s)
            # restore window size and position
            if 'main_window' in self.conf:
                self.resize(QSize(self.conf['main_window']['size'][0], self.conf['main_window']['size'][1]))
                self.move(QPoint(self.conf['main_window']['position'][0], self.conf['main_window']['position'][1]))
            # last folder
            if 'folder' in self.conf:
                self.logFileName = self.conf['folder']
            #if 'smooth' in self.conf:
                #self.spinBox.setValue(int(self.conf['smooth']))
            #if 'scan' in self.conf:
                #self.spinBox_2.setValue(int(self.conf['scan']))
            #if 'result' in self.conf:
                #self.comboBox.setCurrentIndex(int(self.conf['result']))
            # read items from history  
            if 'history' in self.conf:
                self.comboBox_2.currentIndexChanged.disconnect(self.selectionChanged)
                self.comboBox_2.clear()
                self.comboBox_2.addItems(self.conf['history'])
                self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
            if 'history_index' in self.conf:
                self.comboBox_2.setCurrentIndex(self.conf['history_index'])

            # print OK message and exit    
            self.logger.info('Configuration restored from %s'%fullName)
            return True
        except :
            # print error info    
            self.printExceptionInfo()
            self.logger.info('Configuration restore error from %s'%fullName)
            return False

    def setDefaultSettings(self) :
        try :
            # window size and position
            self.resize(QSize(640, 480))
            self.move(QPoint(0, 0))
            # log file name
            self.logFileName = None
            # smooth
            #self.spinBox.setValue(100)
            # scan
            #self.spinBox_2.setValue(0)
            # result
            #self.comboBox.setCurrentIndex(0)
            # items in history  
            #self.comboBox_2.currentIndexChanged.disconnect(self.tableSelectionChanged)
            #self.comboBox_2.clear()
            #self.comboBox_2.currentIndexChanged.connect(self.tableSelectionChanged)
            
            self.conf = {}
            
            # print OK message and exit    
            self.logger.log(logging.DEBUG, 'Default configuration set.')
            return True
        except :
            # print error info    
            self.printExceptionInfo(level=logging.DEBUG)
            self.logger.log(logging.WARNING, 'Default configuration set error.')
            return False

    def printExceptionInfo(self, level=logging.INFO):
        #excInfo = sys.exc_info()
        (tp, value) = sys.exc_info()[:2]
        self.logger.log(level, 'Exception %s %s'%(str(tp), str(value)))

class LogTable():
    def __init__(self, fileName, folder = ""):
        self.logger = logging.getLogger()
        self.data = [[],]
        self.headers = []
        self.fileName = None
        self.buf = None
        self.rows = 0
        self.columns = 0
        
        fn = os.path.join(folder, fileName)
        if not os.path.exists(fn) :
            return  
        with open(fn, "r") as stream:
            self.buf = stream.read()
        if len(self.buf) <= 0 :
            self.logger.info('Nothing to process in %s'%self.fileName)
            return
        self.fileName = fn
        # split buf to lines
        lns = self.buf.split('\n')
        # loop for lines
        for ln in lns:
            # split line to fields
            flds =ln.split("; ")
            if len(flds[0]) < 19:
                continue
            # first field is date time
            time = flds[0].split(" ")[1].strip()
            # add row to table
            self.addColumn("Time")
            self.addRow()
            j = self.headers.index("Time")
            self.data[j][self.rows-1] = time
            
            for fld in flds[1:]:
                kv = fld.split("=")
                key = kv[0].strip()
                val = kv[1].strip()
                if key in self.headers:
                    j = self.headers.index(key)
                    self.data[j][self.rows-1] = val
                else:
                    self.addColumn(key)
                    self.data[self.columns-1][self.rows-1] = val
        
    def addRow(self):
        for item in self.data :
            item.append("")
        self.rows += 1
    
    def removeRow(self, row):
        for item in self.data :
            del item[row]
        self.rows -= 1

    def removeColumn(self, col):
        if isinstance(col, str):
            if col not in self.headers:
                return
            col = self.headers.index(col)
        del self.data[col]
        del self.headers[col]
        self.columns -= 1

    def item(self, row, col):
        if isinstance(col, str):
            if col not in self.headers:
                return None
            col = self.headers.index(col)
        return self.data[col][row]

    def getItem(self, row, col):
        return self.item(self, row, col)

    def setItem(self, row, col, val):
        if isinstance(col, str):
            if col not in self.headers:
                return False
            col = self.headers.index(col)
        self.data[col][row] = val
        return True

    def column(self, col):
        if isinstance(col, str):
            if col not in self.headers:
                return None
            col = self.headers.index(col)
        return self.data[col]

    def row(self, row):
        return [self.data[n][row] for n in range(len(self.headers))]

    def addColumn(self, columnName):
        if columnName is None:
            return -1
        # skip if column exists
        if columnName in self.headers:
            return self.headers.index(columnName)
        self.headers.append(columnName)
        newColumn = ["" for ii in range(self.columns)]
        self.data.append(newColumn)
        self.columns += 1 
        return self.headers.index(columnName)
        
    def find(self, columnName):
        try:
            return self.headers.index(columnName)
        except:
            return -1

    def __contains__(self, item):
        return item in self.headers

    def __len__(self):
        return len(self.headers)

    def __getitem__(self, item):
        return self.data[self.headers.index(item)]
    
class Signal():
    
    def __init__(self):
        self.logger = logging.getLogger()
        self.x = np.zeros(1)
        self.y = self.x.copy()
        self.params = {}
        self.name = ''
        self.unit = ''
        self.scale = 1.0
        self.value = 0.0
        self.marks = {}
        
class DataFile():
    def __init__(self, fileName, folder=""):
        self.logger = logging.getLogger()
        self.fileName = None
        self.files = []
        self.signals = []
        fn = os.path.join(folder, fileName)
        with zipfile.ZipFile(fn, 'r') as zipobj:
            self.files = zipobj.namelist()
        
        self.fileName = fn
        for f in self.files:
            if f.find("chan") >= 0 and f.find("param") < 0:
                self.signals.append(f)
        
    def readSignal(self, signalName):
        signal = Signal()
        if signalName not in self.signals:
            self.logger.log(logging.INFO, "No signal %s in the file"%signalName)
            return signal
        with zipfile.ZipFile(self.fileName, 'r') as zipobj:
            buf = zipobj.read(signalName)
            pf = signalName.replace('chan', 'paramchan')
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
            if len(kv) == 2:
                signal.params[kv[0].strip()] = kv[1].strip()
        # scale to units
        if b'display_unit' in signal.params:
            signal.scale = float(signal.params[b'display_unit'])
            signal.y *= signal.scale
        # name of the signal
        if b"label" in signal.params:
            signal.name = signal.params[b"label"].decode('ascii')
        else:
            signal.name = signalName
        # find marks
        for k in signal.params:
            if k.endswith(b"_start"):
                ms = int(signal.params[k])
                ml = int(signal.params[k.replace(b"_start", b'_length')])
                if ms+ml < n:
                    mv = signal.y[ms:ms+ml].mean()
                else:
                    mv = 0.0
                signal.marks[k.replace(b"_start", b'').decode('ascii')] = (ms, ml, mv)
        if b'zero' in signal.marks:
            zero = signal.marks["zero"][2]
        else:
            zero = 0.0
        if b'unit' in signal.params:
            signal.unit = signal.params[b'unit'].decode('ascii')
        else:
            signal.unit = ''
        signal.value = signal.marks["mark"][2] - zero  
        return signal

    def readAllSignals(self):
        signalsList = []
        for s in self.signals:
            signalsList.append(self.readSignal(s))
        return signalsList    
                        
if __name__ == '__main__':
    # create the GUI application
    app = QApplication(sys.argv)
    # instantiate the main window
    dmw = MainWindow()
    app.aboutToQuit.connect(dmw.onQuit)
    # show it
    dmw.show()
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())