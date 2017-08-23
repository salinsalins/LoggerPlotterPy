# coding: utf-8
'''
Created on Jul 2, 2017

@author: sanin
'''
# used to parse files more easily
from __future__ import with_statement
from __future__ import print_function

import os.path
import shelve
import sys

from findRegions import findRegions as findRegions
from findRegions import restoreFromRegions as restoreFromRegions
from smooth import smooth
from printl import printl 
from readTekFiles import readTekFiles

try:
    from PyQt4.QtGui import QMainWindow
    from PyQt4.QtGui import QApplication
    from PyQt4.QtGui import qApp
    from PyQt4.QtGui import QFileDialog
    from PyQt4.QtGui import QTableWidgetItem
    from PyQt4 import uic
except:
    from PyQt5.QtWidgets import QMainWindow
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtWidgets import qApp
    from PyQt5.QtWidgets import QFileDialog
    from PyQt5.QtWidgets import QTableWidgetItem
    from PyQt5 import uic

import numpy as np
from scipy.integrate import trapz
from scipy.interpolate import interp1d
from scipy.ndimage.filters import gaussian_filter

_progName = 'Emittance'
_progVersion = '_5_1'
_settingsFile = _progName + '_init.dat'
_initScript =  _progName + '_init.py'
_logFile =  _progName + '_log.log'

class DesignerMainWindow(QMainWindow):
    """Customization for Qt Designer created window"""
    def __init__(self, parent = None):
        # initialization of the superclass
        super(DesignerMainWindow, self).__init__(parent)
        # load the GUI 
        uic.loadUi('Emittance.ui', self)
        # connect the signals with the slots
        self.actionOpen.triggered.connect(self.selectFolder)
        self.pushButton_2.clicked.connect(self.selectFolder)
        self.actionQuit.triggered.connect(qApp.quit)
        self.pushButton_4.clicked.connect(self.processFolder)
        self.pushButton_6.clicked.connect(self.pushPlotButton)
        self.pushButton_7.clicked.connect(self.erasePicture)
        self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
        # variables definition
        self.data = None
        self.scanVoltage = None
        self.paramsAuto = None
        self.fleNames = []
        self.folderName = ''
        # welcome message
        printl(_progName + _progVersion + ' started')
        # restore global settings from default location
        self.restoreSettings()
        # read data files
        self.parseFolder(folder = self.folderName)
        # restore local settings
        if not self.restoreSettings(folder = self.folderName, local=True):
            self.processFolder()
    
    def selectFolder(self):
        """Opens a dataFile select dialog"""
        # open the dialog and get the selected dataFolder
        folder = self.folderName
        fileOpenDialog = QFileDialog(caption='Select directory with data files', directory=folder)
        # select folder, not file
        dataFolder = fileOpenDialog.getExistingDirectory()
        # if a dataFolder is selected
        if dataFolder:
            if self.folderName == dataFolder:
                return
            i = self.comboBox_2.findText(dataFolder)
            if i >= 0:
                self.comboBox_2.setCurrentIndex(i)
            else:
                # add item to history  
                self.comboBox_2.insertItem(-1, dataFolder)
                self.comboBox_2.setCurrentIndex(0)
    
    def selectionChanged(self, i):
        #print('Selection changed %s'%str(i))
        if i < 0:
            return
        dataFolder = str(self.comboBox_2.currentText())
        if self.folderName != dataFolder:
            self.parseFolder(dataFolder)
            # restore local settings
            if not self.restoreSettings(folder=dataFolder, local=True):
                self.processFolder()
 
    def onQuit(self) :
        # save settings to folder
        self.saveSettings(folder = self.folderName)
        # save global settings
        self.saveSettings()

    def clearPicture(self, force=False):
        if force or self.checkBox.isChecked():
            # clear the axes
            self.erasePicture()
        
    def erasePicture(self):
        self.mplWidget.canvas.ax.clear()
        self.mplWidget.canvas.draw()

    def parseFolder(self, folder, mask='*.isf'):
        printl('%s%s switch to folder %s'%(_progName, _progVersion, folder))
        # read data
        self.data, self.fileNames = readTekFiles(folder, mask)
        # number of files
        nx = len(self.fileNames)
        if nx <= 0 :
            return
        # switch to local log file
        printl('', stamp=False, fileName = os.path.join(str(folder), _logFile))
        printl('%s%s parsing local folder %s'%(_progName, _progVersion, folder)) 
        # fill listWidget with file names
        self.listWidget.clear()
        # make file names list
        names = [name.replace(folder, '')[1:] for name in self.fileNames]
        for i in range(nx):
            names[i] = '%3d - %s'%(i,names[i])
        # fill listWidget
        self.listWidget.addItems(names)
        self.folderName = folder
    
    def processFolder(self):
        folder = self.folderName
        printl('Processing folder %s'%folder)
        print('Reading data ...')
        # read data array
        data,files  = readTekFiles(folder)
        # number of files
        nx = len(files)
        if nx <= 0 :
            print('Nothing to process')
            return False
        print('%d files fond'%nx)
        # size of Y data
        ny = len(data[0])
        # define arrays
        zero  = np.zeros((nx, ny), dtype=np.float64)
        weight = np.zeros((nx, ny), dtype=np.float64)
        # index array
        ix = np.arange(ny)
        # smooth
        ns = 1
        try:
            ns = int(self.spinBox.value())
        except:
            pass

        # default parameters array
        params = [{'smooth':ns, 'offset':0.0, 'zero':np.zeros(ny), 'scale': 1.95} for i in range(nx)]
        # smooth data array
        print('Smoothing data ...')
        for i in range(nx) :
            y = data[i,:]
            smooth(y, params[i]['smooth'])
            data[i,:] = y
        
        print('Processing scan voltage ...')
        # channel 0 is by default scan voltage 
        x = data[0,:].copy()
        # additionally smooth x 
        smooth(x, params[0]['smooth']*2)
        # find longest monotonic region of scan voltage
        xdiff = np.diff(x)
        xdiff = np.append(xdiff, xdiff[-1])
        mask = xdiff >= 0.0
        regions = findRegions(np.where(mask)[0])         
        # find longest region
        xr = [0,1]
        for r in regions:
            if r[1]-r[0] >= xr[1]-xr[0]:
                xr = r
        mask = xdiff <= 0.0
        regions = findRegions(np.where(mask)[0])         
        for r in regions:
            if r[1]-r[0] >= xr[1]-xr[0]:
                xr = r
        xi = np.arange(xr[0], xr[1])
        params[0]['range'] = xr
        printl('Scan voltage region %s'%str(xr))
        # debug draw 8 Scan voltage region
        self.debugDraw([ix,x,ix[xi],x[xi]])
                    
        # auto process data for zero line and offset
        print('Processing zero lines and offsets ...')
        for i in range(1,nx-1) :
            #print('Channel %d'%(i))
            y1 = data[i,:].copy()
            offset1 = params[i]['offset']
            y1 = y1 - offset1
            y2 = data[i+1,:].copy()
            offset2 = params[i+1]['offset']
            y2 = y2 - offset2
            # double smooth because zero line is slow 
            smooth(y1, params[i]['smooth']*2)
            smooth(y2, params[i+1]['smooth']*2)
            # offsets calculated from upper 10%
            y1min = np.min(y1)
            y1max = np.max(y1)
            dy1 = y1max - y1min
            y2min = np.min(y2)
            y2max = np.max(y2)
            dy2 = y2max - y2min
            dy = max([dy1, dy2])
            i1 = np.where(y1 > (y1max - 0.1*dy))[0]
            o1 = np.average(y1[i1])
            #print('Offset 1 %f'%o1)
            i2 = np.where(y2 > (y2max - 0.1*dy))[0]
            o2 = np.average(y2[i2])
            #print('Offset 2 %f'%o2)
            # debug draw 9 Offset calculation
            self.debugDraw([i,ix,y1,o1,y2,o2,i1,i2])
            # correct y2 and offset2 for calculated offsets
            y2 = y2 - o2 + o1
            offset2 = offset2 + o2 - o1 
            # zero line = where 2 signals are almost equal
            mask = np.abs(y1 - y2) < 0.05*dy1
            index = np.where(mask)[0]
            # filter signal intersection regions
            index = restoreFromRegions(findRegions(index, 50, 300, 100, 100, length=ny))
            if len(index) <= 0:
                index = np.where(mask)[0]
            # new offset
            offset = np.average(y2[index] - y1[index])
            #print('Offset for channel %d = %f'%((i+1), offset))
            # shift y2 and offset2
            y2 = y2 - offset
            offset2 = offset2 + offset 
            # save processed offset
            params[i+1]['offset'] = offset2
            # index with new offset
            #print('4% index with corrected offset')
            mask = np.abs(y1 - y2) < 0.04*dy1
            index = np.where(mask)[0]
            #print(findRegionsText(index))
            # filter signal intersection
            regions = findRegions(index, 50)
            index = restoreFromRegions(regions, 0, 150, length=ny)
            #print(findRegionsText(index))
            # choose largest values
            mask[:] = False
            mask[index] = True
            mask3 = np.logical_and(mask, y1 >= y2)
            index3 = np.where(mask3)[0]
            # update zero line for all channels
            for j in range(1,nx) :
                w = 1.0/((abs(i - j))**2 + 1.0)
                zero[j,index3] = (zero[j,index3]*weight[j,index3] + y1[index3]*w)/(weight[j,index3] + w)
                weight[j,index3] += w
            mask4 = np.logical_and(mask, y1 <= y2)
            index4 = np.where(mask4)[0]
            # update zero line for all channels
            for j in range(1,nx) :
                w = 1.0/((abs(i + 1 - j))**2 + 1.0)
                zero[j,index4] = (zero[j,index4]*weight[j,index4] + y2[index4]*w)/(weight[j,index4] + w)
                weight[j,index4] += w
            # debug draw 10 zero line intermediate results
            self.debugDraw([ix, data, zero, params])
        # save processed zero line
        for i in range(nx) :
            params[i]['zero'] = zero[i]
        
        # determine signal area
        print('Processing signals ...')
        for i in range(1, nx) :
            #print('Channel %d'%i)
            y0 = data[i,:].copy()[xi]
            smooth(y0, params[i]['smooth'])
            z = zero[i].copy()[xi] + params[i]['offset']
            smooth(z, params[i]['smooth']*2)
            y = y0 - z
            ymin = np.min(y)
            ymax = np.max(y)
            dy = ymax - ymin
            mask = y < (ymax - 0.6*dy)
            index = np.where(mask)[0]
            ra = findRegions(index)
            params[i]['range'] = xr
            # determine scale
            is1 = xi[0]
            is2 = xi[-1]
            if len(ra) >= 1:
                is1 = np.argmin(y[ra[0][0]:ra[0][1]]) + ra[0][0] + xi[0]
            if len(ra) >= 2:
                is2 = np.argmin(y[ra[1][0]:ra[1][1]]) + ra[1][0] + xi[0]
            params[i]['scale'] = 10.0/(x[is2] - x[is1])   # [mm/Volt]
            if np.abs(x[is1]) < np.abs(x[is2]) :
                index = is1
            else:
                index = is2
            params[i]['minindex'] = index
            params[i]['minvoltage'] = x[index]
            di = int(abs(is2 - is1)/2.0)
            ir1 = max([xi[ 0], index - di])
            ir2 = min([xi[-1], index + di])
            params[i]['range'] = [ir1, ir2]
            # debug draw 11 Range and scale calculation
            self.debugDraw([i,xi,y,ix[ir1:ir2],y[ir1 - xi[0]:ir2 - xi[0]],is1,is2])
        
        # filter scales
        sc0 = np.array([params[i]['scale'] for i in range(1,nx)])
        sc = sc0.copy()
        asc = np.average(sc)
        ssc = np.std(sc)
        while ssc > 0.3*np.abs(asc):
            index1 = np.where(abs(sc - asc) <= 2.0*ssc)[0]
            index2 = np.where(abs(sc - asc) > 2.0*ssc)[0]
            sc[index2] = np.average(sc[index1])
            asc = np.average(sc)
            ssc = np.std(sc)
        for i in range(1,nx) :
            params[i]['scale'] = sc[i-1] 

        # common parameters
        print('Set common parameters ...')
        # Default parameters of measurements
        params[0]['R'] = 2.0e5  # Ohm   Resistor for beamlet scanner FC
        params[0]['d1'] = 0.5   # mm    Analyzer hole diameter
        params[0]['d2'] = 0.5   # mm    Collector Slit Width
        l1 = 213.0
        params[0]['l1'] = l1    # mm    Distance From emission hole to analyzer hole
        l2 = 195.0
        params[0]['l2'] = l2    # mm    Scanner base
        
        # save to member variable
        self.paramsAuto = params

        # execute init script
        self.execInitScript()

        # X0 and ndh calculation
        l1 = self.readParameter(0, "l1", 213.0, float)
        l2 = self.readParameter(0, "l2", 195.0, float)
        x00 = np.zeros(nx-1)
        for i in range(1, nx) :
            s = self.readParameter(i, "scale", 2.0, float)
            u = self.readParameter(i, "minvoltage", 0.0, float)
            x00[i-1] = -s*u*l1/l2
            #print('%3d N=%d Umin=%f scale=%f X00=%f'%(i, j, u, s, x00[i-1]))
        npt = 0
        sp = 0.0
        nmt = 0
        sm = 0.0
        dx = x00.copy()*0.0
        #print('%3d X00=%f DX=%f'%(0, x00[0], 0.0))
        for i in range(1, nx-1) :
            dx[i] = x00[i] - x00[i-1]
            if dx[i] > 0.0:
                npt += 1
                sp += dx[i]
            if dx[i] < 0.0:
                nmt += 1
                sm += dx[i]
            #print('%3d X00=%f DX=%f'%(i, x00[i], dx[i]))
        #print('npt=%d %f nmt=%d %f %f'%(npt,sp/npt,nmt,sm/nmt,sp/npt-l1/l2*10.))
        x01 = x00.copy()
        h = x00.copy()*0.0
        for i in range(1, nx-1) :
            if npt > nmt :
                x01[i] = x01[i-1] + sp/npt
                if dx[i] > 0.0:
                    h[i] = h[i-1]
                else:
                    h[i] = h[i-1] + 10.0
            else:
                x01[i] = x01[i-1] + sm/nmt
                if dx[i] < 0.0:
                    h[i] = h[i-1]
                else:
                    h[i] = h[i-1] - 10.0
        x01 = x01 - np.average(x01)
        k = int(np.argmin(np.abs(x01)))
        h = h - h[k]
        for i in range(1, nx) :
            params[i]['ndh'] = h[i-1]
            s = self.readParameter(i, "scale", 1.7, float)
            u = self.readParameter(i, "minvoltage", 0.0, float)
            x01[i-1] = (h[i-1] - s*u)*l1/l2 
            params[i]['x0'] = x01[i-1] 
            #print('%3d'%i, end='  ')
            #print('X0=%f mm ndh=%4.1f mm'%(params[i]['x0'],params[i]['ndh']), end='  ')
            #print('X00=%f mm DX=%f mm'%(x00[i-1], dx[i-1]))
        # print calculated parameters
        for i in range(nx) :
            try:
                s = 'Chan.%3d '%i
                s = s + 'range=%s; '%str(params[i]['range'])
                s = s + 'offset=%f V; '%params[i]['offset']
                s = s + 'scale=%6.2f mm/V; '%params[i]['scale']
                s = s + 'MinI=%4d; Umin=%6.2f V; '%(params[i]['minindex'], params[i]['minvoltage'])
                s = s + 'x0=%5.1f mm; ndh=%5.1f mm'%(params[i]['x0'],params[i]['ndh'])
            except:
                pass
            printl(s)
        # debug draw 12 X0 calculation
        self.debugDraw([x01,nx,k])
        
        # save processed to member variable
        self.paramsAuto = params
        print('Auto parameters has been calculated')
        
        return True
                
    def debugDraw(self, data=[]):
        try:
            axes = self.mplWidget.canvas.ax
            # debug draw 8 Scan voltage region
            #self.debugDraw([ix,x,ix[xi],x[xi]])
            if int(self.comboBox.currentIndex()) == 8:
                self.clearPicture()
                axes.set_title('Scan voltage region')
                axes.set_xlabel('Point index')
                axes.set_ylabel('Voltage, V')
                axes.plot(data[0], data[1], label='Scan voltage')
                axes.plot(data[2], data[3], '.', label='Region')
                self.zoplot()
                axes.grid(True)
                axes.legend(loc='best') 
                self.mplWidget.canvas.draw()
            # debug draw 9 Offset calculation
            #self.debugDraw([i,ix,y1,o1,y2,o2,i1,i2])
            if int(self.comboBox.currentIndex()) == 9 :
                indexes = self.listWidget.selectedIndexes()
                i = data[0]
                ix = data[1]
                y1 = data[2]
                o1 = data[3]
                y2 = data[4]
                o2 = data[5]
                i1 = data[6]
                i2 = data[7]
                if (len(indexes) > 0) and (i == indexes[0].row()):
                    self.clearPicture()
                    axes.set_title('Offset calculation')
                    axes.set_xlabel('Point index')
                    axes.set_ylabel('Signal, V')
                    axes.plot(ix, y1,'r', label='raw'+str(i))
                    self.zoplot(o1,'r')
                    axes.plot(ix, y2,'b', label='raw'+str(i+1))
                    self.zoplot(o2,'b')
                    axes.plot(ix[i1], y1[i1], '.')
                    axes.plot(ix[i2], y2[i2], '.')
                    axes.grid(True)
                    axes.legend(loc='best') 
                    self.mplWidget.canvas.draw()
            # debug draw 10 zero line intermediate results
            #self.debugDraw([ix, data, zero, params])
            if int(self.comboBox.currentIndex()) == 10 :
                ix = data[0]
                d = data[1]
                zero = data[2]
                params = data[3]
                indexes = self.listWidget.selectedIndexes()
                if len(indexes) > 0:
                    k = indexes[0].row()             
                    self.clearPicture()
                    axes.set_title('Zero line calculation')
                    axes.set_xlabel('Point index')
                    axes.set_ylabel('Signal, V')
                    axes.plot(ix, d[k,:], label='raw '+str(k))
                    z = zero[k].copy() + params[k]['offset']
                    smooth(z, params[k]['smooth']*2)
                    axes.plot(ix, z, label='zero'+str(k))
                    axes.grid(True)
                    axes.legend(loc='best') 
                    self.mplWidget.canvas.draw()
            # debug draw 11 Range and scale calculation
            #self.debugDraw([i,xi,y,ix[ir1:ir2],y[ir1 - xi[0]:ir2 - xi[0]],is1,is2])
            if int(self.comboBox.currentIndex()) == 11:
                indexes = self.listWidget.selectedIndexes()
                i = data[0]
                if (len(indexes) > 0) and (i == indexes[0].row()):
                    self.clearPicture()
                    axes.set_title('Range and scale calculation')
                    axes.set_xlabel('Point index')
                    axes.set_ylabel('Signal, V')
                    axes.plot(data[1], data[2], label='proc '+str(i))
                    axes.plot(data[3], data[4], '.', label='range'+str(i))
                    self.voplot(data[5], 'r')
                    self.voplot(data[6], 'b')
                    axes.grid(True)
                    axes.legend(loc='best') 
                    self.mplWidget.canvas.draw()
            # debug draw 12 X0 calculation
            #self.debugDraw([x01,nx,k])
            if int(self.comboBox.currentIndex()) == 12:
                x01 = data[0]
                nx = data[1]
                k = data[2]
                x0 = x01.copy()
                for i in range(1, nx) :
                    x0[i-1] = self.readParameter(i, 'x0', 0.0, float)
                if int(self.comboBox.currentIndex()) == 12:
                    self.clearPicture()
                    axes.set_title('X0 calculation')
                    axes.set_xlabel('Index')
                    axes.set_ylabel('X0, mm')
                    axes.plot(x01-x01[k], 'o-', label='X0 calculated')
                    axes.plot(x0-x0[k], 'd-', label='X0 from parameters')
                    axes.grid(True)
                    axes.legend(loc='best') 
                    self.mplWidget.canvas.draw()
        except:
            self.printExceptionInfo()

    def readParameter(self, row, name, default=None, dtype=None, info=False, select=''):
        if name == 'zero':
            return self.readZero(row)
        vd = default
        t = 'default'
        v = vd
        try:
            va = self.paramsAuto[row][name]
            t = 'auto'
            v = va
        except:
            va = None
        try:
            vm = self.paramsManual[row][name]
            t = 'manual'
            v = vm
        except:
            vm = None
        if dtype is not None :
            v = dtype(v)
        if info :
            print('row:%d name:%s %s value:%s (default:%s auto:%s manual:%s)'%(row, name, t, str(v), str(vd), str(va), str(vm)))
        if select == 'manual':
            return vm
        if select == 'auto':
            return va
        if select == 'default':
            return vd
        return v

    def readZero(self, row):
        if self.data is None:
            return None
        try:
            z = self.paramsAuto[row]['zero'].copy()
        except:
            z = np.zeros_like(self.data[0])
        # manual zero line
        try:
            # manual regions
            zr = self.paramsManual[row]['zero']
            for zi in zr:
                try:
                    if zi[0] == -1 :
                        # linear interpolation
                        z0 = self.data[row, :].copy()
                        ns = self.readParameter(row, "smooth", self.spinBox.value(), int)
                        smooth(z0, ns)
                        of = self.readParameter(row, "offset", 0.0, float)
                        z0 = z0 - of # minus is correct !!!
                        y1 = z0[zi[1]]
                        y2 = z0[zi[2]]
                        z[zi[1]:zi[2]+1] = np.interp(np.arange(zi[1],zi[2]+1), [zi[1],zi[2]], [y1,y2])
                    if zi[0] > 0 :
                        z0 = self.data[zi[0], :].copy()
                        ns = self.readParameter(zi[0], "smooth", 1, int)
                        of = self.readParameter(zi[0], "offset", 0.0, float)
                        smooth(z0, 2*ns)
                        z[zi[1]:zi[2]] = z0[zi[1]:zi[2]] + of
                except:
                    pass
        except:
            pass
        return z

    def readSignal(self, row):
        if self.data is None :
            return
        #print('Processing %d'%row)
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
        # filter x to be unique and smooth
        x = xsub[index]
        yy = y[index]
        xmax = x.max()
        xmin = x.min()
        x1 = np.linspace(xmin,xmax,len(x))
        for i in index[:-2]:
            j = i-r[0]
            mask = np.logical_and(x >= x1[j], x < x1[j+1])
            n = np.sum(mask)
            if n > 0.0:
                y[i] = np.sum(yy[mask])/float(n)
            else:
                y[i] = y[i-1]
        index = index[:-2]
        xsub[index] = x[index-r[0]]
        return (xsub, y, index)

    def readX0(self):
        nx = len(self.fileNames) 
        if nx <= 0 :
            return
        self.execInitScript()
        x0 = np.zeros(nx-1)                         # [mm] X0 coordinates of scans
        flag = self.readParameter(0, 'autox0', False)
        for i in range(1, nx) :
            if flag:
                x0[i-1] = self.readParameter(i, 'x0', 0.0, float, select='auto')
            else:
                x0[i-1] = self.readParameter(i, 'x0', 0.0, float)
        return x0
        
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

    def zoplot(self, v=0.0, color='k'):
        axes = self.mplWidget.canvas.ax
        xlim = axes.get_xlim()
        axes.plot(xlim, [v, v], color=color)
        axes.set_xlim(xlim)

    def voplot(self, v=0.0, color='k'):
        axes = self.mplWidget.canvas.ax
        ylim = axes.get_ylim()
        axes.plot([v, v], ylim, color=color)
        axes.set_ylim(ylim)

    def cls(self):
        self.clearPicture()

    def getX(self):
        ix = self.spinBox_2.value()
        if ix >= 0:
            x = self.data[ix, :].copy()
            ns = self.readParameter(ix, "smooth", self.spinBox.value(), int, True)
            smooth(x, ns)
            xTitle = 'Scan Voltage, V'
        else:
            x = np.arange(len(self.data[0, :]))
            xTitle = 'Point index'
        return (x,xTitle)

    def plotRawSignals(self):
        self.execInitScript()
        self.clearPicture()
        if self.data is None :
            return
        # draw chart
        axes = self.mplWidget.canvas.ax
        x,xTitle = self.getX()
        indexes = self.listWidget.selectedIndexes()
        for i in indexes :
            row = i.row()
            y = self.data[row, :].copy()
            ns = self.readParameter(row, "smooth", self.spinBox.value(), int, True)
            smooth(y, ns)
            z = self.readZero(row) + self.readParameter(row, 'offset')
            axes.plot(x, y, label='raw '+str(row))
            axes.plot(x, z, label='zero'+str(row))
        axes.plot(axes.get_xlim(), [0.0,0.0], color='k')
        axes.grid(True)
        axes.set_title('Signals with zero line')
        axes.set_xlabel(xTitle)
        axes.set_ylabel('Signal Voltage, V')
        axes.legend(loc='best') 
        self.mplWidget.canvas.draw()

    def plotProcessedSignals(self):
        """Plots processed signals"""
        if self.data is None :
            return
        self.execInitScript()
        # clear the Axes
        self.clearPicture()
        x,xTitle = self.getX()
        # draw chart
        indexes = self.listWidget.selectedIndexes()
        axes = self.mplWidget.canvas.ax
        for i in indexes :
            row = i.row()
            u,y,index = self.readSignal(row)
            # convert back from Ampers to Volts
            y = y * self.readParameter(0, "R", 2.0e5, float)
            # plot processed signal
            self.plot(x, y, label='proc '+str(row))
            # highlight signal region
            self.plot(x[index], y[index], label='range'+str(row))
            print('Signal %d'%row)
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
 
    def plotElementaryJet(self):
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
        
        if int(self.comboBox.currentIndex()) == 16:
            self.plotRawSignals()
            return
        if int(self.comboBox.currentIndex()) == 17:
            self.plotProcessedSignals()
            return
        if int(self.comboBox.currentIndex()) == 18:
            self.plotElementaryJet()
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
        #printl('', stamp=False)
        #printl('Emittance calculation using parameters:')
        #printl('Use calculated X0 = %s'%str(flag))
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
        #printl('R=%fOhm l1=%fmm l2=%fmm d1=%fmm d2=%fmm'%(R,l1,l2,d1,d2))
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
                #print(i,h)
                yu = yy[h] # [A]
                self.profilemax[i-1] = -1.0 * np.min(yu)      # [A]
                yu = yu / (d2/l2) # convert Y to density [A/Radian]
                # integrate by trapezoids method
                self.profileint[i-1] = -1.0 * trapz(yu, xu)  # [A]
                #print(i, self.profileint[i-1])
            except:
                self.printExceptionInfo()
        # sort in x0 increasing order
        ix0 = np.argsort(x0)
        x0s = x0[ix0]
        #print(x0s)
        self.profileint = self.profileint[ix0]
        #print(self.profileint)
        self.profilemax = self.profilemax[ix0]
        #print(self.profilemax)
        # remove average x
        xavg = trapz(x0s * self.profileint, x0s) / trapz(self.profileint, x0s)
        print('Average X %f mm'%xavg)
        x0s = x0s - xavg
        self.profileint = self.profileint / a1 # convert to local current density [A/mm^2]
        # cross-section current
        Ics = trapz(self.profileint, x0s)*d1 # [A] -  integrate over x and multiply to y width
        printl('Cross-section current %f mA'%(Ics*1000.0)) # from Amperes to mA
        # calculate total current
        index = np.where(x0s >= 0.0)[0]
        Ir = trapz(x0s[index]*self.profileint[index], x0s[index])*2.0*np.pi
        print('Total current right %f mA'%(Ir*1000.0)) # from Amperes to mA
        index = np.where(x0s <= 0.0)[0]
        Il = -1.0*trapz(x0s[index]*self.profileint[index], x0s[index])*2.0*np.pi
        print('Total current left %f mA'%(Il*1000.0)) # from Amperes to mA
        self.I = (Il + Ir)/2.0 #[A]
        printl('Total current %f mA'%(self.I*1000.0))  # from Amperes to mA
        # save profile data
        folder = self.folderName
        fn = os.path.join(str(folder), 'InegralProfile.txt')
        np.savetxt(fn, np.array([x0,self.profileint]).T, delimiter='; ' )
        fn = os.path.join(str(folder), 'MaximumProfile.txt')
        np.savetxt(fn, np.array([x0,self.profilemax]).T, delimiter='; ' )
        # plot profiles
        axes = self.mplWidget.canvas.ax
        # plot integral profile
        if int(self.comboBox.currentIndex()) == 0:
            self.clearPicture()
            axes.set_title('Integral profile')
            axes.set_xlabel('X0, mm')
            axes.set_ylabel('Beamlet current, mkA')
            axes.plot(x0s, self.profileint*1.0e6, 'd-', label='Integral Profile')
            #axes.plot(x0s, gaussfit(x0s,profileint,x0s), '--', label='Gaussian fit')
            axes.grid(True)
            axes.legend(loc='best') 
            self.mplWidget.canvas.draw()
            #return
        # plot maximal profile
        if int(self.comboBox.currentIndex()) == 1:
            self.clearPicture()
            axes.set_title('Maximum profile')
            axes.set_xlabel('X0, mm')
            axes.set_ylabel('Maximal current, mkA')
            axes.plot(x0s, self.profilemax*1.0e6, 'o-', label='Maximum Profile')
            #axes.plot(x0s, gaussfit(x0s,profilemax,x0s), '--', label='Gaussian fit')
            axes.grid(True)
            axes.legend(loc='best') 
            self.mplWidget.canvas.draw()

    def calculateEmittance(self):
        def integrate2d(x,y,z):
            sh = np.shape(z)
            n = sh[1]
            v = np.zeros(n, dtype=np.float64)
            for i in range(n):
                v[i] = trapz(z[:,i],y[:,i])
            return trapz(v,x[0,:])

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
        # R
        R = self.readParameter(0, 'R', 2.0e5, float)    # [Ohm] Faraday cup load resistior
        # l1
        l1 = self.readParameter(0, 'l1', 213.0, float)  # [mm] distance from source to analyzer aperture
        # l2
        l2 = self.readParameter(0, 'l2', 195.0, float)  # [mm] analyzer base
        # d1 and hole area
        d1 = self.readParameter(0, 'd1', 0.5, float)    # [mm] analyzer hole diameter
        a1 = np.pi*d1*d1/4.0                            # [mm**2] analyzer hole area    
        # d2
        d2 = self.readParameter(0, 'd2', 0.5, float)    # [mm] analyzer slit width

        printl('', stamp=False)
        printl('Emittance calculation using parameters:')
        printl('R=%fOhm; l1=%fmm; l2=%fmm; d1=%fmm; d2=%fmm'%(R,l1,l2,d1,d2))
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
            printl(s)

        # calculate maximum and integral profiles
        self.calculateProfiles()

        # calculate emittance plot arrays
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
            zz = z[index]
            ymin = min([ymin, yy.min()])
            ymax = max([ymax, yy.max()])
            index = np.unique(yy, return_index=True)[1]
            F0[i] = interp1d(yy[index], -zz[index], kind='linear', bounds_error=False, fill_value=0.0)
        # symmetry for Y range
        if abs(ymin) > abs(ymax) :
            ymax = abs(ymin)
        else:
            ymax = abs(ymax)
        ymin = -ymax
        #print('Ymin=%f; Ymax=%f'%(ymin,ymax))
        # Y range array
        ys = np.linspace(ymin, ymax, N)
        # fill data arrays
        for i in range(nx-1) :
            X0[:,i] = x0[i]
            Y0[:,i] = ys
            Z0[:,i] = F0[i](Y0[:,i])
        # remove negative data
        Z0[Z0 < 0.0] = 0.0
        #Z0t = integrate2d(X0,Y0,Z0) * l2/d2/1000.0 * d1/a1/1000.0
        #print('Total Z0i (cross-section current) = %f mA'%Z0t)
        #Z0t = np.sum(Z0) * (Y0[1,0]-Y0[0,0])/d2*l2/1000.0 * (X0[0,1]-X0[0,0])*d1/a1/1000.0
        #print('Total Z0 (cross-section current) = %f mA'%Z0t)
        #if int(self.comboBox.currentIndex()) == 6:
        #    self.clearPicture()
        #    axes.contour(X0, Y0, Z0)
        #    axes.grid(True)
        #    axes.set_title('Z0 [N,nx-1]')
        #    self.mplWidget.canvas.draw()
        #    #return
        
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
        #Z1t = np.sum(Z1) * (Y1[1,0]-Y1[0,0])/d2*l2/1000.0 * (X1[0,1]-X1[0,0])*d1/a1/1000.0
        #print('Total Z1 (cross-section current) = %f mA'%Z1t)
        # debug draw 6
        #if int(self.comboBox.currentIndex()) == 6:
        #    self.clearPicture()
        #    axes.contour(X1, Y1, Z1)
        #    axes.grid(True)
        #    axes.set_title('Z1 [N,nx-1]')
        #    self.mplWidget.canvas.draw()
        #    #return
        
        # X1,Y1,Z1 -> X2,Y2,Z2 remove average X
        Z1t = integrate2d(X1,Y1,Z1)
        X1avg = integrate2d(X1,Y1,X1*Z1)/Z1t
        Z2 = Z1
        X2 = X1.copy() - X1avg
        Y2 = Y1
        #Z2t = np.sum(Z2) * (Y2[1,0]-Y2[0,0])*l2/d2/1000.0 * (X2[0,1]-X2[0,0])*d1/a1/1000.0
        Z2t = integrate2d(X2,Y2,Z2) * l2/d2 * d1/a1
        print('Total Z2 (cross-section current) = %f mA'%(Z2t*1000.0)) # from Amperes to mA
        # debug plot 6
        if int(self.comboBox.currentIndex()) == 6:
            self.clearPicture()
            axes.contour(X2, Y2, Z2)
            axes.grid(True)
            axes.set_title('Z2 [N,nx-1]')
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
            Shift[i] = Y2[imax,i]
            Z3[:,i] = F1[i](Y2[:,i] + Shift[i])
        # remove negative data
        Z3[Z3 < 0.0] = 0.0
        Z3t = integrate2d(X3,Y3,Z3) * l2/d2 * d1/a1
        print('Total Z3 (cross-section current) = %f mA'%(Z3t*1000.0))
        # debug draw 7
        if int(self.comboBox.currentIndex()) == 7:
            self.clearPicture()
            axes.contour(X3, Y3, Z3)
            axes.grid(True)
            axes.set_title('Z3 [N,nx-1] Regular divergence reduced')
            self.mplWidget.canvas.draw()
            return
        # debug draw 13
        if int(self.comboBox.currentIndex()) == 13:
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
        s = np.zeros((N,1), dtype=np.float64)
        r = np.abs(X3[0,:])
        for i in range(nx-1) :
            s[:] = 0.0
            x = np.abs(X3[0,i])
            xx = x*x
            dd1 = r < x
            dd2 = r > x
            ra = r[dd2]
            m = ra/np.sqrt(ra*ra - xx)
            for j in range(N) :
                f = Z3[j,:].copy()
                f[dd1] = 0.0
                f[dd2] = Z3[j,dd2]*m
                Z4[j,i] = trapz(f,X3[0,:])
        # convert Z to milliAmperes/cell
        #Z4t = np.sum(Z4)*(Y4[1,0]-Y4[0,0])*l2/d2 * (X4[0,1]-X4[0,0])/a1
        Z4t = integrate2d(X4,Y4,Z4) * (l2/d2) / a1
        print('Total Z4 (beam current) = %f mA'%(Z4t*1e3))
        if int(self.comboBox.currentIndex()) == 8:
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
            ymax = abs(xmin)
        else:
            xmax = abs(xmax)
        xmin = -xmax
        xs = np.linspace(xmin, xmax, N)
        # X and Y
        for i in range(N) :
            X5[i,:] = xs
            Y5[:,i] = ys
        if False:
            # Z3 new interpolation
            for i in range(N-2) :
                fnx1 = float(i) * float(nx-2) / float(N-1)
                nx1 = int(fnx1)
                dnx = fnx1 - float(nx1)
                if dnx > 1.0 : print (i,dnx)
                nx2 = nx1 + 1
                #x1 = X0[0,nx1]
                #x2 = X0[0,nx2]
                ny1 = np.argmax(Z1[:,nx1])
                ny2 = np.argmax(Z1[:,nx2])
                #1 = Y1[0,ny1]
                #y2 = Y1[0,ny2]
                dny = ny2 - ny1
                dn = int(dnx * dny)
                for i1 in range(N-1) :
                    try:
                        z1 = Z1[i1-dn,nx1]
                        z2 = Z1[i1-dn+dny,nx2]
                        Z3[i1,i] = z1 + (z2-z1)*dnx
                    except :
                        Z3[i1,i] = 0.0
            # copy last column
            Z3[:,-1] = Z1[:,-1]
            # remove negative currents
            Z3[Z3 < 0.0] = 0.0
            ZZ3 = gaussian_filter(Z3, 1.0)
            Z3t = np.sum(Z3) * (Y3[1,0]-Y3[0,0])/d2*l2/1000.0 * (X3[0,1]-X3[0,0])*d1/a1/1000.0
            print('Total Z3 (cross-section current) nr = %f mA'%Z3t)
            if int(self.comboBox.currentIndex()) == 114:
                self.clearPicture()
                axes.contour(X3, Y3, ZZ3)
                axes.grid(True)
                axes.set_title('[N,N] new resample')
                self.mplWidget.canvas.draw()
                return
        for i in range(N-1) :
            x = X4[i,:]
            z = Z4[i,:]
            index = np.unique(x, return_index=True)[1]
            f = interp1d(x[index], z[index], kind='linear', bounds_error=False, fill_value=0.0)
            Z5[i,:] = f(X5[i,:])
        # remove negative currents
        Z5[Z5 < 0.0] = 0.0
        Z5t = integrate2d(X5,Y5,Z5) * (l2/d2) * 1.0/a1
        #Z5t = np.sum(Z3) * (Y3[1,0]-Y3[0,0])/d2*l2/1000.0 * (X3[0,1]-X3[0,0])*d1/a1/1000.0
        print('Total Z5 (beam current) = %f mA'%(Z5t*1e3))
        # debug plot 14
        if int(self.comboBox.currentIndex()) == 14:
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
        for i in range(N) :
            y = Y5[:,i]
            z = Z5[:,i]
            index = np.unique(y, return_index=True)[1]
            f = interp1d(y[index], z[index], kind='linear', bounds_error=False, fill_value=0.0)
            fnx1 = float(i) * float(nx-2) / float(N-1)
            nx1 = int(fnx1 + 1.0e-7)
            dnx = fnx1 - float(nx1)
            nx2 = nx1 + 1
            if nx2 > nx-2:
                nx2 = nx1
            s1 = Shift[nx1]
            s2 = Shift[nx2]
            s = s1 + (s2-s1)*dnx
            #print(nx1,nx2,s1,s2,s,dnx)
            Z6[:,i] = f(Y5[:,i] - s)
        Z6[Z6 < 0.0] = 0.0
        # debug plot 15
        if int(self.comboBox.currentIndex()) == 16:
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
        printl('Beam energy U= %f V'%U)
        beta = np.sqrt(2.0*q*U/m)/c
        # RMS Emittance
        # calculate average X and X'
        X = X6
        Y = Y6
        Z = Z6 * (l2/d2) * 1.0/a1 # [A/mm/Radian]
        Zt = integrate2d(X,Y,Z)
        Xavg = integrate2d(X,Y,X*Z)/Zt
        Yavg = integrate2d(X,Y,Y*Z)/Zt
        # subtract average values 
        X = X - Xavg
        Y = Y - Yavg
        # calculate moments 
        XYavg = integrate2d(X,Y,X*Y*Z)/Zt
        XXavg = integrate2d(X,Y,X*X*Z)/Zt
        YYavg = integrate2d(X,Y,Y*Y*Z)/Zt
        RMS = np.sqrt(XXavg*YYavg-XYavg*XYavg)*1000.0 # from Radians to milliRadians
        #print('Xavg=%f mm   X\'avg=%f mRad'%(Xavg, Yavg))
        printl('Normalized RMS Emittance %f Pi*mm*mrad'%(RMS*beta))

        # save data to text file
        folder = self.folderName
        fn = os.path.join(str(folder), _progName + '_X.gz')
        np.savetxt(fn, X, delimiter='; ' )
        fn = os.path.join(str(folder), _progName + '_Y.gz')
        np.savetxt(fn, Y, delimiter='; ' )
        fn = os.path.join(str(folder), _progName + '_Z.gz')
        np.savetxt(fn, Z, delimiter='; ' )
        fn = os.path.join(str(folder), _progName + '_X_cs.gz')
        np.savetxt(fn, X2, delimiter='; ' )
        fn = os.path.join(str(folder), _progName + '_Y_cs.gz')
        np.savetxt(fn, Y2, delimiter='; ' )
        fn = os.path.join(str(folder), _progName + '_Z_cs.gz')
        np.savetxt(fn, Z2 * l2/d2 * d1/a1, delimiter='; ' )

        nz = 100
        zl = np.linspace(0.0, Z.max(), nz)
        zi = np.zeros(nz)
        zn = np.zeros(nz)
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
            #print(xxs*yys-xys*xys)
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
        printl('% Current  Normalized emittance      Normalized RMS emittance')
        for i in range(len(levels)):
            printl('%2.0f %%       %5.3f Pi*mm*milliRadians  %5.3f Pi*mm*milliRadians'%(fractions[i]*100.0, emit[i], rms[i]))
        printl('%2.0f %%                                %5.3f Pi*mm*milliRadians'%(100.0, RMS*beta))
        # plot contours
        if int(self.comboBox.currentIndex()) == 2:
            self.clearPicture()
            axes.contour(X, Y, Z, linewidths=1.0)
            axes.grid(True)
            axes.set_title('Emittance contour plot')
            #axes.set_ylim([ymin,ymax])
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Normalized RMS Emittance %5.3f Pi*mm*mrad'%(RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()
        # plot filled contours
        if int(self.comboBox.currentIndex()) == 3:
            self.clearPicture()
            axes.contourf(X, Y, Z)
            axes.grid(True)
            axes.set_title('Emittance color plot')
            #axes.set_ylim([ymin,ymax])
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Normalized RMS Emittance %5.3f Pi*mm*mrad'%(RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11, color='white')
            self.mplWidget.canvas.draw()
            return
        # plot levels
        if int(self.comboBox.currentIndex()) == 4:
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
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Normalized RMS Emittance %5.3f Pi*mm*mrad'%(RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()
            return
        if int(self.comboBox.currentIndex()) == 15:
            self.clearPicture()
            axes.contour(X2, Y2, Z2, linewidths=1.0)
            axes.grid(True)
            axes.set_title('Emittance of cross-section contour plot')
            axes.set_xlabel('X, mm')
            axes.set_ylabel('X\', milliRadians')
            axes.annotate('Total current %4.1f mA'%(self.I*1000.0) + '; Normalized RMS Emittance %5.3f Pi*mm*mrad'%(RMS*beta),
                          xy=(.5, .2), xycoords='figure fraction',
                          horizontalalignment='center', verticalalignment='top',
                          fontsize=11)
            self.mplWidget.canvas.draw()
        
    def saveSettings(self, folder='', fileName=_settingsFile, local=False) :
        fullName = os.path.join(str(folder), fileName)
        dbase = shelve.open(fullName, flag='n')
        # data folder
        dbase['folder'] = self.folderName
        # default smooth
        dbase['smooth'] = int(self.spinBox.value())
        # scan voltage channel number
        dbase['scan'] = int(self.spinBox_2.value())
        # result combo
        dbase['result'] = int(self.comboBox.currentIndex())
        comboitems = [self.comboBox_2.itemText(count) for count in range(self.comboBox_2.count())]
        if len(comboitems) > 10 :
            comboitems = comboitems[:10]
        dbase['history'] = comboitems
        # save paramsAuto
        dbase['paramsAuto'] = self.paramsAuto
        dbase.close()
        print('Configuration saved to %s'%fullName)
        return True
   
    def restoreSettings(self, folder='', fileName=_settingsFile, local=False) :
        # execute init script
        self.execInitScript(folder)
        # read saved settings
        try :
            fullName = os.path.join(str(folder), fileName)
            dbase = shelve.open(fullName)
            # smooth
            self.spinBox.setValue(dbase['smooth'])
            # result comboBox
            self.comboBox.setCurrentIndex(dbase['result'])
            # scan voltage channel number
            self.spinBox_2.setValue(dbase['scan'])
            # restore paramsAuto
            self.paramsAuto = dbase['paramsAuto']
            # global settings
            if not local :
                # data folder
                self.folderName = dbase['folder']
                # history
                self.comboBox_2.currentIndexChanged.disconnect(self.selectionChanged)
                self.comboBox_2.clear()
                self.comboBox_2.addItems(dbase['history'])
                # add dataFolder to history
                i = self.comboBox_2.findText(self.folderName)
                if i >= 0:
                    self.comboBox_2.setCurrentIndex(i)
                else:
                    # add item to history  
                    self.comboBox_2.insertItem(-1, self.folderName)
                    self.comboBox_2.setCurrentIndex(0)
                self.comboBox_2.currentIndexChanged.connect(self.selectionChanged)
            # print OK message and exit    
            print('Configuration restored from %s.'%fullName)
            return True
        except :
            # print error info    
            self.printExceptionInfo()
            print('Configuration file %s restore error.'%fullName)
        finally:
            if hasattr(printl, "dbase"):
                dbase.close()
        return False

    def execInitScript(self, folder=None, fileName=_initScript):
        if folder is None :
            folder = self.folderName
        try:
            fullName = os.path.join(str(folder), fileName)
            exec(open(fullName).read(), globals(), locals())
            print('Init script %s executed'%fullName)
        except:
            self.printExceptionInfo()
            print('Init script %s error.'%fullName)

    def printExceptionInfo(self):
        (tp, value) = sys.exc_info()[:2]
        print('Exception %s %s'%(str(tp), str(value)))

if __name__ == '__main__':
    # create the GUI application
    app = QApplication(sys.argv)
    # instantiate the main window
    dmw = DesignerMainWindow()
    app.aboutToQuit.connect(dmw.onQuit)
    # show it
    dmw.show()
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())