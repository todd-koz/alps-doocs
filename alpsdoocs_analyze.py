from PyQt5.QtWidgets import (QPushButton, QWidget, QLabel, QLineEdit,
    QTextEdit, QCheckBox, QComboBox, QSizePolicy,
    QGridLayout, QApplication, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox)
from PyQt5 import QtGui
import pyqtgraph as pg

import sys
import time
from datetime import datetime, timedelta
from threading import Thread
from scipy import signal

#from alpsdoocslib import get_doocs_data

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
        self.plotWidget.setLabel('bottom', 'Frequency [Hz]', units='s', size='40pt')
        self.plotWidget.setLabel('left', 'Power [Calibrated Units^2]', size ="40pt")
        self.plotWidget.setLogMode(True, True)
        self.plotWidget.showGrid(True, True, alpha=1.0)
        self.plotWidget.getAxis("bottom").tickFont = font
        self.plotWidget.getAxis("left").tickFont = font
        self.plotWidget.enableAutoRange()

        self.labelChannels = QLabel('Channels:')
        self.labelTimebase = QLabel('Timebase (s):')
        self.labelAveraging = QLabel('Averaging:')
        self.labelWindow = QLabel('Window:')
        self.labelScaling = QLabel('Scaling:')

        self.comboBoxChannelMenu = QComboBox(self)
        self.comboBoxChannelMenu.addItems(self.channelOptions)

        self.lineEditTimebase = QLineEdit(self)
        self.lineEditTimebase.setText('1')

        self.lineEditAveraging = QLineEdit(self)
        self.lineEditAveraging.setText('1')

        self.comboBoxWindow = QComboBox(self)
        self.comboBoxWindow.addItems(self.windowOptions)
        self.comboBoxWindow.setCurrentText('hann')
        self.comboBoxScaling = QComboBox(self)
        self.comboBoxScaling.addItems(['spectrum (V^2)', 'density (V^2/Hz)'])

        self.comboBoxChannelMenu.currentTextChanged.connect(self.clearBuffer)
        self.lineEditTimebase.textEdited.connect(self.clearBuffer)
        self.lineEditAveraging.textEdited.connect(self.clearBuffer)

        self.buttonStart = QPushButton('Start Plot', self)
        self.buttonStart.clicked.connect(self.startClick)
        self.buttonStop = QPushButton('Stop Plot', self)
        self.buttonStop.clicked.connect(self.stopClick)

        hboxMain = QHBoxLayout()
        vboxSettings = QVBoxLayout()

        hboxChannels = QHBoxLayout()
        hboxChannels.addWidget(self.labelChannels)
        hboxChannels.addWidget(self.comboBoxChannelMenu)
        vboxSettings.addLayout(hboxChannels)

        hboxTimebase = QHBoxLayout()
        hboxTimebase.addWidget(self.labelTimebase)
        hboxTimebase.addStretch()
        hboxTimebase.addWidget(self.lineEditTimebase)
        vboxSettings.addLayout(hboxTimebase)

        hboxAveraging = QHBoxLayout()
        hboxAveraging.addWidget(self.labelAveraging)
        hboxAveraging.addStretch()
        hboxAveraging.addWidget(self.lineEditAveraging)
        vboxSettings.addLayout(hboxAveraging)

        hboxWindow = QHBoxLayout()
        hboxWindow.addWidget(self.labelWindow)
        hboxWindow.addWidget(self.comboBoxWindow)
        vboxSettings.addLayout(hboxWindow)

        hboxScaling = QHBoxLayout()
        hboxScaling.addWidget(self.labelScaling)
        hboxScaling.addWidget(self.comboBoxScaling)
        vboxSettings.addLayout(hboxScaling)

        vboxSettings.addSpacing(20)

        hboxButtons = QHBoxLayout()
        hboxButtons.addStretch()
        hboxButtons.addWidget(self.buttonStart)
        hboxButtons.addWidget(self.buttonStop)
        hboxButtons.addStretch()
        vboxSettings.addLayout(hboxButtons)
        vboxSettings.addStretch()

        hboxMain.addLayout(vboxSettings)
        hboxMain.addWidget(self.plotWidget, 5)

        self.setLayout(hboxMain)
        self.setWindowTitle('Spectrum Plot')
        self.setGeometry(100, 100, 1280, 720)

    def stopClick(self):
        self.interrupt = True

    def startClick(self):
        self.interrupt = False
        getDataThread = Thread(target=self.getData)
        getDataThread.start()
        plotSpecThread = Thread(target=self.plotSpec)
        plotSpecThread.start()

    def clearBuffer(self):
        self.buffer.clear()

    def getData(self):
        prevTime = None
        while not self.interrupt:
            stop_dt = datetime.now()
            try:
                averaging = int(self.lineEditAveraging.text())
            except:
                averaging = 1
            duration_dt = timedelta(seconds=int(self.lineEditTimebase.text())) * averaging

            if not prevTime == None:
                if prevTime > stop_dt - duration_dt:
                    waitTime = (prevTime-(stop_dt-duration_dt)).seconds
                    time.sleep(waitTime)
                    continue

            timebase = duration_dt.seconds
            channel = self.baseAdr + self.comboBoxChannelMenu.currentText()

            start_dt = stop_dt - timebase
            start = start_dt.strftime('%Y-%m-%dT%H:%M:%S')
            stop = stop_dt.strftime('%Y-%m-%dT%H:%M:%S')

            result = get_doocs_data([channel], start, stop)
            if not isinstance(result, Exception):
                window = self.comboBoxWindow.currentText()
                scaling = self.comboBoxScaling.currentText()
                self.buffer.append( {'data':result[0][0], 'averaging':averaging, 'window':window, 'scaling':scaling} )

            prevTime = stop_dt

    def plotSpec(self):
        while not self.interrupt:
            if len(self.buffer) > 1:
                next = self.buffer[0]
                self.buffer.pop(0)

                freqs, spec = signal.periodogram(next['data'], 16000, window=next['window'], scaling=next['scaling'],
                                                 nperseg=len(next['data'])/next['averaging'])

                self.plotWidget.clear()
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
