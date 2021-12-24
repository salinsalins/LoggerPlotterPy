import sys
import time

import time
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QCategoryAxis
from PyQt5.QtCore import QPoint
from PyQt5.Qt import QPen, QFont, Qt, QSize
from PyQt5.QtGui import QColor, QBrush, QLinearGradient, QGradient, QPainter

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
        for i in range(N):
            series.append(i, data[i])

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

        axixBrush = QBrush(Qt.white)
        axisX.setLabelsBrush(axixBrush)
        axisY.setLabelsBrush(axixBrush)

        axisX.setRange(0, 300)
        # axisX.append('low', 10)
        # axisX.append('medium', 20)
        # axisX.append('high', 30)

        # axisY.setRange(0, 30)
        # axisY.append('slow', 10)
        # axisY.append('average', 20)
        # axisY.append('fast', 30)

        axisX.setGridLineVisible(False)
        axisY.setGridLineVisible(False)

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