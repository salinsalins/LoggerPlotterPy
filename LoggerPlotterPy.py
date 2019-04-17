# coding: utf-8
'''
Created on Jul 2, 2017

@author: sanin
''' 
# used to parse files more easily
from __future__ import with_statement
from __future__ import print_function
from configparser import ConfigParser

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
from smooth import smooth

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
        # load the GUI 
        uic.loadUi('LoggerPlotter.ui', self)
        # connect the signals with the slots
        self.pushButton_2.clicked.connect(self.selectLogFile)
        #self.pushButton_4.clicked.connect(self.processFolder)
        #self.pushButton_6.clicked.connect(self.pushPlotButton)
        #self.pushButton_7.clicked.connect(self.erasePicture)
        self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
        self.tableWidget_3.itemSelectionChanged.connect(self.tableSelectionChanged)
        self.comboBox_1.currentIndexChanged.connect(self.logLevelIndexChanged)
        # menu actions connection
        self.actionOpen.triggered.connect(self.selectLogFile)
        self.actionQuit.triggered.connect(qApp.quit)
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
        self.logger = logging.getLogger(progName+progVersion)
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
        fileOpenDialog = QFileDialog(caption='Select log file', directory=d)
        # select lfn, not file
        lfn = fileOpenDialog.getOpenFileName()[0]
        # if a lfn is selected
        if lfn:
            if self.logFileName == lfn:
                return
            i = self.comboBox_2.findText(lfn)
            if i >= 0:
                self.comboBox_2.setCurrentIndex(i)
            else:
                # add item to history  
                self.comboBox_2.insertItem(-1, lfn)
                self.comboBox_2.setCurrentIndex(0)
    
    def tableSelectionChanged(self):
        row = self.tableWidget_3.selectedRanges()[0].topRow()
        self.logger.log(logging.DEBUG, 'Selection changed to row %s'%str(row))
        if row < 0:
            return
        zipFileName = self.table["File"][row]
        self.logger.log(logging.DEBUG, 'ZipFile %s'%zipFileName)
        folder = os.path.dirname(self.logFileName)
        self.logger.log(logging.DEBUG, 'Folder %s'%folder)
        
        self.dataFile = ""
        self.dataFile = DataFile(zipFileName, folder = folder)
        self.signalsList = []
        self.signalsList = self.dataFile.readAllSignals()
        layout = self.scrollAreaWidgetContents_3.layout()
        jj = 0
        col = 0
        row = 0
        for s in self.signalsList:
            if jj < layout.count() :    
                mplw = layout.itemAt(jj).widget()
            else:
                mplw = MplWidget()
                mplw.setMinimumHeight(320)
                mplw.setMinimumWidth(320)
                layout.addWidget(mplw, row, col)
                col += 1
                if col > 1:
                    col = 0
                    row += 1
                axes = mplw.canvas.ax
                axes.clear()
                axes.plot(s.x, s.y, label='plot '+str(jj))
                # decorate the plot
                axes.grid(True)
                axes.set_title(s.title)
                axes.set_xlabel('Time, s')
                axes.set_ylabel('Signal, V')
                axes.legend(loc='best') 
                mplw.canvas.draw()
                jj += 1
        return        
 
    def selectionChanged(self, i):
        self.logger.debug('Selection changed to %s'%str(i))
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

    def logLevelIndexChanged(self, i):
        levels = [logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
        self.logger.debug('Log selection changed to %s'%str(i))
        i = int(self.comboBox_1.currentIndex())
        #self.logger.setLevel(levels[i])

 
    def onQuit(self) :
        # save global settings
        self.saveSettings()

    def parseFolder(self, fn=None):
        if fn is None:
            fn = self.logFileName
        if fn is None:
            return
        self.logger.log(logging.DEBUG, 'Reading log file %s'%fn)
        # read log file content
        
        #self.logTable = LogTable(fn)
        #self.tableWidget_3.clear()
        #for col in self.logTable:
        #    self.tableWidget_3.insertRow(i)
        #    self.tableWidget_3.insertColumn(j)
        #    self.tableWidget_3.setHorizontalHeaderItem (j, QTableWidgetItem(key))
        
        try:
            stream = open(fn, "r")
            self.buf = stream.read()
            stream.close()
            if len(self.buf) <= 0 :
                self.logger.info('Nothing to process in %s'%fn)
                return
            self.logFileName = fn
            
            self.table = {}
            # split buf to lines
            lns = self.buf.split('\n')
            # loop for lines
            i = 0
            for ln in lns:
                j = 0
                # split line to fields
                flds =ln.split("; ")
                if len(flds[0]) < 19:
                    continue
                # first field is date time
                time = flds[0].split(" ")[1].strip()
                # add row to table
                self.tableWidget_3.insertRow(i)
                if "Time" not in self.table:
                    self.table["Time"] = ['' for j in range(i)]
                    self.tableWidget_3.insertColumn(j)
                    self.tableWidget_3.setHorizontalHeaderItem (j, QTableWidgetItem("Time"))
                self.table["Time"].append(time)
                self.tableWidget_3.setItem(i, j, QTableWidgetItem(time))
                j += 1
                #print("Time = -", time, "-")
                for fld in flds[1:]:
                    #print(fld)
                    kv = fld.split("=")
                    key = kv[0].strip()
                    val = kv[1].strip()
                    #print(kv)
                    if key not in self.table:
                        self.table[key] = ['' for j in range(i)]
                        j = self.tableWidget_3.columnCount()
                        self.tableWidget_3.insertColumn(j)
                        self.tableWidget_3.setHorizontalHeaderItem (j, QTableWidgetItem(key))
                    else:
                        j = list(self.table.keys()).index(key)
                        
                    self.tableWidget_3.setItem(i, j, QTableWidgetItem(val))
                    self.table[key].append(val)
                for t in self.table :
                    if len(self.table[t]) < len(self.table["Time"]) :
                        self.table[t].append("")
                i += 1
            self.tableWidget_3.selectRow(self.tableWidget_3.rowCount()-1)
            self.tableWidget_3.scrollToBottom()
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
    def __init__(self, fileName, folder = "", wdgt=None):
        self.data = [[],]
        self.headers = []
        self.FileName = None
        self.wdgt = wdgt
        self.rows = 0
        self.columns = 0
        
        fn = os.path.join(folder, fileName)
        if not os.path.exists(fn) :
            return  
        with open(fn, "r") as stream:
            self.buf = stream.read()
        if len(self.buf) <= 0 :
            self.logger.info('Nothing to process in %s'%self.FileName)
            return
        self.FileName = fn
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
    
    def addColumn(self, columnName):
        if columnName is None:
            return
        # skip if column exists
        if columnName is self.headers:
            return
        self.headers.append(columnName)
        newColumn = ["" for ii in range(self.columns)]
        self.data.append(newColumn)
        self.columns += 1 
        
    def find(self, columnName):
        return self.headers.index(columnName)

    def __contains__(self, item):
        return item in self.headers

    def __len__(self):
        return len(self.headers)
    
class Signal():
    
    def __init__(self):
        self.x = np.zeros(1)
        self.y = self.x.copy()
        self.title = ''
        self.params = {}
        
    def read(self, fileName, signalName, folder=''):
        if signalName.find("chan") < 0 or signalName.find("param") >= 0:
            self.logger.log(logging.INFO, "Wrong Signal Name %s"%signalName)
            return
        fn = os.path.join(folder, fileName)
        #self.logger.log(logging.DEBUG, 'File %s'%fn)
        with zipfile.ZipFile(os.path.join(folder, fn), 'r') as zipobj:
            files = zipobj.namelist()
            if signalName not in files :
                self.logger.log(logging.INFO, "No such signal")
                return
            buf = zipobj.read(signalName)
            lines = buf.split(b"\r\n")
            n = len(lines)
            self.x = np.empty(n)
            self.y = np.empty(n)
            ii = 0
            for ln in lines:
                xy = ln.split(b'; ')
                self.x[ii] = float(xy[0].replace(b',', b'.'))
                self.y[ii] = float(xy[1].replace(b',', b'.'))
                ii += 1
            # read parameters        
            self.params = {}
            pf = signalName.replace('chan', 'paramchan')
            buf = zipobj.read(pf)
            lines = buf.split(b"\r\n")
            for ln in lines:
                kv = ln.split(b'=')
                if len(kv) == 2:
                    self.params[kv[0].strip()] = kv[1].strip()
            # title of the signal
            self.title = ""
            self.title = self.params[b"label"].decode('ascii')
            # find marks
            self.marks = []
            ms = int(self.params['mark_start'])
            ml = int(self.params['mark_length'])
            self.mark.append((ms, ml))
            for k in self.params:
                if k.start("mark"):
                    print(k)

class DataFile():
    def __init__(self, fileName, folder=""):
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
        # title of the signal
        signal.title = ""
        signal.title = signal.params[b"label"].decode('ascii')
        # find marks
        signal.marks = {}
        for k in signal.params:
            if k.endswith(b"_start"):
                ms = int(signal.params[k])
                ml = int(signal.params[k.replace(b"_start", b'_length')])
                if ms+ml < n:
                    mv = signal.y[ms:ms+ml].mean()
                else:
                    mv = 0.0
                signal.marks[k.replace(b"_start", b'').decode('ascii')] = (ms, ml, mv)
        signal.value = 0.0
        if b'zero' in signal.marks:
            zero = signal.marks["zero"][2]
        else:
            zero = 0.0
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