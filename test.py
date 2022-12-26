# coding: utf-8
import sys
import time



def countdown(n):
    print("Counting down from", n)
    while n >= 0:
        newvalue = (yield n)
        # If a new value got sent in, reset n with it
        if newvalue is not None:
            n = newvalue
        else:
            n -= 1

c = countdown(5)
for n in c:
    print(n)
    if n == 5:
        c.send(3)

from PySide6.QtWidgets import QApplication, QWidget

# Only needed for access to command line arguments
import sys

# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.
app = QApplication(sys.argv)

# Create a Qt widget, which will be our window.
window = QWidget()
window.show()  # IMPORTANT!!!!! Windows are hidden by default.

# Start the event loop.
app.exec_()

# Your application won't reach here until you exit and the event
# loop has stopped.

import PySide6
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import QLineSeries, QChart, QCategoryAxis, QChartView
# from PySide6.QtChart import QChart, QChartView, QLineSeries, QCategoryAxis
from PySide6.QtCore import QPoint
# from PySide6.Qt import QPen, QFont, Qt, QSize
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QGradient, QPainter, QPen, QFont, Qt

import numpy as np

class MyChart(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Chart Formatting Demo')
        self.resize(1200, 800)

        t_0 = time.time()
        self.initChart()

        self.setCentralWidget(self.chartView)

        print('Chart', time.time() - t_0, 's')

    def initChart(self):
        series = QLineSeries()

        data = [
            QPoint(0, 6),
            QPoint(9, 4),
            QPoint(15, 20),
            QPoint(18, 12),
            QPoint(28, 25)
        ]

        N = 1000000
        data = np.random.random(N)
        datay = np.random.random(N)
        for i in range(N):
            series.append(datay[i], data[i])

        # creating chart object
        chart = QChart()
        chart.legend().hide()
        chart.addSeries(series)

        pen = QPen(QColor(1, 1, 1))
        pen.setWidth(1)
        series.setPen(pen)

        font = QFont('Open Sans')
        font.setPixelSize(40)
        font.setBold(True)
        chart.setTitleFont(font)
        chart.setTitleBrush(QBrush(Qt.black))
        chart.setTitle('Custom Chart Demo')

        # backgroundGradient = QLinearGradient()
        # backgroundGradient.setStart(QPoint(0, 0))
        # backgroundGradient.setFinalStop(QPoint(0, 1))
        # backgroundGradient.setColorAt(0.0, QColor(175, 201, 182))
        # backgroundGradient.setColorAt(1.0, QColor(51, 105, 66))
        # backgroundGradient.setCoordinateMode(QGradient.ObjectBoundingMode)
        # chart.setBackgroundBrush(backgroundGradient)

        # plotAreaGraident = QLinearGradient()
        # plotAreaGraident.setStart(QPoint(0, 1))
        # plotAreaGraident.setFinalStop(QPoint(1, 0))
        # plotAreaGraident.setColorAt(0.0, QColor(222, 222, 222))
        # plotAreaGraident.setColorAt(1.0, QColor(51, 105, 66))
        # plotAreaGraident.setCoordinateMode(QGradient.ObjectBoundingMode)
        # chart.setPlotAreaBackgroundBrush(plotAreaGraident)
        # chart.setPlotAreaBackgroundVisible(True)

        # customize axis
        axisX = QCategoryAxis()
        axisY = QCategoryAxis()

        labelFont = QFont('Open Sans')
        labelFont.setPixelSize(25)

        axisX.setLabelsFont(labelFont)
        axisY.setLabelsFont(labelFont)

        axisPen = QPen(Qt.black)
        axisPen.setWidth(2)

        axisX.setLinePen(axisPen)
        axisY.setLinePen(axisPen)

        axixBrush = QBrush(Qt.black)
        axisX.setLabelsBrush(axixBrush)
        axisY.setLabelsBrush(axixBrush)

        axisX.setRange(0, 1)
        # axisX.append('low', 10)
        # axisX.append('medium', 20)
        # axisX.append('high', 30)

        # axisY.setRange(0, 30)
        # axisY.append('slow', 10)
        # axisY.append('average', 20)
        # axisY.append('fast', 30)

        # axisX.setGridLineVisible(False)
        # axisY.setGridLineVisible(False)

        chart.addAxis(axisX, Qt.AlignBottom)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        self.chartView = QChartView(chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    t0 = time.time()
    chartDemo = MyChart()
    chartDemo.show()
    print('Show', time.time() - t0, 's')

    stat = app.exec_()
    print('Total', time.time() - t0, 's')
    sys.exit(stat)