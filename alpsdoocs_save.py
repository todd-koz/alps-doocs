#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 01 11:08:22 2022

@author: Daniel
"""
from PyQt5.QtWidgets import (QPushButton, QWidget, QLabel, QLineEdit,
    QTextEdit, QCheckBox, QComboBox, QSizePolicy,
    QGridLayout, QApplication, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox)
from PyQt5 import QtGui

import sys
import os
import os.path
import time
from datetime import datetime
from datetime import timedelta

import alpsdoocslib

class ConfigError(Exception):
    pass

class DateError(ConfigError):
    """The measurement end time has not yet been reached. Measurement end must be in the past."""
    pass

class ChannelError(ConfigError):
    """No channels selected or a file name is missing."""
    pass


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
        self.title = 'Select Channels'
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

        vboxMain = QVBoxLayout(self)

        hboxLabels = QHBoxLayout(self)
        hboxLabels.addWidget(self.labelChannels)
        hboxLabels.addStretch()
        hboxLabels.addWidget(self.labelNames)
        hboxLabels.addStretch()
        vboxMain.addLayout(hboxLabels)

        for i in range(len(self.channelOptions)):
            hbox = QHBoxLayout(self)
            hbox.addWidget(self.checks[i])
            hbox.addWidget(self.names[i])
            vboxMain.addLayout(hbox)

        vboxMain.addStretch()

        hboxButtons = QHBoxLayout(self)
        hboxButtons.addStretch()
        hboxButtons.addWidget(self.buttonUpdateSelection)
        hboxButtons.addStretch()
        vboxMain.addLayout(hboxButtons)

        vboxMain.addStretch()

        hboxSelection = QHBoxLayout(self)
        hboxSelection.addWidget(self.labelSelection)
        hboxSelection.addWidget(self.lineEditSelection)
        vboxMain.addLayout(hboxSelection)

        self.setLayout(vboxMain)
        self.setWindowTitle(self.title)
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

    def __init__(self):
        super().__init__()

        self.title = 'ALPS DOOCS Save File'

        self.interrupt = False
        self.channels = []
        self.filenames = []

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
        hboxMain = QHBoxLayout(self)
        vboxSettings = QVBoxLayout(self)

        hboxFiletypeDownsample = QHBoxLayout(self)
        hboxFiletypeDownsample.addWidget(self.labelFiletype)
        hboxFiletypeDownsample.addWidget(self.comboBoxFiletype)
        hboxFiletypeDownsample.addSpacing(20)
        hboxFiletypeDownsample.addWidget(self.labelDownsample)
        hboxFiletypeDownsample.addWidget(self.comboBoxDownsample)
        vboxSettings.addLayout(hboxFiletypeDownsample)

        hboxDirectory = QHBoxLayout(self)
        hboxDirectory.addWidget(self.labelDirectory)
        hboxDirectory.addWidget(self.lineEditDirectory)
        hboxDirectory.addWidget(self.buttonSelectFolder)
        vboxSettings.addLayout(hboxDirectory)

        hboxStartDate = QHBoxLayout(self)
        hboxStartDate.addWidget(self.labelStartDate)
        hboxStartDate.addWidget(self.lineEditStartDate)
        vboxSettings.addLayout(hboxStartDate)

        hboxStartTime = QHBoxLayout(self)
        hboxStartTime.addWidget(self.labelStartTime)
        hboxStartTime.addWidget(self.lineEditStartTime)
        vboxSettings.addLayout(hboxStartTime)

        hboxChannels = QHBoxLayout(self)
        hboxChannels.addWidget(self.labelChannels)
        hboxChannels.addWidget(self.lineEditChannels)
        hboxChannels.addWidget(self.buttonSelectChannels)
        vboxSettings.addLayout(hboxChannels)

        hboxDuration = QHBoxLayout(self)
        vboxDuration = QVBoxLayout(self)
        vboxDuration.addStretch()
        vboxDuration.addWidget(self.labelDuration)
        hboxDuration.addLayout(vboxDuration)
        vboxDays = QVBoxLayout(self)
        vboxDays.addWidget(self.labelDays)
        vboxDays.addWidget(self.lineEditDays)
        hboxDuration.addLayout(vboxDays)
        vboxHours = QVBoxLayout(self)
        vboxHours.addWidget(self.labelHours)
        vboxHours.addWidget(self.lineEditHours)
        hboxDuration.addLayout(vboxHours)
        vboxMinutes = QVBoxLayout(self)
        vboxMinutes.addWidget(self.labelMinutes)
        vboxMinutes.addWidget(self.lineEditMinutes)
        hboxDuration.addLayout(vboxMinutes)
        vboxSeconds = QVBoxLayout(self)
        vboxSeconds.addWidget(self.labelSeconds)
        vboxSeconds.addWidget(self.lineEditSeconds)
        hboxDuration.addLayout(vboxSeconds)
        vboxSettings.addLayout(hboxDuration)
        vboxSettings.addSpacing(20)

        vboxComments = QVBoxLayout(self)
        vboxComments.addWidget(self.labelComments)
        vboxComments.addWidget(self.textEditComments)
        vboxSettings.addLayout(vboxComments)

        hboxStartStop = QHBoxLayout(self)
        hboxStartStop.addStretch()
        hboxStartStop.addWidget(self.buttonStartSave)
        hboxStartStop.addWidget(self.buttonInterrupt)
        hboxStartStop.addStretch()
        vboxSettings.addLayout(hboxStartStop)

        hboxMain.addLayout(vboxSettings)

        vboxConsole = QVBoxLayout(self)
        vboxConsole.addWidget(self.textEditConsoleBox)
        hboxMain.addLayout(vboxConsole)

        hboxMain.setStretchFactor(vboxSettings, 1)
        hboxMain.setStretchFactor(vboxConsole, 1)

        self.setLayout(hboxMain)
        self.setWindowTitle(self.title)

    def print(self, *text):
        for t in text:
            self.textEditConsoleBox.insertPlainText(str(t)+' ')
        self.textEditConsoleBox.insertPlainText('\n')

    def openChannelSelect(self):
        self.selectdialog = ChannelSelect(self)
        self.selectdialog.show()

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

        return start, duration, stop_dt

    def dateisPast(self, stoptime):
        return datetime.now() < stoptime

    def badChannelSelection(self, channels, comments):
        result = not any(channels)

        for com in comments:
            result = result or (com=='')

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
        self.interrupt = False

        ftype = self.comboBoxFiletype.currentText()
        directory = self.lineEditDirectory.text()

        filenames = [directory+'/'+fname.replace(' ','_')+ftype*(not fname[-len(ftype):]==ftype) for fname in self.filenames]
        if not self.overwriteCheck(filenames): return

        start, duration, stop_dt = self.getTimes()

        try:
            if self.badChannelSelection(self.channels, self.filenames):
                raise ChannelError
            if self.dateisPast(stop_dt):
                raise DateError
        except ConfigError as err:
            self.textEditConsoleBox.setTextColor(QtGui.QColor('red'))
            self.print(err.__doc__)
            self.textEditConsoleBox.setTextColor(QtGui.QColor('black'))
            return

        sampleRate = self.comboBoxDownsample.currentText()
        decimationFactor = 16000 / self.decimationVal[sampleRate]

        filesize = self.decimationVal[sampleRate] * 8 * duration * len(self.channels)
        if not self.oversizeCheck(filesize): return

        self.print('Directory:', directory)
        self.print('Start:', start)
        self.print('Duration:', duration, 'seconds')
        self.print('Sampling rate:', sampleRate)

        self.print('\nChannels:')
        for ch in self.channels:
            self.print(ch)

        self.print('\nFile names:')
        for fname in filenames:
            self.print(fname)

        #### begin new thread and start saving

    def interruptSave(self):
        self.interrupt = True


if __name__ == '__main__':
    app = QApplication(sys.argv)
    savewindow = SaveApp()
    savewindow.show()
    sys.exit(app.exec_())
