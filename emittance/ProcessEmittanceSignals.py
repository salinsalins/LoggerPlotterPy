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

import numpy as np
from astropy import table

# PyQt4-5 universal imports
try:            
    from PyQt4.QtGui import QMainWindow      # @UnresolvedImport @UnusedImport
    from PyQt4.QtGui import QApplication     # @UnresolvedImport @UnusedImport
    from PyQt4.QtGui import qApp             # @UnresolvedImport @UnusedImport
    from PyQt4.QtGui import QFileDialog      # @UnresolvedImport @UnusedImport
    from PyQt4.QtGui import QTableWidgetItem # @UnresolvedImport @UnusedImport
    from PyQt4.QtGui import QMessageBox      # @UnresolvedImport @UnusedImport
    from PyQt4 import uic                    # @UnresolvedImport @UnusedImport
    from PyQt4.QtCore import QPoint, QSize   # @UnresolvedImport @UnusedImport
except:
    from PyQt5.QtWidgets import QMainWindow     # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5.QtWidgets import QApplication    # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5.QtWidgets import qApp            # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5.QtWidgets import QFileDialog     # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5.QtWidgets import QTableWidgetItem # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5.QtWidgets import QMessageBox     # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5 import uic                       # @UnresolvedImport @UnusedImport @Reimport
    from PyQt5.QtCore import QPoint, QSize      # @UnresolvedImport @UnusedImport @Reimport

from smooth import smooth

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
        uic.loadUi('.\emittance\Emittance1.ui', self)
        # connect the signals with the slots
        self.pushButton_2.clicked.connect(self.selectLogFile)
        #self.pushButton_4.clicked.connect(self.processFolder)
        self.pushButton_6.clicked.connect(self.pushPlotButton)
        self.pushButton_7.clicked.connect(self.erasePicture)
        self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
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
    
    def selectionChanged(self, i):
        self.logger.log(logging.DEBUG, 'Selection changed to %s'%str(i))
        if i < 0:
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
        self.logger.log(logging.INFO, 'Reading %s'%fn)
        # read log file content
        try:
            stream = open(fn, "r")
            self.buf = stream.read()
            stream.close()
            if len(self.buf) <= 0 :
                self.logger.info('Nothing to process in %s'%fn)
                return
            self.logFileName = fn
            
            table = {}
            # split to lines
            lns = self.buf.split('\n')
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
                if "Time" not in table:
                    table["Time"] = ['' for j in range(i)]
                    self.tableWidget_2.insertColumn(j)
                    self.tableWidget_2.setHorizontalHeaderItem (j, QTableWidgetItem("Time"))
                table["Time"].append(time)
                self.tableWidget_2.setItem(i, j, QTableWidgetItem(time))
                j += 1
                #print("Time = -", time, "-")
                for fld in flds[1:]:
                    #print(fld)
                    kv = fld.split("=")
                    print(kv)
                    if kv[0] not in table:
                        table[kv[0]] = ['' for j in range(i)]
                        j = self.tableWidget_2.columnCount()
                        self.tableWidget_2.insertColumn(j)
                        self.tableWidget_2.setHorizontalHeaderItem (j, QTableWidgetItem(kv[0]))
                    else:
                        j = list(table.keys()).index(kv[0])
                        
                    self.tableWidget_2.setItem(i, j, QTableWidgetItem(kv[1]))
                    table[kv[0]].append(kv[1])
                for t in table :
                    if len(table[t]) < len(table["Time"]) :
                        table[t].append("")
                i += 1
    
            folder = os.path.dirname(self.logFileName)
            self.logger.info('Parsing %s'%folder)
            self.dirlist = os.listdir(folder)
            # fill listWidget with file zipFiles
            self.listWidget.clear()
            # make zip file zipFiles list
            self.zipFiles = [f for f in self.dirlist if f.endswith(".zip")]
            nx = len(self.zipFiles)
            self.listWidget.addItems(self.zipFiles)
        except :
            self.logger.log(logging.WARNING, 'Exception in parseFolder')
            self.printExceptionInfo()
            return

    def addColumn(self, col, val):
        x = self.columns.find(col)
        if col in self.columns:
            self.tableWidget_2.setItem(x, y, QTableWidgetItem(val))
        else:
            self.columns.add(col)
            self.tableWidget_2.insertColumn()
    
    def readSignal(self, row):
        if self.data is None :
            return (None, None, None)
        #self.logger.info('Processing %d'%row)
        # scan voltage
        u = self.data[0, :].copy()
        # smooth
        ns = self.readParameter(0, "smooth", 100, int)
        smooth(u, 2*ns)
        # signal
        y = self.data[row, :].copy()
        # smooth
        ns = self.readParameter(row, "smooth", 1, int)
        # offset
        of = self.readParameter(row, "offset", 0.0, float)
        # zero line
        z = self.readZero(row)
        # smooth
        smooth(y, ns)
        smooth(z, 2*ns)
        # subtract offset and zero
        y = y - z - of
        # load resistor
        R = self.readParameter(0, "R", 2.0e5, float)
        # convert signal to Amperes
        y = y/R
        # signal region
        r0 = self.readParameter(0, "range", (0, len(y)))
        r = self.readParameter(row, "range", r0)
        index = np.arange(r[0],r[1])
        # scale
        s = self.readParameter(row, "scale", 1.7, float)
        # ndh
        ndh = self.readParameter(row, "ndh", 0.0, float)
        # scanner base
        l2 = self.readParameter(0, "l2", 195.0, float)
        # x' in Radians
        xsub = (ndh - s*u) / l2
        return (xsub, y, index)
    
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
        self.execInitScript()
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