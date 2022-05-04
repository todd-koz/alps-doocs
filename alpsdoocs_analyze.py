from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QComboBox,
    QApplication, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox)
from PyQt5 import QtGui
import pyqtgraph as pg

import sys
import time
from datetime import datetime, timedelta
from threading import Thread
from scipy import signal

from alpsdoocslib import get_doocs_data

pg.setConfigOption('background', 'w') # Standard (white)

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
        self.buffer = []
        self.initUI()

    def initUI(self):
        font = QtGui.QFont()
        font.setPixelSize(25)

        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setLabel('bottom', 'Frequency', units='Hz', size='40pt')
        self.plotWidget.setLabel('left', 'Power', units='un-calibrated units^2', size ="40pt")
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

    def stopClick(self):
        self.interrupt = True
        self.setEnableSetings(True)

    def startClick(self):
        self.interrupt = False
        self.setEnableSettings(False)

        channel = self.baseAdr + self.comboBoxChannelMenu.currentText()
        averaging = int(self.lineEditAveraging.text())
        timebase = int(self.lineEditTimebase.text())
        duration_dt = timedelta(seconds=timebase) * averaging

        calibration = float(self.lineEditCalibration.text())
        window = self.comboBoxWindow.currentText()
        scaling = self.comboBoxScaling.currentText()

        getDataThread = Thread(target=self.getData, args=(channel, duration_dt))
        getDataThread.start()
        plotSpecThread = Thread(target=self.plotSpec, args=(calibration, averaging, window, scaling))
        plotSpecThread.start()

    def setEnableSettings(self, enabled):
        self.comboBoxChannelMenu.setEnabled(enabled)
        self.lineEditCalibration.setEnabled(enabled)
        self.lineEditTimebase.setEnabled(enabled)
        self.lineEditAveraging.setEnabled(enabled)
        self.comboBoxWindow.setEnabled(enabled)
        self.comboBoxScaling.setEnabled(enabled)

    def getData(self, channel, duration_dt):
        batch = 0
        while not self.interrupt:
            batch += 1

            stop_dt = datetime.now()
            start_dt = stop_dt - duration_dt
            start = start_dt.strftime('%Y-%m-%dT%H:%M:%S')
            stop = stop_dt.strftime('%Y-%m-%dT%H:%M:%S')

            result = get_doocs_data([channel], start, stop)
            if isinstance(result, str):
                self.stopClick()
                self.textEditConsole.setText(result+'\nPlotting stopped.')
            else:
                self.buffer.append( result[0][0] )
                self.textEditConsole.setText('Batch: ' + str(batch) + '\n' + result[1])

    def plotSpec(self, calibration, averaging, window, scaling):
        batch = 0
        while not self.interrupt:
            batch += 1
            if len(self.buffer) > 1:
                calibrated_data = self.buffer[0] * calibration
                self.buffer.pop(0)

                freqs, spec = signal.welch(calibrated_data, 16000, window=window, scaling=scaling,
                                                 nperseg=len(calibrated_data)/averaging)

                self.plotWidget.clear()
                self.plotWidget.setLabel('top', )
                curve1 = self.plotWidget.plot()
                curve1.setPen(color=(0,33,165))    # UF blue
                curve1.setData(freqs, spec)
                pg.Qt.QtGui.QApplication.processEvents()
            else:
                time.sleep(0.1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    plotwindow = SpectrumPlot()
    plotwindow.show()
    sys.exit(app.exec_())
