from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QComboBox,
    QApplication, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5 import QtGui
import pyqtgraph as pg

import sys
import time
from datetime import datetime, timedelta
from traceback import format_exc
from collections import deque

from scipy import signal
import numpy as np

import pydoocs

UNITS_TIP = """\
(Optional)
Sets units to display on plot's y-axis label.
If blank, none will display.\
"""

FREQ_RES_TIP = """\
Must be no greater than 32 Hz.

Upon each request for data, DOOCS sends 500 samples
corresponding to the latest 'macropulse' event. Thus,
the total measurement time for a spectrum must be an
integer multiple of 500 samples, or 0.03125 seconds.
Equivalently, the requested frequency resolution will
be discretized to (32/N) Hz, for some integer N >= 1.\
"""

AVERAGING_TIP = """\
The measurement time set by the frequency resolution
above will be multiplied by the averaging. The length
of a segment of data for a single spectrum is the
total length divided by the averaging. No overlap
between segments is used.\
"""

UPDATE_TIME_TIP = """\
Time between the display of the next spectrum plot.
Requesting update times significantly below 1 second
is not guaranteed to be fulfilled.\
"""

pg.setConfigOption('background', 'w') # Standard (white)

class CalcSpecWorker(QObject):
    finished = pyqtSignal()
    plotsignal = pyqtSignal(tuple)
    report = pyqtSignal(str)

    def __init__(self, parent, cycles, calibration, averaging, window, scaling, buffer):
        super().__init__()
        self.parent = parent
        self.cycles = cycles
        self.calibration = calibration
        self.averaging = averaging
        self.window = window
        self.scaling = scaling
        self.buffer = buffer

    def calc(self):
        if not self.parent.interrupt:
            if self.cycles == len(self.buffer):
                data = np.ravel(self.buffer)
                calibrated_data = data * self.calibration
                out = signal.welch(calibrated_data, 16000, window=self.window, scaling=self.scaling,
                                   nperseg=len(calibrated_data)/self.averaging, noverlap=0)
                self.plotsignal.emit(out)
        else:
            self.finished.emit()

    def run(self):
        self.parent.timer.timeout.connect(self.calc)

class GetDataWorker(QObject):
    finished = pyqtSignal()
    report = pyqtSignal(str)

    def __init__(self, parent, channel, buffer, cycles):
        super().__init__()
        self.parent = parent
        self.channel = channel
        self.buffer = buffer
        self.cycles = cycles

    def run(self):
        try:
            pulse = 0
            while not self.parent.interrupt:
                output = pydoocs.read(self.channel)
                if output['macropulse'] == pulse:
                    continue
                else:
                    pulse = output['macropulse']
                    self.buffer.append( output['data'][:,1] )
        except:
            self.report.emit(format_exc())

        self.finished.emit()

class SpectrumPlot(QWidget):
    channelOptions = [
        'NR/CH_1.00',
        'NR/CH_1.01',
        'NR/CH_1.02',
        'NR/CH_1.03',
        'NR/CH_1.04',
        'NR/CH_1.05',
        'NR/CH_1.06',
        'NR/CH_1.07',
        'NL/CH_1.00',
        'NL/CH_1.01',
        'HN/CH_1.00' ]

    baseAdr = 'ALPS.DIAG/ALPS.ADC.'

    windowOptions = [
        'barthann',
        'bartlett',
        'blackmanharris',
        'bohman',
        'boxcar',
        'cosine',
        'exponential',
        'flattop',
        'hamming',
        'hann',
        'nuttall',
        'parzen',
        'taylor',
        'triang',
        'tukey']

    def __init__(self, parent=None):
        super().__init__()

        self.parent = parent
        self.interrupt = False
        self.buffer = None
        self.timer = QTimer()
        self.timer.setInterval(1000)

        self.initUI()

    def initUI(self):
        font = QtGui.QFont()
        font.setPixelSize(25)

        self.plotWidget = pg.PlotWidget()
        self.plotCurve = self.plotWidget.plot()
        self.plotCurve.setPen(color=(0,33,165))    # UF blue
        self.plotWidget.setLabel('bottom', 'Frequency', units='Hz', size='40pt')
        self.plotWidget.setLabel('left', 'Power', size ="40pt")
        self.plotWidget.setLogMode(True, True)
        self.plotWidget.showGrid(True, True, alpha=1.0)
        self.plotWidget.getAxis("bottom").tickFont = font
        self.plotWidget.getAxis("left").tickFont = font
        self.plotWidget.enableAutoRange()

        self.labelChannels = QLabel('Channels:')
        self.labelCalibration = QLabel('Calibration Factor:')
        self.labelUnits = QLabel('Calibration Units:')
        self.labelFreqRes = QLabel('Frequency Resolution (Hz):')
        self.labelAveraging = QLabel('Averaging:')
        self.labelWindow = QLabel('Window:')
        self.labelScaling = QLabel('Scaling:')
        self.labelUpdate = QLabel('Plot Update Time (s)')

        self.comboBoxChannelMenu = QComboBox(self)
        self.comboBoxChannelMenu.addItems(self.channelOptions)

        self.lineEditCalibration = QLineEdit(self)
        self.lineEditCalibration.setText('8.1e-4')

        self.lineEditUnits = QLineEdit(self)
        self.lineEditUnits.setPlaceholderText('units')
        self.lineEditUnits.setToolTip(UNITS_TIP)

        self.lineEditFreqRes = QLineEdit(self)
        self.lineEditFreqRes.setText('1')
        self.lineEditFreqRes.setToolTip(FREQ_RES_TIP)

        self.lineEditAveraging = QLineEdit(self)
        self.lineEditAveraging.setText('1')
        self.lineEditAveraging.setToolTip(AVERAGING_TIP)

        self.comboBoxWindow = QComboBox(self)
        self.comboBoxWindow.addItems(self.windowOptions)
        self.comboBoxWindow.setCurrentText('hann')

        self.comboBoxScaling = QComboBox(self)
        self.comboBoxScaling.addItems(['spectrum', 'density'])

        self.lineEditUpdate = QLineEdit(self)
        self.lineEditUpdate.setText('1')
        self.lineEditUpdate.setToolTip(UPDATE_TIME_TIP)
        self.lineEditUpdate.editingFinished.connect(self.updatePlotTime)

        self.buttonStart = QPushButton('Start Plot', self)
        self.buttonStart.clicked.connect(self.startClick)
        self.buttonStop = QPushButton('Stop Plot', self)
        self.buttonStop.clicked.connect(self.stopClick)
        self.buttonStop.setEnabled(False)

        self.textEditConsole = QTextEdit(self)
        self.textEditConsole.setReadOnly(True)

        hboxMain = QHBoxLayout()
        vboxLeftPane = QVBoxLayout()
        hboxSettings = QHBoxLayout()

        vboxLabels = QVBoxLayout()
        vboxFields = QVBoxLayout()

        vboxLabels.addWidget(self.labelChannels)
        vboxLabels.addWidget(self.labelCalibration)
        vboxLabels.addWidget(self.labelUnits)
        vboxLabels.addWidget(self.labelFreqRes)
        vboxLabels.addWidget(self.labelAveraging)
        vboxLabels.addWidget(self.labelWindow)
        vboxLabels.addWidget(self.labelScaling)
        vboxLabels.addWidget(self.labelUpdate)

        vboxFields.addWidget(self.comboBoxChannelMenu)
        vboxFields.addWidget(self.lineEditCalibration)
        vboxFields.addWidget(self.lineEditUnits)
        vboxFields.addWidget(self.lineEditFreqRes)
        vboxFields.addWidget(self.lineEditAveraging)
        vboxFields.addWidget(self.comboBoxWindow)
        vboxFields.addWidget(self.comboBoxScaling)
        vboxFields.addWidget(self.lineEditUpdate)

        hboxSettings.addLayout(vboxLabels)
        hboxSettings.addLayout(vboxFields)
        vboxLeftPane.addLayout(hboxSettings)
        vboxLeftPane.addSpacing(20)

        hboxButtons = QHBoxLayout()
        hboxButtons.addStretch()
        hboxButtons.addWidget(self.buttonStart)
        hboxButtons.addWidget(self.buttonStop)
        hboxButtons.addStretch()

        vboxLeftPane.addLayout(hboxButtons)
        vboxLeftPane.addStretch()
        vboxLeftPane.addWidget(self.textEditConsole)

        hboxMain.addLayout(vboxLeftPane)
        hboxMain.addWidget(self.plotWidget, 5)

        self.setLayout(hboxMain)
        self.setWindowTitle('Spectrum Plot')
        self.setGeometry(100, 100, 1280, 720)

    def setEnableSettings(self, enabled):
        self.buttonStop.setEnabled(not enabled)
        self.buttonStart.setEnabled(enabled)
        self.comboBoxChannelMenu.setEnabled(enabled)
        self.lineEditCalibration.setEnabled(enabled)
        self.lineEditUnits.setEnabled(enabled)
        self.lineEditFreqRes.setEnabled(enabled)
        self.lineEditAveraging.setEnabled(enabled)
        self.comboBoxWindow.setEnabled(enabled)
        self.comboBoxScaling.setEnabled(enabled)

    def print(self, *text):
        for t in text:
            self.textEditConsole.insertPlainText(str(t)+' ')
        self.textEditConsole.insertPlainText('\n')

    def updatePlotTime(self):
        updateTime = int(float(self.lineEditUpdate.text())* 1e3)
        self.timer.setInterval(updateTime)

    @pyqtSlot(str)
    def workerReport(self, report):
        self.print(report)

    def stopClick(self):
        self.interrupt = True

    def startClick(self):
        self.interrupt = False
        self.setEnableSettings(False)

        units = self.lineEditUnits.text()
        if not units == '':
            self.plotWidget.setLabel('left', 'Power', units=units, size='40pt')

        channel = self.baseAdr + self.comboBoxChannelMenu.currentText() + '/CH00.TD'
        averaging = int(self.lineEditAveraging.text())
        timebase = 1/float(self.lineEditFreqRes.text())

        calibration = float(self.lineEditCalibration.text())
        window = self.comboBoxWindow.currentText()
        scaling = self.comboBoxScaling.currentText()

        cycles = int(timebase * averaging * 32)

        self.buffer = deque(maxlen=cycles)

        self.getDataWorker = GetDataWorker(self, channel, self.buffer, cycles)
        self.getDataThread = QThread()
        self.getDataWorker.moveToThread(self.getDataThread)
        self.getDataThread.started.connect(self.getDataWorker.run)
        self.getDataWorker.finished.connect(self.getDataThread.quit)
        self.getDataWorker.finished.connect(self.getDataWorker.deleteLater)
        self.getDataThread.finished.connect(self.getDataThread.deleteLater)
        self.getDataWorker.report.connect(self.workerReport)

        self.calcSpecWorker = CalcSpecWorker(self, cycles, calibration, averaging, window, scaling, self.buffer)
        self.calcSpecThread = QThread()
        self.calcSpecWorker.moveToThread(self.calcSpecThread)
        self.calcSpecThread.started.connect(self.calcSpecWorker.run)
        self.calcSpecWorker.finished.connect(self.calcSpecThread.quit)
        self.calcSpecWorker.finished.connect(self.calcSpecWorker.deleteLater)
        self.calcSpecThread.finished.connect(self.calcSpecThread.deleteLater)
        self.calcSpecWorker.report.connect(self.workerReport)
        self.calcSpecWorker.plotsignal.connect(self.updatePlot)

        self.getDataThread.finished.connect(lambda : self.setEnableSettings(True))
        self.calcSpecThread.finished.connect(lambda : self.timer.stop)

        self.setEnableSettings(False)
        self.calcSpecThread.start()
        self.getDataThread.start()
        self.timer.start()

    @pyqtSlot(tuple)
    def updatePlot(self, plotData):
        freqs, ps = plotData
        self.plotCurve.setData(freqs, ps)
        pg.Qt.QtGui.QApplication.processEvents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    plotwindow = SpectrumPlot()
    plotwindow.show()
    sys.exit(app.exec_())
