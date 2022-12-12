from PyQt5 import QtGui
from PyQt5.QtGui import QFont

_l0 = locals().copy()
ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'Plotter for Signals from Dumper'
APPLICATION_NAME_SHORT = 'LoggerPlotterPy'
APPLICATION_VERSION = '11.1'
VERSION_DATE = "12-12-2022"
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'
# fonts
CELL_FONT = QFont('Open Sans', 14)
CELL_FONT_BOLD = QFont('Open Sans', 14, weight=QFont.Bold)
STATUS_BAR_FONT = CELL_FONT
CLOCK_FONT = CELL_FONT_BOLD
# colors
WHITE = QtGui.QColor(255, 255, 255)
YELLOW = QtGui.QColor(255, 255, 0)
GREEN = QtGui.QColor(0, 255, 0)
PREVIOUS_COLOR = '#ffff00'
TRACE_COLOR = '#00ff00'
MARK_COLOR = '#ff0000'
ZERO_COLOR = '#0000ff'

_l1 = locals().copy()
l2 = _l1.pop('_l0')
l3 = {x for x in l2 if x not in _l0}
