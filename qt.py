# import sys
#
# try:
#     import PyQt6
#     import PyQt5
#     import PySide6
# except:
#     pass
#
# if 'PyQt6' in sys.modules:
#     # PyQt6
#     PyQt = PyQt6
#     from PyQt6 import QtGui, QtWidgets, QtCore
#     from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
# elif 'PyQt5' in sys.modules:
#     # PyQt5
#     PyQt = PyQt5
#     from PyQt5 import QtGui, QtWidgets, QtCore
#     from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
# elif 'PySide6' in sys.modules:
#     # PySide6
#     PyQt = PySide6
#     from PySide6 import QtGui, QtWidgets, QtCore
#     from PySide6.QtCore import Signal, Slot
# else:
#     raise ModuleNotFoundError('Can not found Qt compatible graphic module')
#
#
# def _enum(obj, name):
#     parent, child = name.split('.')
#     result = getattr(obj, child, False)
#     if result:  # Found using short name only.
#         return result
#     obj = getattr(obj, parent)  # Get parent, then child.
#     return getattr(obj, child)
#
#
# def _exec(obj):
#     if hasattr(obj, 'exec'):
#         return obj.exec()
#     else:
#         return obj.exec_()

# quine
_='_=%r;print(_%%_)';print(_%_)
