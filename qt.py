# _='_=%r;print(_%%_)';print(_%_)
import os
try:
    _ = os.environ['QT_API']
except:
    os.environ['QT_API'] = 'pyside6'
    # os.environ['QT_API'] = 'pyqt6'
print('using', os.environ['QT_API'])

import qtpy

from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from qtpy.QtCore import QPoint
from qtpy.QtCore import QSize
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QComboBox
from qtpy.QtWidgets import QFileDialog
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QMainWindow, QHeaderView, QFrame, QMenu
from qtpy.QtWidgets import QMessageBox
from qtpy.QtWidgets import QTableWidgetItem
