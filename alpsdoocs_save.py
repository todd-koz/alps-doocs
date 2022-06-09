from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QComboBox,
    QApplication, QHBoxLayout, QVBoxLayout,
    QTabWidget, QFileDialog, QMessageBox)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5 import QtGui

import sys
import os
import os.path
import time
import csv
from datetime import datetime, timedelta
from contextlib import ExitStack

from alpsdoocslib import (open_npy, open_mat, open_csvwrite,
                          get_doocs_data_continuous, save_subroutine,
                          BASE_ADDRESS, DECIMATION_VALUES,
                          NR_ADDRESSES, NL_ADDRESSES, HN_ADDRESSES)

class ConfigError(Exception):
    pass

class DateError(ConfigError):
    """The measurement end time has not yet been reached. Measurement end must be in the past."""
    pass

class ChannelError(ConfigError):
    """No channels selected or a file name is missing."""
    pass

class SaveWorker(QObject):
    finished = pyqtSignal()
    report = pyqtSignal(str)

    def __init__(self, parent, channels, ftype, filenames, start, stop, decimationFactor):
        super().__init__()
        self.parent = parent
        self.channels = channels
        self.ftype = ftype
        self.filenames = filenames
        self.start = start
        self.stop = stop
        self.decimationFactor = decimationFactor
        self.dtype = 'double'*(decimationFactor>1) + 'int16'*(decimationFactor==1)

    def run(self):
        with ExitStack() as stack:
            if self.ftype == '.mat':
                writers = [stack.enter_context(open_mat(fname, 'w', self.dtype)) for fname in self.filenames]
            elif self.ftype == '.npy':
                writers = [stack.enter_context(open_npy(fname, 'w', self.dtype)) for fname in self.filenames]
            elif self.ftype == '.csv':
                writers = [stack.enter_context(open_csvwrite(fname)) for fname in self.filenames]
            else:
                self.report.emit("Filetype not supported.")
                self.finished.emit()
                return

            result = get_doocs_data_continuous(self.channels, save_subroutine,
                                               start=self.start, stop=self.stop,
                                               sub_args=(self.channels, writers, self.decimationFactor),
                                               interrupt=lambda : self.parent.interrupt)

        if 'Trace' in result or 'Except' in result or 'Error' in result:
            for f in self.filenames: os.remove(f)

        self.report.emit(result)
        self.finished.emit()

class SaveChannelTab(QWidget):
    def __init__(self, channelOptions, _channels, _filenames):
        super().__init__()
        self._channels = _channels
        self._filenames = _filenames

        self.channelOptions = channelOptions
        self.checks = [QCheckBox(ch) for ch in channelOptions]
        self.lineFilenames = [QLineEdit(self) for i in range(len(channelOptions))]

        self.labelChannels = QLabel('Channels:')
        self.labelNames = QLabel('File names:')

        vboxMain = QVBoxLayout()

        hboxLabels = QHBoxLayout()
        hboxLabels.addWidget(self.labelChannels)
        hboxLabels.addStretch()
        hboxLabels.addWidget(self.labelNames)
        hboxLabels.addStretch()
        vboxMain.addLayout(hboxLabels)

        for i in range(len(channelOptions)):
            hbox = QHBoxLayout()
            hbox.addWidget(self.checks[i])
            hbox.addWidget(self.lineFilenames[i])
            vboxMain.addLayout(hbox)

        self.setLayout(vboxMain)

    def updateSelection(self):
        for i in range(len(self.channelOptions)):
            if self.checks[i].isChecked():
                self._channels.append(self.channelOptions[i])
                self._filenames.append(self.lineFilenames[i].text())


class SaveChannelSelect(QWidget):
    selectionUpdated = pyqtSignal()

    RANGE_OPTIONS = ['0-7', '8-15', '16-23', '24-31']
    ADDRESSES = {'NR':NR_ADDRESSES, 'HN':HN_ADDRESSES, 'NL':NL_ADDRESSES}

    def __init__(self, parent=None, _channels=[], _filenames=[]):
        super().__init__()
        self.parent = parent
        self._channels = _channels
        self._filenames = _filenames
        self.initUI()

    def initUI(self):
        self.tabLocation = QTabWidget()
        self.tabRange = {}
        self.tabs = []
        for loc in self.ADDRESSES.keys():
            self.tabRange[loc] = QTabWidget()
            for i in range(4):
                self.tabs.append( SaveChannelTab(self.ADDRESSES[loc][i*8:i*8+8], self._channels, self._filenames) )
                self.tabRange[loc].addTab( self.tabs[-1] , self.RANGE_OPTIONS[i] )
            self.tabLocation.addTab( self.tabRange[loc] , loc)

        self.buttonUpdateSelection = QPushButton("Update Selection")
        self.buttonUpdateSelection.clicked.connect(self.updateSelection)

        self.textSelection = QTextEdit()
        self.textSelection.setReadOnly(True)

        vboxMain = QVBoxLayout()
        vboxMain.addWidget(self.tabLocation)
        vboxMain.addSpacing(20)
        vboxMain.addWidget(self.buttonUpdateSelection)
        vboxMain.addSpacing(20)
        vboxMain.addWidget(self.textSelection)

        self.setLayout(vboxMain)
        self.setWindowTitle('Select Channels')

    def updateSelection(self):
        self._channels.clear()
        self._filenames.clear()
        self.textSelection.clear()

        for tab in self.tabs:
            tab.updateSelection()

        for ch,fname in zip(self._channels, self._filenames):
            self.textSelection.insertPlainText(ch + ' : ' + fname + '\n')

        self.selectionUpdated.emit()


class SaveApp(QWidget):
    filetypeOptions = ['.mat', '.npy', '.csv' ]
    baseAdr = BASE_ADDRESS

    decimationVal = DECIMATION_VALUES

    def __init__(self, parent=None):
        super().__init__()

        self.parent = parent

        self.channels = []
        self.filenames = []
        self.windowChannelSelect = None
        self.interrupt = False

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
        self.textEditComments.setPlaceholderText("ex: 'Transmitted Power to NL'")

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
        if self.windowChannelSelect == None:
            self.windowChannelSelect = SaveChannelSelect(self, self.channels, self.filenames)
        self.windowChannelSelect.show()
        self.windowChannelSelect.selectionUpdated.connect(self.displayChannelSelection)

    def displayChannelSelection(self):
        selection_text = ''
        for ch, fname in zip(self.channels, self.filenames):
            selection_text += f"{ch}:{fname}, "
        self.lineEditChannels.setText(selection_text)

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
                raise ChannelError("No channels selected or a file name is missing.")
            if self.dateisPast(stop_dt):
                raise DateError("The measurement end time has not yet been reached. Measurement end must be in the past.")
        except ConfigError as err:
            self.print_error(str(err))
            return

        ftype = self.comboBoxFiletype.currentText()
        directory = self.lineEditDirectory.text()

        filenames = [directory+'/'+fname.replace(' ','_')+ftype*(not fname[-len(ftype):]==ftype) for fname in self.filenames]
        if not self.overwriteCheck(filenames): return

        channels = [self.baseAdr+ch for ch in self.channels]

        sampleRate = self.comboBoxDownsample.currentText()
        decimationFactor = int(16000 / self.decimationVal[sampleRate])

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

        self.saveThread = QThread()
        self.saveWorker = SaveWorker(self, channels, ftype, filenames, start, stop, decimationFactor)
        self.saveWorker.moveToThread(self.saveThread)
        self.saveThread.started.connect(self.saveWorker.run)
        self.saveWorker.finished.connect(self.saveThread.quit)
        self.saveWorker.finished.connect(self.saveWorker.deleteLater)
        self.saveThread.finished.connect(self.saveThread.deleteLater)
        self.saveWorker.report.connect(self.saveWorkerReport)

        self.saveThread.start()
        self.buttonStartSave.setEnabled(False)
        self.saveThread.finished.connect(lambda : self.buttonStartSave.setEnabled(True))

        if not comments=='':
            with open(directory+'/'+'comments.txt', 'w') as f:
                f.write(comments)

    @pyqtSlot(str)
    def saveWorkerReport(self, report):
        self.print('\n'+report)

    def interruptSave(self):
        self.interrupt = False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    savewindow = SaveApp()
    savewindow.show()
    sys.exit(app.exec_())
