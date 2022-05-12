from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QComboBox,
    QApplication, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5 import QtGui
import pyqtgraph as pg

import sys
import time
from datetime import datetime, timedelta
from traceback import format_exc

from scipy import signal
import numpy as np

import pydoocs

pg.setConfigOption('background', 'w') # Standard (white)

class PlotWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    plotsignal = pyqtSignal(list)

    def __init__(self, parent, channel, duration, calibration, averaging, window, scaling):
        super().__init__()
        self.parent = parent

        self.channel = channel
        self.duration = duration
        self.calibration = calibration
        self.averaging = averaging
        self.window = window
        self.scaling = scaling

    def run(self):
        batch = 0
        goal = int(self.duration * 32)
        while not self.parent.interrupt:
            data = []
            batch += 1
            cycles = 1
            try:
                output = pydoocs.read(self.channel)
                pulse_initial = output['macropulse']
                pulse = pulse_initial
                data.append(output['data'][:,1])

                while cycles < goal:
                    output = pydoocs.read(self.channel)
                    if output['macropulse'] == pulse:
                        continue
                    else:
                        cycles += 1
                        pulse = output['macropulse']
                        data.append( output['data'][:,1] )

                data = np.reshape(data, (500*goal,))

                calibrated_data = data * self.calibration

                freqs, ps = signal.welch(calibrated_data, 16000,
                                         window=self.window, scaling=self.scaling,
                                         nperseg=len(calibrated_data)/self.averaging)

                self.plotsignal.emit([batch,freqs,ps])
                self.progress.emit(f"Batch #{batch}\nMacropulse span: {pulse-pulse_initial}")

            except:
                summary = format_exc()
                self.progress.emit(f"Batch #{batch}\n"+summary)

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

    decimationVal = {
        "16 kHz": 16000,
        "8 kHz": 8000,
        "4 kHz": 4000,
        "2 kHz": 2000,
        "1 kHz": 1000,
        "500 Hz": 500,
        "100 Hz": 100,
        "64 Hz": 64,
        "32 Hz": 32 }

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

        self.initUI()

    def initUI(self):
        font = QtGui.QFont()
        font.setPixelSize(25)

        self.plotWidget = pg.PlotWidget()
        self.plotCurve = self.plotWidget.plot()
        self.plotCurve.setPen(color=(0,33,165))    # UF blue
        self.plotWidget.setLabel('bottom', 'Frequency', units='Hz', size='40pt')
        self.plotWidget.setLabel('left', 'Power', units='units^2', size ="40pt")
        self.plotWidget.setLogMode(True, True)
        self.plotWidget.showGrid(True, True, alpha=1.0)
        self.plotWidget.getAxis("bottom").tickFont = font
        self.plotWidget.getAxis("left").tickFont = font
        self.plotWidget.enableAutoRange()

        self.labelChannels = QLabel('Channels:')
        self.labelCalibration = QLabel('Calibration Factor:')
        self.labelTimebase = QLabel('Timebase (s):')
        self.labelAveraging = QLabel('Averaging:')
        self.labelWindow = QLabel('Window:')
        self.labelScaling = QLabel('Scaling:')

        self.comboBoxChannelMenu = QComboBox(self)
        self.comboBoxChannelMenu.addItems(self.channelOptions)

        self.lineEditCalibration = QLineEdit(self)
        self.lineEditCalibration.setText('8.1e-4')

        self.lineEditTimebase = QLineEdit(self)
        self.lineEditTimebase.setText('1')

        self.lineEditAveraging = QLineEdit(self)
        self.lineEditAveraging.setText('1')

        self.comboBoxWindow = QComboBox(self)
        self.comboBoxWindow.addItems(self.windowOptions)
        self.comboBoxWindow.setCurrentText('hann')

        self.comboBoxScaling = QComboBox(self)
        self.comboBoxScaling.addItems(['spectrum', 'density'])

        self.buttonStart = QPushButton('Start Plot', self)
        self.buttonStart.clicked.connect(self.startClick)
        self.buttonStop = QPushButton('Stop Plot', self)
        self.buttonStop.clicked.connect(self.stopClick)

        self.textEditConsole = QTextEdit(self)
        self.textEditConsole.setReadOnly(True)

        hboxMain = QHBoxLayout()
        vboxLeftPane = QVBoxLayout()
        hboxSettings = QHBoxLayout()

        vboxLabels = QVBoxLayout()
        vboxFields = QVBoxLayout()

        vboxLabels.addWidget(self.labelChannels)
        vboxLabels.addWidget(self.labelCalibration)
        vboxLabels.addWidget(self.labelTimebase)
        vboxLabels.addWidget(self.labelAveraging)
        vboxLabels.addWidget(self.labelWindow)
        vboxLabels.addWidget(self.labelScaling)

        vboxFields.addWidget(self.comboBoxChannelMenu)
        vboxFields.addWidget(self.lineEditCalibration)
        vboxFields.addWidget(self.lineEditTimebase)
        vboxFields.addWidget(self.lineEditAveraging)
        vboxFields.addWidget(self.comboBoxWindow)
        vboxFields.addWidget(self.comboBoxScaling)

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
        self.comboBoxChannelMenu.setEnabled(enabled)
        self.lineEditCalibration.setEnabled(enabled)
        self.lineEditTimebase.setEnabled(enabled)
        self.lineEditAveraging.setEnabled(enabled)
        self.comboBoxWindow.setEnabled(enabled)
        self.comboBoxScaling.setEnabled(enabled)

    def print(self, *text):
        self.textEditConsole.clear()
        for t in text:
            self.textEditConsole.insertPlainText(str(t)+' ')

    @pyqtSlot(str)
    def dataProgress(self, report):
        self.print(report)

    def stopClick(self):
        self.interrupt = True

    def startClick(self):
        self.interrupt = False
        self.setEnableSettings(False)

        channel = self.baseAdr + self.comboBoxChannelMenu.currentText() + '/CH00.TD'
        averaging = int(self.lineEditAveraging.text())
        timebase = float(self.lineEditTimebase.text())

        calibration = float(self.lineEditCalibration.text())
        window = self.comboBoxWindow.currentText()
        scaling = self.comboBoxScaling.currentText()

        duration = timebase * averaging

        self.plotWorker = PlotWorker(self, channel, duration, calibration, averaging, window, scaling)
        self.plotThread = QThread()
        self.plotWorker.moveToThread(self.plotThread)
        self.plotThread.started.connect(self.plotWorker.run)
        self.plotWorker.finished.connect(self.plotThread.quit)
        self.plotWorker.finished.connect(self.plotWorker.deleteLater)
        self.plotThread.finished.connect(self.plotThread.deleteLater)
        self.plotWorker.progress.connect(self.dataProgress)
        self.plotWorker.plotsignal.connect(self.updatePlot)

        self.plotThread.start()
        self.setEnableSettings(False)

        self.plotThread.finished.connect(lambda : self.setEnableSettings(True))

    @pyqtSlot(list)
    def updatePlot(self, plotDataList):
        batch, freqs, ps = plotDataList

        self.plotWidget.setLabel('top', f'Power Spectrum - Batch {batch}')
        self.plotCurve.setData(freqs, ps)
        pg.Qt.QtGui.QApplication.processEvents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    plotwindow = SpectrumPlot()
    plotwindow.show()
    sys.exit(app.exec_())
