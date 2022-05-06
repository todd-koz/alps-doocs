from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QComboBox,
    QApplication, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5 import QtGui

import sys
import os
import os.path
import time
from datetime import datetime, timedelta
from threading import Thread
from contextlib import ExitStack

from alpsdoocslib import MatWriter, get_doocs_data_continuous, save_mat_subroutine

class ConfigError(Exception):
    pass

class DateError(ConfigError):
    """The measurement end time has not yet been reached. Measurement end must be in the past."""
    pass

class ChannelError(ConfigError):
    """No channels selected or a file name is missing."""
    pass

class SaveMatWorker(QObject):
    finished = pyqtSignal()
    report = pyqtSignal(str)

    def __init__(self, channels, filenames, start, stop, decimationFactor):
        super().__init__()
        self.channels = channels
        self.filenames = filenames
        self.start = start
        self.stop = stop
        self.decimationFactor = decimationFactor
        self.interrupt = False

    @pyqtSlot()
    def interruptListen(self):
        self.interrupt = True

    def run(self):
        with ExitStack() as stack:
            files = [stack.enter_context(open(fname, 'wb')) for fname in self.filenames]
            mat_writers = []

            for i in range(len(files)):
                mat_writers.append( MatWriter(files[i]) )
                mat_writers[i].write_preamble()

            result = get_doocs_data_continuous(self.channels, save_mat_subroutine,
                                            self.start, self.stop,
                                            sub_args=(self.channels, mat_writers, self.decimationFactor),
                                            interrupt=lambda : self.interrupt)

            for i in range(len(mat_writers)):
                mat_writers[i].update_tags()

        if 'Trace' in result or 'Exception' in result or 'Error' in result:
            for f in self.filenames: os.remove(f)

        self.report.emit(res)
        self.finished.emit()

class ChannelSelect(QWidget):
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

    def __init__(self, parent):
        super().__init__()
        self.left = 100
        self.top = 100
        self.width = 500
        self.height = 100
        self.parent = parent
        self.initUI()

    def initUI(self):

        self.labelChannels = QLabel('Channels:')
        self.labelNames = QLabel('File names:')
        self.labelSelection = QLabel('Current selection:')
        self.lineEditSelection = QLineEdit(self)
        self.buttonUpdateSelection = QPushButton('Update Selection', self)
        self.buttonUpdateSelection.clicked.connect(self.updateSelection)

        self.checks = []
        self.names = []

        for i in range(len(self.channelOptions)):
            self.checks.append(QCheckBox(self.channelOptions[i]))
            self.names.append(QLineEdit(self))

        vboxMain = QVBoxLayout()

        hboxLabels = QHBoxLayout()
        hboxLabels.addWidget(self.labelChannels)
        hboxLabels.addStretch()
        hboxLabels.addWidget(self.labelNames)
        hboxLabels.addStretch()
        vboxMain.addLayout(hboxLabels)

        for i in range(len(self.channelOptions)):
            hbox = QHBoxLayout()
            hbox.addWidget(self.checks[i])
            hbox.addWidget(self.names[i])
            vboxMain.addLayout(hbox)

        vboxMain.addStretch()

        hboxButtons = QHBoxLayout()
        hboxButtons.addStretch()
        hboxButtons.addWidget(self.buttonUpdateSelection)
        hboxButtons.addStretch()
        vboxMain.addLayout(hboxButtons)

        vboxMain.addStretch()

        hboxSelection = QHBoxLayout()
        hboxSelection.addWidget(self.labelSelection)
        hboxSelection.addWidget(self.lineEditSelection)
        vboxMain.addLayout(hboxSelection)

        self.setLayout(vboxMain)
        self.setWindowTitle('Select Channels')
        self.setGeometry(self.left, self.top, self.width, self.height)

    def updateSelection(self):
        self.parent.channels.clear()
        self.parent.filenames.clear()

        selectionText = ''
        for i in range(len(self.channelOptions)):
            if self.checks[i].isChecked():
                ch = self.channelOptions[i]
                fname = self.names[i].text()
                self.parent.channels.append(ch)
                self.parent.filenames.append(fname)
                selectionText += f"({ch}:{fname}) "

        self.parent.lineEditChannels.setText(selectionText)
        self.lineEditSelection.setText(selectionText)


class SaveApp(QWidget):
    filetypeOptions = ['.mat', '.csv' ]
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

    interrupt = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.channels = []
        self.filenames = []
        self.windowChannelSelect = None

        self.defineWidgets()
        self.placeWidgets()

    def defineWidgets(self):
        self.labelFiletype = QLabel('Filetype:')
        self.labelDirectory = QLabel('Save directory:')
        self.labelStartDate = QLabel('Start date:')
        self.labelStartTime = QLabel('Start time:')
        self.labelChannels = QLabel('Select channels:')
        self.labelDuration = QLabel('Duration:')
        self.labelDays = QLabel('Days:')
        self.labelHours = QLabel('Hours:')
        self.labelMinutes = QLabel('Minutes:')
        self.labelSeconds = QLabel('Seconds:')
        self.labelDownsample = QLabel('Down-sampling:')
        self.labelComments = QLabel('Additional comments:')

        self.lineEditDirectory = QLineEdit(self)
        self.lineEditDirectory.setPlaceholderText(os.getcwd())
        self.lineEditStartDate = QLineEdit(self)
        self.lineEditStartDate.setPlaceholderText(datetime.now().strftime('%Y-%m-%d'))
        self.lineEditStartTime = QLineEdit(self)
        self.lineEditStartTime.setPlaceholderText(datetime.now().strftime('%H:%M:%S'))
        self.lineEditChannels = QLineEdit(self)
        self.lineEditChannels.setPlaceholderText('NR/CH_1.00:ch1')
        self.lineEditDays = QLineEdit(self)
        self.lineEditDays.setText('0')
        self.lineEditHours = QLineEdit(self)
        self.lineEditHours.setText('0')
        self.lineEditMinutes = QLineEdit(self)
        self.lineEditMinutes.setText('0')
        self.lineEditSeconds = QLineEdit(self)
        self.lineEditSeconds.setText('10')

        self.buttonSelectChannels = QPushButton('Select Channels', self)
        self.buttonSelectChannels.clicked.connect(self.openChannelSelect)
        self.buttonStartSave = QPushButton('Start', self)
        self.buttonStartSave.clicked.connect(self.startSave)
        self.buttonInterrupt = QPushButton('Interrupt', self)
        self.buttonInterrupt.clicked.connect(self.interruptSave)
        self.buttonSelectFolder = QPushButton('Select directory', self)
        self.buttonSelectFolder.clicked.connect(self.openFolderSelect)

        self.comboBoxFiletype = QComboBox(self)
        self.comboBoxFiletype.addItems(self.filetypeOptions)
        self.comboBoxDownsample = QComboBox(self)
        self.comboBoxDownsample.addItems(list(self.decimationVal.keys()))

        self.textEditComments = QTextEdit(self)
        self.textEditComments.setPlaceholderText('Transmitted Power to NL')

        self.textEditConsoleBox = QTextEdit(self)
        self.textEditConsoleBox.setReadOnly(True)
        self.textEditConsoleBox.setTextColor(QtGui.QColor('black'))

    def placeWidgets(self):
        hboxMain = QHBoxLayout()
        vboxSettings = QVBoxLayout()

        hboxFiletypeDownsample = QHBoxLayout()
        hboxFiletypeDownsample.addWidget(self.labelFiletype)
        hboxFiletypeDownsample.addWidget(self.comboBoxFiletype)
        hboxFiletypeDownsample.addSpacing(20)
        hboxFiletypeDownsample.addWidget(self.labelDownsample)
        hboxFiletypeDownsample.addWidget(self.comboBoxDownsample)
        vboxSettings.addLayout(hboxFiletypeDownsample)

        hboxDirectory = QHBoxLayout()
        hboxDirectory.addWidget(self.labelDirectory)
        hboxDirectory.addWidget(self.lineEditDirectory)
        hboxDirectory.addWidget(self.buttonSelectFolder)
        vboxSettings.addLayout(hboxDirectory)

        hboxStartDate = QHBoxLayout()
        hboxStartDate.addWidget(self.labelStartDate)
        hboxStartDate.addWidget(self.lineEditStartDate)
        vboxSettings.addLayout(hboxStartDate)

        hboxStartTime = QHBoxLayout()
        hboxStartTime.addWidget(self.labelStartTime)
        hboxStartTime.addWidget(self.lineEditStartTime)
        vboxSettings.addLayout(hboxStartTime)

        hboxChannels = QHBoxLayout()
        hboxChannels.addWidget(self.labelChannels)
        hboxChannels.addWidget(self.lineEditChannels)
        hboxChannels.addWidget(self.buttonSelectChannels)
        vboxSettings.addLayout(hboxChannels)

        hboxDuration = QHBoxLayout()
        vboxDuration = QVBoxLayout()
        vboxDuration.addStretch()
        vboxDuration.addWidget(self.labelDuration)
        hboxDuration.addLayout(vboxDuration)
        vboxDays = QVBoxLayout()
        vboxDays.addWidget(self.labelDays)
        vboxDays.addWidget(self.lineEditDays)
        hboxDuration.addLayout(vboxDays)
        vboxHours = QVBoxLayout()
        vboxHours.addWidget(self.labelHours)
        vboxHours.addWidget(self.lineEditHours)
        hboxDuration.addLayout(vboxHours)
        vboxMinutes = QVBoxLayout()
        vboxMinutes.addWidget(self.labelMinutes)
        vboxMinutes.addWidget(self.lineEditMinutes)
        hboxDuration.addLayout(vboxMinutes)
        vboxSeconds = QVBoxLayout()
        vboxSeconds.addWidget(self.labelSeconds)
        vboxSeconds.addWidget(self.lineEditSeconds)
        hboxDuration.addLayout(vboxSeconds)
        vboxSettings.addLayout(hboxDuration)
        vboxSettings.addSpacing(20)

        vboxComments = QVBoxLayout()
        vboxComments.addWidget(self.labelComments)
        vboxComments.addWidget(self.textEditComments)
        vboxSettings.addLayout(vboxComments)

        hboxStartStop = QHBoxLayout()
        hboxStartStop.addStretch()
        hboxStartStop.addWidget(self.buttonStartSave)
        hboxStartStop.addWidget(self.buttonInterrupt)
        hboxStartStop.addStretch()
        vboxSettings.addLayout(hboxStartStop)

        hboxMain.addLayout(vboxSettings)

        vboxConsole = QVBoxLayout()
        vboxConsole.addWidget(self.textEditConsoleBox)
        hboxMain.addLayout(vboxConsole)

        hboxMain.setStretchFactor(vboxSettings, 1)
        hboxMain.setStretchFactor(vboxConsole, 1)

        self.setLayout(hboxMain)
        self.setWindowTitle('ALPS - Save Data from DOOCS')

    def print(self, *text):
        for t in text:
            self.textEditConsoleBox.insertPlainText(str(t)+' ')
        self.textEditConsoleBox.insertPlainText('\n')

    def print_error(self, text):
        self.textEditConsoleBox.setTextColor(QtGui.QColor('red'))
        self.textEditConsoleBox.insertPlainText(text+'\n')
        self.textEditConsoleBox.setTextColor(QtGui.QColor('black'))

    def openChannelSelect(self):
        if not self.windowChannelSelect == None:
            self.windowChannelSelect.close()
        self.windowChannelSelect = ChannelSelect(self)
        self.windowChannelSelect.show()

    def openFolderSelect(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec_():
            self.lineEditDirectory.setText(dialog.selectedFiles()[0])

    def getTimes(self):
        start = self.lineEditStartDate.text() + 'T' + self.lineEditStartTime.text()
        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")

        duration_dt = timedelta(
            days = int(self.lineEditDays.text()),
            hours = int(self.lineEditHours.text()),
            minutes = int(self.lineEditMinutes.text()),
            seconds = int(self.lineEditSeconds.text())
        )
        duration = duration_dt.seconds

        stop_dt = (start_dt + duration_dt)
        stop = stop_dt.strftime('%Y-%m-%dT%H:%M:%S')

        return start, stop, duration, stop_dt

    def dateisPast(self, stoptime):
        return datetime.now() < stoptime

    def badChannelSelection(self, channels, names):
        result = not any(channels)
        for name in names:
            result = result or (name=='')
        return result

    def overwriteCheck(self, filenames):
        overwrite = True
        for file in filenames:
            if os.path.exists(file):
                msg = QMessageBox()
                msg.setWindowTitle('File warning')
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f'Existing file found: {file}\n\nOverwrite file?')
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                choice = msg.exec()
                overwrite &= (choice == QMessageBox.Yes)
                if not overwrite: break
        return overwrite

    def oversizeCheck(self, filesize):
        writeoversize = True
        if filesize > 1e9:
            msg = QMessageBox()
            msg.setWindowTitle('File warning')
            msg.setIcon(QMessageBox.Warning)
            msg.setText("The expected filesize is "+str(round(filesize/1e9,-1))+" GB. Are you sure you want to proceed?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            choice = msg.exec()
            writeoversize &= (choice == QMessageBox.Yes)
        return writeoversize

    def startSave(self):
        start, stop, duration, stop_dt = self.getTimes()

        try:
            if self.badChannelSelection(self.channels, self.filenames):
                raise ChannelError
            if self.dateisPast(stop_dt):
                raise DateError
        except ConfigError as err:
            self.print_error(err.__doc__)
            return

        ftype = self.comboBoxFiletype.currentText()
        directory = self.lineEditDirectory.text()

        filenames = [directory+'/'+fname.replace(' ','_')+ftype*(not fname[-len(ftype):]==ftype) for fname in self.filenames]
        if not self.overwriteCheck(filenames): return

        channels = [self.baseAdr+ch for ch in self.channels]

        sampleRate = self.comboBoxDownsample.currentText()
        decimationFactor = 16000 / self.decimationVal[sampleRate]

        filesize = self.decimationVal[sampleRate] * 8 * duration * len(channels)
        if not self.oversizeCheck(filesize): return

        comments = self.textEditComments.toPlainText()

        self.print('Directory:', directory)
        self.print('Start:', start)
        self.print('Duration:', duration, 'seconds')
        self.print('Sampling rate:', sampleRate)

        self.print('\nChannels:')
        for ch in channels:
            self.print(ch)

        self.print('\nFile names:')
        for fname in filenames:
            self.print(fname)

        if ftype=='.mat':
            self.saveMatThread = QThread()
            self.saveMatWorker = SaveMatWorker(channels, filenames, start, stop, decimationFactor)
            self.saveMatWorker.moveToThread(self.saveMatThread)
            self.saveMatThread.started.connect(self.saveMatWorker.run)
            self.saveMatWorker.finished.connect(self.saveMatThread.quit)
            self.saveMatWorker.finished.connect(self.saveMatWorker.deleteLater)
            self.saveMatThread.finished.connect(self.saveMatThread.deleteLater)
            self.saveMatWorker.report.connect(self.saveWorkerReport)
            self.interrupt.connect(self.saveMatWorker.interruptListen)

            self.saveMatThread.start()
            self.buttonStartSave.setEnabled(False)
            self.saveMatThread.finished.connect(lambda : self.buttonStartSave.setEnabled(True))
        else:
            self.print_error('File type not yet implemented.')
            return

        if not comments=='':
            with open(directory+'/'+'comments.txt', 'w') as f:
                f.write(comments)

    @pyqtSlot(str)
    def saveWorkerReport(self, report):
        self.print('\n'+report)

    def interruptSave(self):
        self.interrupt.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    savewindow = SaveApp()
    savewindow.show()
    sys.exit(app.exec_())
