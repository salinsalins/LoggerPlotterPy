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
import re

import numpy as np
from astropy import table

from PyQt5.QtWidgets import QMainWindow     # @UnresolvedImport @UnusedImport @Reimport
from PyQt5.QtWidgets import QApplication    # @UnresolvedImport @UnusedImport @Reimport
from PyQt5.QtWidgets import qApp            # @UnresolvedImport @UnusedImport @Reimport
from PyQt5.QtWidgets import QFileDialog     # @UnresolvedImport @UnusedImport @Reimport
from PyQt5.QtWidgets import QTableWidgetItem # @UnresolvedImport @UnusedImport @Reimport
from PyQt5.QtWidgets import QTableWidget     # @UnresolvedImport @UnusedImport
from PyQt5.QtWidgets import QMessageBox     # @UnresolvedImport @UnusedImport @Reimport
from PyQt5 import uic                       # @UnresolvedImport @UnusedImport @Reimport
from PyQt5.QtCore import QPoint, QSize      # @UnresolvedImport @UnusedImport @Reimport

from smooth import smooth
from mplwidget import MplWidget

progName = 'LoggerPlotterPy'
progVersion = '_1_0'
settingsFile = progName + '.json'
initScript =  progName + '_init.py'
logFile =  progName + '.log'
dataFile = progName + '.dat'

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
        self.pushButton_6.clicked.connect(self.pushPlotButton)
        self.pushButton_7.clicked.connect(self.erasePicture)
        #self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
        self.tableWidget_2.itemSelectionChanged.connect(self.selectionChanged)
        # menu actions connection
        self.actionOpen.triggered.connect(self.selectLogFile)
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionPlot.triggered.connect(self.showPlot)
        self.actionLog.triggered.connect(self.showLog)
        self.actionParameters.triggered.connect(self.showParameters)
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
        self.log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
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
        #self.tableWidget_2.horizontalHeader().
        
        # read data files
        self.parseFolder()
        
        # connect mouse button press event
        #self.cid = self.mplWidget.canvas.mpl_connect('button_press_event', self.onclick)
        #self.mplWidget.canvas.mpl_disconnect(cid)

    def showAbout(self):
        QMessageBox.information(self, 'About', progName + ' Version ' + progVersion + 
                                '\nPlot Logger traces.', QMessageBox.Ok)    

    def showPlot(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(False)
    
    def showLog(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(True)
        self.actionParameters.setChecked(False)

    def showParameters(self):
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
    
    def selectionChanged(self):
        i = self.tableWidget_2.selectedRanges()[0].topRow()
        self.logger.log(logging.DEBUG, 'Selection changed to row %s'%str(i))
        if i < 0:
            return
        zipFileName = self.table["File"][i]
        self.logger.log(logging.DEBUG, 'ZipFile %s'%zipFileName)
        folder = os.path.dirname(self.logFileName)
        self.logger.log(logging.DEBUG, 'Folder %s'%folder)
        with zipfile.ZipFile(os.path.join(folder, zipFileName), 'r') as zipobj:
            files = zipobj.namelist()
            layout = self.scrollAreaWidgetContents.layout()
            jj = 0
            col = 0
            row = 0
            for f in files :
                if f.find("chan") >= 0 and f.find("param") < 0:
                    self.logger.log(logging.DEBUG, "Signal %s"%f)
                    buf = zipobj.read(f)
                    lines = buf.split(b"\r\n")
                    n = len(lines)
                    x = np.empty(n)
                    y = np.empty(n)
                    ii = 0
                    for ln in lines:
                        xy = ln.split(b'; ')
                        x[ii] = float(xy[0].replace(b',', b'.'))
                        y[ii] = float(xy[1].replace(b',', b'.'))
                        ii += 1
                    
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
                    axes.plot(x, y, label='plot '+str(jj))

                    pf = f.replace('chan', 'paramchan')
                    buf = zipobj.read(pf)
                    lines = buf.split(b"\r\n")
                    keys = []
                    vals = []
                    for ln in lines:
                        kv = ln.split(b'=')
                        if len(kv) == 2:
                            keys.append(kv[0].strip())
                            vals.append(kv[1].strip())
                    title = f
                    if b"label" in keys:
                        i = keys.index(b"label")
                        title = vals[i].decode('ascii')
                        
                    # decorate the plot
                    axes.grid(True)
                    axes.set_title(title)
                    axes.set_xlabel('Time, s')
                    axes.set_ylabel('Signal, V')
                    axes.legend(loc='best') 
                    mplw.canvas.draw()

                    jj += 1

                    #print(x[0])
                    pass
                       
        
        return        
        newFileName = str(self.comboBox_2.currentText())
        self.logger.log(logging.DEBUG, 'Selected %s'%newFileName)
        if not os.path.isfile(newFileName):
            self.logger.warning('%s is not a file'%newFileName)
            self.comboBox_2.removeItem(i)
            return
        if self.logFileName != newFileName:
            self.clearPicture()
            self.logFileName = newFileName
            self.parseFolder()
 
    def onQuit(self) :
        # save global settings
        self.saveSettings()

    def clearPicture(self, force=False):
        if force or self.checkBox.isChecked():
            # clear the axes
            self.erasePicture()
        
    def erasePicture(self):
        self.mplWidget.canvas.ax.clear()
        self.mplWidget.canvas.draw()

    def parseFolder(self, fn=None):
        if fn is None:
            fn = self.logFileName
        if fn is None:
            return
        self.logger.log(logging.DEBUG, 'Reading %s'%fn)
        # read log file content
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
                self.tableWidget_2.insertRow(i)
                if "Time" not in self.table:
                    self.table["Time"] = ['' for j in range(i)]
                    self.tableWidget_2.insertColumn(j)
                    self.tableWidget_2.setHorizontalHeaderItem (j, QTableWidgetItem("Time"))
                self.table["Time"].append(time)
                self.tableWidget_2.setItem(i, j, QTableWidgetItem(time))
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
                        j = self.tableWidget_2.columnCount()
                        self.tableWidget_2.insertColumn(j)
                        self.tableWidget_2.setHorizontalHeaderItem (j, QTableWidgetItem(key))
                    else:
                        j = list(self.table.keys()).index(key)
                        
                    self.tableWidget_2.setItem(i, j, QTableWidgetItem(val))
                    self.table[key].append(val)
                for t in self.table :
                    if len(self.table[t]) < len(self.table["Time"]) :
                        self.table[t].append("")
                i += 1
            self.tableWidget_2.selectRow(self.tableWidget_2.rowCount()-1)
            self.tableWidget_2.scrollToBottom()
            #self.scrollArea_2.scrollToBottom()
    
            folder = os.path.dirname(self.logFileName)
            self.logger.info('Parsing %s'%folder)
            self.dirlist = os.listdir(folder)
            # fill listWidget with file zipFiles
            self.listWidget.clear()
            # make zip file zipFiles list
            self.zipFiles = [f for f in self.dirlist if f.endswith(".zip")]
            self.listWidget.addItems(self.zipFiles)
        except :
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.printExceptionInfo()
            return
    
    def plot(self, *args, **kwargs):
        axes = self.mplWidget.canvas.ax
        axes.plot(*args, **kwargs)
        #zoplot()
        #xlim = axes.get_xlim()
        #axes.plot(xlim, [0.0,0.0], color='k')
        #axes.set_xlim(xlim)
        axes.grid(True)
        axes.legend(loc='best') 
        self.mplWidget.canvas.draw()

    def draw(self):
        self.mplWidget.canvas.draw()

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

    def cls(self):
        self.clearPicture()

    def plotRawSignals(self):
        self.clearPicture()
        if self.data is None :
            return
        indexes = self.listWidget.selectedIndexes()
        if len(indexes) <= 0:
            return
        axes = self.mplWidget.canvas.ax
        x,xTitle = self.getX()
        for i in indexes :
            row = i.row()
            y = self.data[row, :].copy()
            ns = self.readParameter(row, "smooth", self.spinBox.value(), int)
            smooth(y, ns)
            z = self.readZero(row) + self.readParameter(row, 'offset')
            axes.plot(x, y, label='raw '+str(row))
            axes.plot(x, z, label='zero'+str(row))
        self.zoplot()
        axes.grid(True)
        axes.set_title('Signals with zero line')
        axes.set_xlabel(xTitle)
        axes.set_ylabel('Signal Voltage, V')
        axes.legend(loc='best') 
        self.mplWidget.canvas.draw()

    def onclick(self, event):
        self.logger.info('button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              (event.button, event.x, event.y, event.xdata, event.ydata))

    def plotElementaryJets(self, file=None, entry=None):
        axes = self.mplWidget.canvas.ax
        self.clearPicture()
        # draw chart
        indexes = self.listWidget.selectedIndexes()
        for i in indexes :
            row = i.row()
            x,y,index = self.readSignal(row)
            xx = x[index]*1000.0 # convert to milliRadians
            yy = -1.0e6*y[index] # convert to microAmpers
            axes.plot(xx, yy, label='jet '+str(row))
        axes.plot(axes.get_xlim(), [0.0,0.0], color='k')
        # decorate the plot
        axes.grid(True)
        axes.set_title('Elementary jet profile')
        axes.set_xlabel('X\', milliRadians')
        axes.set_ylabel('Signal, mkA')
        axes.legend(loc='best') 
        self.mplWidget.canvas.draw()

    def pushPlotButton(self):
        if self.data is None :
            return
        nx = len(self.fileNames) 
        if nx <= 0 :
            return
        
        if int(self.comboBox.currentIndex()) == 0:
            self.plotRawSignals()
            return
        if int(self.comboBox.currentIndex()) == 1:
            self.plotProcessedSignals()
            return
        if int(self.comboBox.currentIndex()) == 2:
            self.plotElementaryJets()
            return
        if int(self.comboBox.currentIndex()) == 3:
            self.calculateProfiles()
            return
        if int(self.comboBox.currentIndex()) == 4:
            self.calculateProfiles()
            return
        self.calculateEmittance()
    
    def saveSettings(self, folder='', fileName=settingsFile) :
        try:
            fullName = os.path.join(str(folder), fileName)
            # save window size and position
            p = self.pos()
            s = self.size()
            self.conf['main_window'] = {'size':(s.width(), s.height()), 'position':(p.x(), p.y())}
            #
            self.conf['folder'] = self.logFileName
            self.conf['smooth'] = int(self.spinBox.value())
            self.conf['scan'] = int(self.spinBox_2.value())
            self.conf['result'] = int(self.comboBox.currentIndex())
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
            #
            if 'folder' in self.conf:
                self.logFileName = self.conf['folder']
            if 'smooth' in self.conf:
                self.spinBox.setValue(int(self.conf['smooth']))
            if 'scan' in self.conf:
                self.spinBox_2.setValue(int(self.conf['scan']))
            if 'result' in self.conf:
                self.comboBox.setCurrentIndex(int(self.conf['result']))
            # read items from history  
            if 'history' in self.conf:
                self.comboBox_2.currentIndexChanged.disconnect(self.selectionChanged)
                self.comboBox_2.clear()
                self.comboBox_2.addItems(self.conf['history'])
                self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)

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
            self.spinBox.setValue(100)
            # scan
            self.spinBox_2.setValue(0)
            # result
            self.comboBox.setCurrentIndex(0)
            # items in history  
            self.comboBox_2.currentIndexChanged.disconnect(self.selectionChanged)
            self.comboBox_2.clear()
            self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
            
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
        (tp, value) = sys.exc_info()[:2]
        self.logger.log(level, 'Exception %s %s'%(str(tp), str(value)))

class LogTable():
    wdgt = None
    headers = []
    data = []
    
    def __init__(self, wdgt=None):
        self.data = []
        self.headers = []
        self.wdgt = wdgt
        
    def addRow(self):
        for item in self.data :
            item.append("")
    
    def addColumn(self, columnName=None):
        if columnName is None:
            return
        self.headers.append(columnName)
        newColumn = ["" for i in range(len(self.data[0]))]
        self.data.append(newColumn) 
        
    def findColumn(self, columnName):
        return self.headers.index(columnName)

class Signal():
    def __init__(self, n):
        self.x = np.empty(n, float)
        self.y = self.x.copy()
        
    def read(self, fileName, signalName, folder=''):
        if signalName.find("chan") < 0 or signalName.find("param") >= 0:
            self.logger.log(logging.INFO, "Wrong Signal Name %s"%signalName)
            return
        fn = os.path.join(folder, fileName)
        self.logger.log(logging.DEBUG, 'File %s'%fn)
        with zipfile.ZipFile(os.path.join(folder, fn), 'r') as zipobj:
            files = zipobj.namelist()
            if signalName not in files :
                self.logger.log(logging.INFO, "Signal %s not in file"%signalName)
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