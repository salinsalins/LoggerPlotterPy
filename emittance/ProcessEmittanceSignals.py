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
        fileOpenDialog = QFileDialog(caption='Select log file', directory=os.path.dirname(self.logFileName))
        # select lfn, not file
        lfn = fileOpenDialog.getOpenFileName()
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
        #self.logger.debug('Selection changed to %s'%str(i))
        if i < 0:
            return
        newFileName = str(self.comboBox_2.currentText())
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
        self.logger.info('Reading data from %s'%fn)
        # read log file content
        stream = open(self.LogFileName, "r")
        buf = stream.read()
        stream.close()
        # number of lines?
        nx = len(buf)
        if nx <= 0 :
            self.logger.info('Nothing to process in %s'%fn)
            return
        self.logger.info('%d lines in %s'%(nx, self.logFileName))
        self.logFileName = fn

        folder = os.path.dirname(self.logFileName)
        self.logger.info('Parsing %s'%folder)
        dirlist = os.listdir(folder)
        # fill listWidget with file names
        self.listWidget.clear()
        # make zip file names list
        names = [f for f in dirlist if f.endswith(".zip")]
        nx = len(names)
        #for i in range(nx):
        #    names[i] = '%3d - %s'%(i, names[i])
        # fill listWidget
        self.listWidget.addItems(names)
    
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

    def plotProcessedSignals(self):
        """Plots processed signals"""
        if self.data is None :
            self.logger.info('data is None')
            return
        self.execInitScript()
        # clear the Axes
        self.clearPicture()
        indexes = self.listWidget.selectedIndexes()
        if len(indexes) <= 0:
            self.logger.debug('Selection is empty')
            return
        axes = self.mplWidget.canvas.ax
        x,xTitle = self.getX()
        # draw chart
        for i in indexes :
            row = i.row()
            u,y,index = self.readSignal(row)
            # convert back from Amperes to Volts
            y = y * self.readParameter(0, "R", 2.0e5, float)
            # plot processed signal
            self.plot(x, y, label='proc '+str(row))
            # highlight signal region
            self.plot(x[index], y[index], label='range'+str(row))
            self.logger.info('Plot Processed Signal %d'%row)
            # print parameters
            self.readParameter(row, "smooth", 1, int, True)
            self.readParameter(row, "offset", 0.0, float, True)
            self.readParameter(row, "scale", 0.0, float, True)
            self.readParameter(row, "x0", 0.0, float, True)
            self.readParameter(row, "ndh", 0.0, float, True)
            # range vertical lines
            r = self.readParameter(row, "range", (0,-1), None, True)
            self.voplot(x[r[0]])
            self.voplot(x[r[1]-1])
        # plot zero line
        self.zoplot()
        axes.set_title('Processed Signals')
        axes.set_xlabel(xTitle)
        axes.set_ylabel('Voltage, V')
        axes.legend(loc='best') 
        # force an image redraw
        self.draw()

    def onclick(self, event):
        self.logger.info('button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              (event.button, event.x, event.y, event.xdata, event.ydata))

    def pickZeroLine(self):
        if self.data is None :
            return
        self.execInitScript()
        axes = self.mplWidget.canvas.ax
        self.clearPicture()
        indexes = self.listWidget.selectedIndexes()
        if len(indexes) <= 0:
            return
        # draw chart
        row = indexes[0].row()
        x,xTitle = self.getX()
        y = self.data[row, :].copy()
        ns = self.readParameter(row, "smooth", self.spinBox.value(), int)
        smooth(y, ns)
        z = self.readZero(row) + self.readParameter(row, 'offset')
        axes.plot(x, y, label='raw '+str(row))
        axes.plot(x, z, label='zero'+str(row))
        self.zoplot()
        axes.grid(True)
        axes.set_title('Signal %s with zero line'%str(row))
        axes.set_xlabel(xTitle)
        axes.set_ylabel('Signal Voltage, V')
        axes.legend(loc='best') 
        self.mplWidget.canvas.draw()
        # connect mouse button press event
        #self.cid = self.mplWidget.canvas.mpl_connect('button_press_event', self.onclick)
        #self.mplWidget.canvas.mpl_disconnect(cid)

    def plotElementaryJets(self):
        """Plot elementary jet profile"""
        if self.data is None :
            return
        self.execInitScript()
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
            #axes.plot(xx, gaussfit(xx, yy), '--', label='gauss '+str(row))
        # plot axis y=0
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
    
    def calculateProfiles(self):
        nx = len(self.fileNames) 
        if nx <= 0 :
            return
        
        self.execInitScript()
        
        # calculate common values
        x0 = np.zeros(nx-1)                         # [mm] X0 coordinates of scans
        flag = self.readParameter(0, 'autox0', False)
        #self.logger.info('', stamp=False)
        #self.logger.info('Emittance calculation using parameters:')
        #self.logger.info('Use calculated X0 = %s'%str(flag))
        for i in range(1, nx) :
            if flag:
                x0[i-1] = self.readParameter(i, 'x0', 0.0, float, select='auto')
            else:
                x0[i-1] = self.readParameter(i, 'x0', 0.0, float)
        # parameters
        # R
        R = self.readParameter(0, 'R', 2.0e5, float)    # [Ohm] Faraday cup load resistior
        # l1
        l1 = self.readParameter(0, 'l1', 213.0, float)  # [mm] distance from source to analyzer aperture
        # l2
        l2 = self.readParameter(0, 'l2', 195.0, float)  # [mm] analyzer base
        # d1 and hole area
        d1 = self.readParameter(0, 'd1', 0.4, float)    # [mm] analyzer hole diameter
        a1 = np.pi*d1*d1/4.0                            # [mm**2] analyzer hole area    
        # d2
        d2 = self.readParameter(0, 'd2', 0.5, float)    # [mm] analyzer slit width
        #self.logger.info('R=%fOhm l1=%fmm l2=%fmm d1=%fmm d2=%fmm'%(R,l1,l2,d1,d2))
        # calculate maximum and integral profiles
        self.profilemax = np.zeros(nx-1)
        self.profileint = np.zeros(nx-1)
        for i in range(1, nx) :
            try:
                x,y,index = self.readSignal(i)           # x - [Radians] y - [A]
                yy = y[index]
                xx = x[index]
                # select unique x values for spline interpolation
                xu, h = np.unique(xx, return_index=True)
                #self.logger.info(i,h)
                yu = yy[h] # [A]
                self.profilemax[i-1] = -1.0 * np.min(yu)      # [A]
                yu = yu / (d2/l2) # convert Y to density [A/Radian]
                # integrate by trapezoids method
                self.profileint[i-1] = -1.0 * trapz(yu, xu)  # [A]
                #self.logger.info(i, self.profileint[i-1])
            except:
                self.printExceptionInfo()
        # sort in x0 increasing order
        ix0 = np.argsort(x0)
        x0s = x0[ix0]
        #self.logger.info(x0s)
        self.profileint = self.profileint[ix0]
        #self.logger.info(self.profileint)
        self.profilemax = self.profilemax[ix0]
        #self.logger.info(self.profilemax)
        # remove average x
        xavg = trapz(x0s * self.profileint, x0s) / trapz(self.profileint, x0s)
        #self.logger.info('Average X %f mm'%xavg)
        x0s = x0s - xavg
        self.profileint = self.profileint / a1 # convert to local current density [A/mm^2]
        # cross-section current
        self.Ics = trapz(self.profileint, x0s)*d1 # [A] -  integrate over x and multiply to y width
        self.logger.info('Cross-section current %f mkA'%(self.Ics*1e6)) # from Amperes to mA
        # calculate total current
        index = np.where(x0s >= 0.0)[0]
        Ir = trapz(x0s[index]*self.profileint[index], x0s[index])*2.0*np.pi
        #self.logger.info('Total current right %f mA'%(Ir*1000.0)) # from Amperes to mA
        index = np.where(x0s <= 0.0)[0]
        Il = -1.0*trapz(x0s[index]*self.profileint[index], x0s[index])*2.0*np.pi
        #self.logger.info('Total current left %f mA'%(Il*1000.0)) # from Amperes to mA
        self.I = (Il + Ir)/2.0 #[A]
        self.logger.info('Total current %f mA'%(self.I*1000.0))  # from Amperes to mA
        # save profile data
        folder = self.logFileName
        fn = os.path.join(str(folder), 'InegralProfile.txt')
        np.savetxt(fn, np.array([x0,self.profileint]).T, delimiter='; ' )
        fn = os.path.join(str(folder), 'MaximumProfile.txt')
        np.savetxt(fn, np.array([x0,self.profilemax]).T, delimiter='; ' )
        # plot profiles
        axes = self.mplWidget.canvas.ax
        # plot integral profile
        if int(self.comboBox.currentIndex()) == 3:
            self.clearPicture()
            axes.set_title('Integral profile')
            axes.set_xlabel('X0, mm')
            axes.set_ylabel('Beamlet current, mkA')
            axes.plot(x0s, self.profileint*1.0e6, 'd-', label='Integral Profile')
            #axes.plot(x0s, gaussfit(x0s,profileint,x0s), '--', label='Gaussian fit')
            axes.grid(True)
            axes.legend(loc='best') 
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + ' Cross-section current %4.1f mkA'%(self.Ics*1e6),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()
            return
        # plot maximal profile
        if int(self.comboBox.currentIndex()) == 4:
            self.clearPicture()
            axes.set_title('Maximum profile')
            axes.set_xlabel('X0, mm')
            axes.set_ylabel('Maximal current, mkA')
            axes.plot(x0s, self.profilemax*1.0e6, 'o-', label='Maximum Profile')
            #axes.plot(x0s, gaussfit(x0s,profilemax,x0s), '--', label='Gaussian fit')
            axes.grid(True)
            axes.legend(loc='best') 
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + ' Cross-section current %4.1f mkA'%(self.Ics*1e6),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()

    # experimental interpolation function
    
    def interpolatePlot(self, x, y, F):
        # x,F -> x1,F1 sort data according rising x0
        nx = len(x)
        index = np.argsort(x)
        x1 = x.copy()
        F1 = list(F)
        for i in range(nx) :
            x1[index[i]] = x[i]
            F1[index[i]] = F[i]
        
        # shift jets maximum to X'=0 (remove equivalent regular divergence)
        shift = np.zeros(nx, dtype=np.float64)
        for i in range(nx) :
            z = F1[i](y)
            imax = np.argmax(z)
            shift[i] = y[imax]
        fs = interp1d(x1, shift, kind='cubic', bounds_error=False, fill_value=0.0)
        z = np.zeros(nx, dtype=np.float64)
        
        def answer(ax, ay) :
            # calculate shifted function at x
            by = ay - fs(ax)
            for i in range(nx) :
                z[i] = F1[i](by + shift[i])
            # interpolate over x1
            fx = interp1d(x1, z, kind='cubic', bounds_error=False, fill_value=0.0)
            # calculate result
            return fx(ax)
        return answer

    # integrate from radial to linear

    def integrate2d(self,x,y,z):
        sh = np.shape(z)
        n = sh[1]
        v = np.zeros(n, dtype=np.float64)
        for i in range(n):
            v[i] = trapz(z[:,i],y[:,i])
        return trapz(v,x[0,:])

    def calculateEmittance(self):

        if self.data is None :
            return
        nx = len(self.fileNames) 
        if nx <= 0 :
            return

        axes = self.mplWidget.canvas.ax
        
        self.execInitScript()

        # parameters
        x0 = self.readX0()      # [mm] X0 coordinates of scans
        ndh = np.zeros(nx-1)    # [mm] displacement of analyzer slit (number n) from axis
        x0auto = x0.copy()
        for i in range(1, nx) :
            ndh[i-1] = self.readParameter(i, 'ndh', 0.0, float)
            x0auto[i-1] = self.readParameter(i, 'x0', 0.0, float, select='auto')
        # common parameters
        R = self.readParameter(0, 'R', 2.0e5, float)    # [Ohm] Faraday cup load resistior
        l1 = self.readParameter(0, 'l1', 213.0, float)  # [mm] distance from source to analyzer aperture
        l2 = self.readParameter(0, 'l2', 195.0, float)  # [mm] analyzer base
        d1 = self.readParameter(0, 'd1', 0.5, float)    # [mm] analyzer hole diameter
        a1 = np.pi*d1*d1/4.0                            # [mm**2] analyzer hole area    
        d2 = self.readParameter(0, 'd2', 0.5, float)    # [mm] analyzer slit width

        self.logger.info('Emittance calculation using parameters:')
        self.logger.info('R=%fOhm; l1=%fmm; l2=%fmm; d1=%fmm; d2=%fmm'%(R,l1,l2,d1,d2))
        for i in range(nx) :
            try:
                s = 'Chan.%3d '%i
                s = s + 'x0=%5.1f mm; ndh=%5.1f mm; '%(x0[i-1],ndh[i-1])
                s = s + 'range=%s; '%str(self.readParameter(i, 'range'))
                s = s + 'offset=%f V; '%self.params[i]['offset']
                s = s + 'scale=%6.2f mm/V; '%self.params[i]['scale']
                s = s + 'MinI=%4d; Umin=%6.2f V; '%(self.params[i]['minindex'], self.params[i]['minvoltage'])
            except:
                pass
            self.logger.info(s)

        # calculate maximum and integral profiles
        self.calculateProfiles()

        # number of points for emittance matrix
        N = self.readParameter(0, 'N', 200, int)
        # calculate (N x nx-1) initial arrays
        # X [mm] -- X axis of emittance plot
        X0 = np.zeros((N,nx-1), dtype=np.float64)
        # X' [milliRadians] --  Y axis  of emittance plot
        Y0 = np.zeros((N,nx-1), dtype=np.float64)
        # Z [mkA] signal or current density
        Z0 = np.zeros((N,nx-1), dtype=np.float64)
        # F interpolating functions
        F0 = list(range(nx-1))     
        # Y range
        ymin = 1.0e99
        ymax = -1.0e99
        # calculate interpolating functions for initial data
        for i in range(nx-1) :
            y,z,index = self.readSignal(i+1)         # y in [Radians]; z < 0.0 in [A]
            yy = y[index]
            # convert to [Ampere/Radian/mm^2]
            zz = z[index] * l2/d2 / a1
            ymin = min([ymin, yy.min()])
            ymax = max([ymax, yy.max()])
            (yyy,zzz) = self.smoothX(yy,zz)
            F0[i] = interp1d(yyy, -zzz, kind='linear', bounds_error=False, fill_value=0.0)
        # symmetry for Y range
        if abs(ymin) > abs(ymax) :
            ymax = abs(ymin)
        else:
            ymax = abs(ymax)
        ymax *= 1.05
        ymin = -ymax
        # Y range array
        ys = np.linspace(ymin, ymax, N)
        # fill data arrays
        for i in range(nx-1) :
            X0[:,i] = x0[i]
            Y0[:,i] = ys
            Z0[:,i] = F0[i](Y0[:,i])
        # remove negative data
        Z0[Z0 < 0.0] = 0.0
        
        # X0,Y0,Z0,F0 -> X1,Y1,Z1,F1 sort data according rising x0
        index = np.argsort(X0[0,:])
        X1 = X0.copy()
        Y1 = Y0.copy()
        Z1 = Z0.copy()
        F1 = list(F0)
        for i in range(nx-1) :
            X1[:,index[i]] = X0[:,i]
            Y1[:,index[i]] = Y0[:,i]
            Z1[:,index[i]] = Z0[:,i]
            F1[index[i]] = F0[i]
        
        # X1,Y1,Z1 -> X2,Y2,Z2 remove average X and Y
        if self.readParameter(0, 'center', 'avg') == 'max':
            n = np.argmax(Z1)
            X1avg = X1.flat[n]
            Y1avg = Y1.flat[n]
        if self.readParameter(0, 'center', 'avg') == 'avg':
            Z1t = self.integrate2d(X1,Y1,Z1)
            X1avg = self.integrate2d(X1,Y1,X1*Z1)/Z1t
            Y1avg = self.integrate2d(X1,Y1,Y1*Z1)/Z1t
        Z2 = Z1
        X2 = X1.copy() - X1avg
        Y2 = Y1.copy() - Y1avg
        # debug draw 10
        if int(self.comboBox.currentIndex()) == 10:
            # cross-section current
            Z2t = self.integrate2d(X2,Y2,Z2) * d1 *1e6 # [mkA]
            self.logger.info('Total Z2 (cross-section current) = %f mkA'%Z2t)
            self.clearPicture()
            axes.contour(X2, Y2, Z2)
            axes.grid(True)
            axes.set_title('Z2 [N,nx-1] Initial data average shifted')
            self.mplWidget.canvas.draw()
            return
        
        # X2,Y2,Z2 -> X3,Y3,Z3 shift jets maximum to X'=0 (remove equivalent regular divergence)
        X3 = X2
        Y3 = Y2
        Z3 = Z2.copy()
        Shift = np.zeros(nx-1, dtype=np.float64)
        for i in range(nx-1) :
            z = Z2[:,i]
            imax = np.argmax(z)
            Shift[i] = Y2[imax,i] + Y1avg
            Z3[:,i] = F1[i](Y2[:,i] + Shift[i])
        # remove negative data
        Z3[Z3 < 0.0] = 0.0
        # debug draw 11
        if int(self.comboBox.currentIndex()) == 11:
            # cross-section current
            Z3t = self.integrate2d(X3,Y3,Z3) * d1 *1e6 # [mkA]
            self.logger.info('Total Z3 (cross-section current) = %f mkA'%Z3t)
            self.clearPicture()
            axes.contour(X3, Y3, Z3)
            axes.grid(True)
            axes.set_title('Z3 [N,nx-1] Regular divergence reduced')
            self.mplWidget.canvas.draw()
            return
        # debug draw 17
        if int(self.comboBox.currentIndex()) == 17:
            self.clearPicture()
            indexes = self.listWidget.selectedIndexes()
            for j in indexes:
                k = j.row()             
                self.plot(Y3[:,k-1]*1e3, Z3[:,k-1]*1e6, '.-', label='sh'+str(k))
                self.plot(Y1[:,k-1]*1e3, Z1[:,k-1]*1e6, '.-', label='or'+str(k))
            axes.set_title('Shifted elementary jets')
            axes.set_xlabel('X\', milliRadians')
            axes.set_ylabel('Current, mkA')
            self.mplWidget.canvas.draw()
            return

        # X3,Y3,Z3 -> X4,Y4,Z4 integrate emittance from cross-section to circular beam
        X4 = X3
        Y4 = Y3
        Z4 = Z3.copy()
        x = X3[0,:]
        y = x.copy()
        for i in range(nx-1) :
            xi = x[i]
            if xi >= 0.0:
                mask = x >= xi
                y[mask] = np.sqrt(x[mask]**2 - xi**2)
            if xi < 0.0:
                mask = x <= xi
                y[mask] = -np.sqrt(x[mask]**2 - xi**2)
            for k in range(N) :
                z = Z3[k,:].copy()
                Z4[k,i] = 2.0*trapz(z[mask], y[mask])
        Z4[Z4 < 0.0] = 0.0
        if int(self.comboBox.currentIndex()) == 13:
            # total beam current
            Z4t = self.integrate2d(X4,Y4,Z4) * 1000.0 # [mA]
            self.logger.info('Total Z4 (beam current) = %f mA'%Z4t)
            self.clearPicture()
            axes.contour(X4, Y4, Z4)
            axes.grid(True)
            axes.set_title('Z4 [N,nx] total beam')
            self.mplWidget.canvas.draw()
            return

        # X4,Y4,Z4 -> X5,Y5,Z5 resample to NxN array
        X5 = np.zeros((N, N), dtype=np.float64)
        Y5 = np.zeros((N, N), dtype=np.float64)
        Z5 = np.zeros((N, N), dtype=np.float64)
        xmin = x0.min()
        xmax = x0.max()
        if abs(xmin) > abs(xmax) :
            xmax = abs(xmin)
        else:
            xmax = abs(xmax)
        xmax *= 1.05
        xmin = -xmax
        xs = np.linspace(xmin, xmax, N)
        # X and Y
        for i in range(N) :
            X5[i,:] = xs
            Y5[:,i] = ys
        for i in range(N-1) :
            x = X4[i,:]
            z = Z4[i,:]
            index = np.unique(x, return_index=True)[1]
            f = interp1d(x[index], z[index], kind='cubic', bounds_error=False, fill_value=0.0)
            Z5[i,:] = f(X5[i,:])
        # remove negative currents
        Z5[Z5 < 0.0] = 0.0
        # debug plot 18
        if int(self.comboBox.currentIndex()) == 18:
            Z5t = self.integrate2d(X5,Y5,Z5) * 1000.0 # [mA]
            self.logger.info('Total Z5 (beam current) = %f mA'%Z5t)
            self.clearPicture()
            axes.contour(X5, Y5, Z5)
            axes.grid(True)
            axes.set_title('Z5 [N,N] no divergence')
            self.mplWidget.canvas.draw()
            return

        # X5,Y5,Z5 -> X6,Y6,Z6 return shift of jets back
        X6 = X5
        Y6 = Y5
        Z6 = np.zeros((N, N), dtype=np.float64)
        g = interp1d(X3[0,:], Shift, kind='cubic', bounds_error=False, fill_value=0.0)
        for i in range(N) :
            y = Y5[:,i]
            z = Z5[:,i]
            f = interp1d(y, z, kind='linear', bounds_error=False, fill_value=0.0)
            s = g(X5[0,i])
            Z6[:,i] = f(Y5[:,i] - s)
        Z6[Z6 < 0.0] = 0.0
        # debug plot 16
        if int(self.comboBox.currentIndex()) == 16:
            Z6t = self.integrate2d(X6,Y6,Z6) * 1000.0 # [mA]
            self.logger.info('Total Z6 (beam current) = %f mA'%Z6t)

            # experimental resample function
            #ff = self.interpolatePlot(X1[0,:],Y1[:,0],F1)
            #for i in range(N) :
            #    self.logger.info(i)
            #    for k in range(N) :
            #        pass
            #        #Z6[i,k] = ff(X6[i,k], Y6[i,k])
            #Z6[Z6 < 0.0] = 0.0
            #Z6t = self.integrate2d(X6,Y6,Z6) * 1000.0 # [mA]
            #self.logger.info('Total Z6 (beam current) = %f mA'%Z6t)

            self.clearPicture()
            axes.contour(X6, Y6, Z6)
            axes.grid(True)
            axes.set_title('Z6 [N,N] divergence back')
            self.mplWidget.canvas.draw()
            return
        
        # calculate emittance values
        q=1.6e-19        # [Q] electron charge
        m=1.6726e-27     # [kg]  proton mass
        c=2.9979e8       # [m/s] speed of light
        U = self.readParameter(0, 'energy', 32000.0, float)
        self.logger.info('Beam energy U= %f V'%U)
        beta = np.sqrt(2.0*q*U/m)/c
        self.logger.info('beta=%e'%beta)
        # X6,Y6,Z6 -> X,Y,Z final array X and Y centered to plot and emittance calculation
        X = X6
        Y = Y6
        Z = Z6 # [A/mm/Radian]
        Zt = self.integrate2d(X,Y,Z) # [A]
        # calculate average X and X'
        Xavg = self.integrate2d(X,Y,X*Z)/Zt
        Yavg = self.integrate2d(X,Y,Y*Z)/Zt
        # subtract average values 
        X = X - Xavg
        Y = Y - Yavg
        # calculate moments 
        XYavg = self.integrate2d(X,Y,X*Y*Z)/Zt
        XXavg = self.integrate2d(X,Y,X*X*Z)/Zt
        YYavg = self.integrate2d(X,Y,Y*Y*Z)/Zt
        # RMS Emittance
        self.RMS = np.sqrt(XXavg*YYavg-XYavg*XYavg) * 1000.0 # [Pi*mm*mrad]
        self.logger.info('Normalized RMS Emittance of total beam    %f Pi*mm*mrad'%(self.RMS*beta))
        # cross section RMS emittance
        Z2 = Z2 * d1 # [A/mm/Radian]
        Z2t = self.integrate2d(X2,Y2,Z2) # [A]
        X2avg = self.integrate2d(X2,Y2,X2*Z2)/Z2t
        Y2avg = self.integrate2d(X2,Y2,Y2*Z2)/Z2t
        # subtract average values 
        X2 = X2 - X2avg
        Y2 = Y2 - Y2avg
        # calculate moments 
        XY2avg = self.integrate2d(X2,Y2,X2*Y2*Z2)/Z2t
        XX2avg = self.integrate2d(X2,Y2,X2*X2*Z2)/Z2t
        YY2avg = self.integrate2d(X2,Y2,Y2*Y2*Z2)/Z2t
        # cross section RMS Emittance
        self.RMScs = np.sqrt(XX2avg*YY2avg-XY2avg*XY2avg) * 1000.0  # [Pi*mm*mrad]
        self.logger.info('Normalized RMS Emittance of cross-section %f Pi*mm*mrad'%(self.RMScs*beta))
        # calculate emittance fraction for density levels 
        # number of levels
        nz = 100    
        # level
        zl = np.linspace(0.0, Z.max(), nz)
        # total beam for level zl[i]
        zi = np.zeros(nz)
        # number of points inside level (~ total emittance)
        zn = np.zeros(nz)
        # RMS emittance for level
        zr = np.zeros(nz)

        for i in range(nz):
            mask = Z[:,:] >= zl[i]
            zn[i] = np.sum(mask)
            za = Z[mask]
            xa = X[mask]
            ya = Y[mask]
            zt = np.sum(za)
            zi[i] = zt
            xys = np.sum(xa*ya*za)/zt
            xxs = np.sum(xa*xa*za)/zt
            yys = np.sum(ya*ya*za)/zt
            zr[i] = np.sqrt(max([xxs*yys-xys*xys, 0.0]))*1000.0

        # levels to draw
        fractions = np.array(self.readParameter(0, 'fractions', [0.5,0.7,0.9]))
        levels = fractions*0.0
        emit = fractions*0.0
        rms = fractions*0.0
        zt = np.sum(Z)
        for i in range(len(fractions)):
            index = np.where(zi >= fractions[i]*zt)[0]
            n = index.max()
            levels[i] = zl[n]
            emit[i] = zn[n]
            rms[i] = zr[n]
        
        emit = emit*(X[0,0]-X[0,1])*(Y[0,0]-Y[1,0])/np.pi*beta*1000.0
        rms = rms*beta
        self.logger.info('% Current  Normalized emittance      Normalized RMS emittance')
        for i in range(len(levels)):
            self.logger.info('%2.0f %%       %5.3f Pi*mm*milliRadians  %5.3f Pi*mm*milliRadians'%(fractions[i]*100.0, emit[i], rms[i]))
        self.logger.info('%2.0f %%                                %5.3f Pi*mm*milliRadians'%(100.0, self.RMS*beta))
        # return X and Y to symmetrical range
        X = X + Xavg
        Y = Y + Yavg
        # subtract average values 
        if self.readParameter(0, 'center', 'avg') == 'max':
            n = np.argmax(Z)
            Xavg = X.flat[n]
            Yavg = Y.flat[n]
        if self.readParameter(0, 'center', 'avg') == 'avg':
            Zt = self.integrate2d(X,Y,Z) # [A]
            Xavg = self.integrate2d(X,Y,X*Z)/Zt
            Yavg = self.integrate2d(X,Y,Y*Z)/Zt
        # recalculate Z
        for i in range(N) :
            y = Y[:,i]
            z = Z[:,i]
            f = interp1d(y, z, kind='linear', bounds_error=False, fill_value=0.0)
            Z[:,i] = f(Y[:,i] + Yavg)
        for i in range(N) :
            x = X[i,:]
            z = Z[i,:]
            f = interp1d(x, z, kind='linear', bounds_error=False, fill_value=0.0)
            Z[i,:] = f(X[i,:] + Xavg)
        Z[Z < 0.0] = 0.0

        # save data to text file
        folder = self.logFileName
        fn = os.path.join(str(folder), progName + '_X.gz')
        np.savetxt(fn, X, delimiter='; ' )
        fn = os.path.join(str(folder), progName + '_Y.gz')
        np.savetxt(fn, Y, delimiter='; ' )
        fn = os.path.join(str(folder), progName + '_Z.gz')
        np.savetxt(fn, Z, delimiter='; ' )
            
        # plot contours
        if int(self.comboBox.currentIndex()) == 5:
            self.clearPicture()
            axes.contour(X, Y, Z, linewidths=1.0)
            axes.grid(True)
            axes.set_title('Emittance contour plot')
            #axes.set_ylim([ymin,ymax])
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Norm. RMS Emittance %5.3f Pi*mm*mrad'%(self.RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()
        # plot filled contours
        if int(self.comboBox.currentIndex()) == 6:
            self.clearPicture()
            axes.contourf(X, Y, Z)
            axes.grid(True)
            axes.set_title('Emittance color plot')
            #axes.set_ylim([ymin,ymax])
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Norm. RMS Emittance %5.3f Pi*mm*mrad'%(self.RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11, color='white')
            self.mplWidget.canvas.draw()
            return
        # plot levels
        if int(self.comboBox.currentIndex()) == 7:
            self.clearPicture()
            CS = axes.contour(X, Y, Z, linewidths=1.0, levels=levels[::-1])
            axes.grid(True)
            axes.set_title('Emittance contours for levels')
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            labels = ['%2d %% of current'%(fr*100) for fr in np.sort(fractions)[::-1]]
            for i in range(len(labels)):
                CS.collections[i].set_label(labels[i])
            axes.legend(loc='upper left')
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Norm. RMS Emittance %5.3f Pi*mm*mrad'%(self.RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()
            return
        # Emittance contour plot of beam cross-section
        if int(self.comboBox.currentIndex()) == 8:
            # X3,Y3,Z3 -> X5,Y5,Z5 resample to NxN array
            xmin = X3.min()
            xmax = X3.max()
            if abs(xmin) > abs(xmax) :
                xmax = abs(xmin)
            else:
                xmax = abs(xmax)
            xmax *= 1.05
            xmin = -xmax
            xs = np.linspace(xmin, xmax, N)
            ymin = Y3.min()
            ymax = Y3.max()
            if abs(ymin) > abs(ymax) :
                ymax = abs(ymin)
            else:
                ymax = abs(ymax)
            ymax *= 1.05
            ymin = -ymax
            ys = np.linspace(ymin, ymax, N)
            for i in range(N) :
                X5[i,:] = xs
                Y5[:,i] = ys
            for i in range(N-1) :
                x = X3[i,:]
                z = Z3[i,:]
                f = interp1d(x, z, kind='cubic', bounds_error=False, fill_value=0.0)
                Z5[i,:] = f(X5[i,:])
            # remove negative currents
            Z5[Z5 < 0.0] = 0.0
            # X5,Y5,Z5 -> X6,Y6,Z6 return shift of jets back
            g = interp1d(X3[0,:], Shift, kind='cubic', bounds_error=False, fill_value=0.0)
            for i in range(N) :
                y = Y5[:,i]
                z = Z5[:,i]
                f = interp1d(y, z, kind='linear', bounds_error=False, fill_value=0.0)
                s = g(X5[0,i])
                Z6[:,i] = f(Y5[:,i] - s)
            Z6[Z6 < 0.0] = 0.0
            X = X6
            Y = Y6
            Z = Z6 # [A/mm^2/Radian]
            if self.readParameter(0, 'center', 'avg') == 'max':
                n = np.argmax(Z)
                Xavg = X.flat[n]
                Yavg = Y.flat[n]
            if self.readParameter(0, 'center', 'avg') == 'avg':
                Zt = self.integrate2d(X,Y,Z) # [A]
                Xavg = self.integrate2d(X,Y,X*Z)/Zt
                Yavg = self.integrate2d(X,Y,Y*Z)/Zt
            # recalculate Z
            for i in range(N) :
                y = Y[:,i]
                z = Z[:,i]
                f = interp1d(y, z, kind='linear', bounds_error=False, fill_value=0.0)
                Z[:,i] = f(Y[:,i] + Yavg)
            for i in range(N) :
                x = X[i,:]
                z = Z[i,:]
                f = interp1d(x, z, kind='linear', bounds_error=False, fill_value=0.0)
                Z[i,:] = f(X[i,:] + Xavg)
            Z[Z < 0.0] = 0.0

            # save data to text file
            folder = self.logFileName
            fn = os.path.join(str(folder), progName + '_X_cs.gz')
            np.savetxt(fn, X, delimiter='; ' )
            fn = os.path.join(str(folder), progName + '_Y_cs.gz')
            np.savetxt(fn, Y, delimiter='; ' )
            fn = os.path.join(str(folder), progName + '_Z_cs.gz')
            np.savetxt(fn, Z, delimiter='; ' )
            
            self.clearPicture()
            axes.contour(X, Y, Z, linewidths=1.0)
            axes.grid(True)
            axes.set_title('Emittance contour plot of beam cross-section')
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            axes.annotate('Cross-section I=%5.1f mkA'%(self.Ics*1e6) + '; Norm. RMS Emittance %5.3f Pi*mm*mrad'%(self.RMScs*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()

    '''
    def resampleAndCenter(x,y,z,N):
            # x,y,z -> X5,Y5,Z5 resample to NxN array
            xmax = max([abs(x.max()), abs(x.min())])*1.05
            xmin = -xmax
            xarr = np.linspace(-xmax, xmax, N)
            ymax = max([abs(y.max()), abs(y.min())])*1.05
            ymin = -ymax
            yarr = np.linspace(ymin, ymax, N)
            X5 = np.zeros((N, N), dtype=np.float64)
            Y5 = np.zeros((N, N), dtype=np.float64)
            Z5 = np.zeros((N, N), dtype=np.float64)
            for i in range(N) :
                X5[i,:] = xarr
                Y5[:,i] = yarr
            for i in range(N-1) :
                xi = x[i,:]
                zi = z[i,:]
                f = interp1d(xi, zi, kind='cubic', bounds_error=False, fill_value=0.0)
                Z5[i,:] = f(X5[i,:])
            # remove negative currents
            Z5[Z5 < 0.0] = 0.0
            # X5,Y5,Z5 -> X6,Y6,Z6 return shift of jets back
            g = interp1d(X3[0,:], Shift, kind='cubic', bounds_error=False, fill_value=0.0)
            for i in range(N) :
                y = Y5[:,i]
                z = Z5[:,i]
                f = interp1d(y, z, kind='linear', bounds_error=False, fill_value=0.0)
                s = g(X5[0,i])
                Z6[:,i] = f(Y5[:,i] - s)
            Z6[Z6 < 0.0] = 0.0
            X = X6
            Y = Y6
            Z = Z6 # [A/mm^2/Radian]
            if self.readParameter(0, 'center', 'avg') == 'max':
                n = np.argmax(Z)
                Xavg = X.flat[n]
                Yavg = Y.flat[n]
            if self.readParameter(0, 'center', 'avg') == 'avg':
                Zt = self.integrate2d(X,Y,Z) # [A]
                Xavg = self.integrate2d(X,Y,X*Z)/Zt
                Yavg = self.integrate2d(X,Y,Y*Z)/Zt
            # recalculate Z
            for i in range(N) :
                y = Y[:,i]
                z = Z[:,i]
                f = interp1d(y, z, kind='linear', bounds_error=False, fill_value=0.0)
                Z[:,i] = f(Y[:,i] + Yavg)
            for i in range(N) :
                x = X[i,:]
                z = Z[i,:]
                f = interp1d(x, z, kind='linear', bounds_error=False, fill_value=0.0)
                Z[i,:] = f(X[i,:] + Xavg)
            Z[Z < 0.0] = 0.0
    return (X,Y,Z)
    '''
                
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

            # print OK message and exit    
            self.logger.info('Default configuration set.')
            return True
        except :
            # print error info    
            self.printExceptionInfo(level=logging.DEBUG)
            self.logger.log(logging.INFO, 'Default configuration set error.')
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