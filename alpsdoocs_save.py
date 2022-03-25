#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 13:15:16 2022

@author: todd, daniel
"""

from tkinter import *
from tkinter.ttk import *
from tkinter import scrolledtext
from tkinter.messagebox import askyesno
#from tkcalendar import DateEntry

from datetime import datetime
from datetime import timedelta
import os
import os.path

import alpsdoocslib

class ConfigError(Exception):
    pass

class DateError(ConfigError):
    """The measurement end time has not yet been reached. Measurement end must be in the past."""
    pass

class ChannelError(ConfigError):
    """No channels selected or a file name is missing."""
    pass

### child window to display and choose from an arbitrary number of channels
class ChannelSelectWindow():
    channel_options = [
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
        if parent.parent == None:
            self.root = Toplevel(parent.root)
        else:
            self.root = Toplevel(parent)
        self.root.title('Select channels')
        self.parent = parent

        self.channelsLabel = Label(self.root, text="Channels:")
        self.namesLabel = Label(self.root, text="File names:")
        self.selectButton = Button(self.root, text="Update Selection", command=self.SaveAndClose)

        self.vars = []
        self.checks = []
        self.names = []

        for i in range(len(self.channel_options)):
            self.vars.append(IntVar())
            self.checks.append( Checkbutton(self.root, text=self.channel_options[0], variable=self.vars[i]) )
            self.names.append( Entry(self.root, width=50) )

        self.channelsLabel.grid(row=0, column=0)
        self.namesLabel.grid(row=0, column=1)

        for i in range(len(self.channel_options)):
            self.checks[i].grid(row=i+1, column=0)
            self.names[i].grid(row=i+1, column=1)

        self.selectButton.grid(row=len(self.channel_options)+1, column=1, columnspan=2)

    def SaveAndClose(self):
        self.parent.channels.clear()
        self.parent.filenames.clear()
        for i in range(len(self.channel_options)):
            if self.vars[i].get():
                self.parent.channels.append(self.channel_options[i])
                self.parent.filenames.append(self.names[i].get())
        self.updateView()

    def updateView(self):
        s = ''
        for i in range(len(self.parent.channels)):
            s = s + f"({self.parent.channels[i]}, {self.parent.filenames[i]}) "
        self.parent.channelSelectResult.insert(0, s)

class SaveApp():
    filetype_options = ['.mat', '.csv' ]

    decimationVal = {
        "16kHz": 16000,
        "8kHz": 8000,
        "4kHz": 4000,
        "2kHz": 2000,
        "1kHz": 1000,
        "500Hz": 500,
        "100Hz": 100,
        "64Hz": 64,
        "32Hz": 32 }

    def __init__(self, parent=None):

        if parent==None:
            self.root = Tk()
        else:
            self.root = Toplevel(parent)

        self.parent = parent
        self.root.title("ALPS DOOCS Save Data")

        self.defineWidgets()
        self.placeWidgets()

        self.channels = []
        self.filenames = []

        self.interrupt = False

    def defineWidgets(self):
        self.channelSelectLabel = Label(self.root, text="Select channels: ")
        self.filetypeLabel = Label(self.root, text="Filetype: ")
        self.directoryLabel = Label(self.root, text="Save Directory: ")
        self.startdateLabel = Label(self.root, text="Start date: ")
        self.starttimeLabel = Label(self.root, text="Start time: ")
        self.durationLabel = Label(self.root, text="Duration: ")
        self.daysLabel = Label(self.root, text="Days:")
        self.hoursLabel = Label(self.root, text="Hours:")
        self.minutesLabel = Label(self.root, text="Minutes:")
        self.secondsLabel = Label(self.root, text="Seconds:")
        self.usercommentsLabel = Label(self.root, text="Enter additional user comments about this measurement/data. \nThese additional comments will be saved as a .txt file in the destination directory.")

        self.channelSelectButton = Button(self.root, text="Select Channels", command=self.openChannelSelect)
        self.channelSelectResult = Entry(self.root, width=50, justify='left')

        self.filetype = StringVar()
        self.filetype.set('.mat')
        self.filetype_drop = OptionMenu(self.root, self.filetype, self.filetype_options[0], *self.filetype_options)

        self.directory = Entry(self.root, width=50, justify='left')
        self.directory.insert(0, os.getcwd())
        self.directory.xview_moveto(1)

        self.startdateEntry = Entry(self.root, width=50)
        self.startdateEntry.insert(0, datetime.today().strftime('%Y-%m-%d'))

        self.starttimeEntry = Entry(self.root, width=50)
        self.starttimeEntry.insert(0, datetime.today().strftime('%H:%M:%S'))

        self.duration_d = Entry(self.root, width=10)
        self.duration_d.insert(0,0)
        self.duration_h = Entry(self.root, width=10)
        self.duration_h.insert(0,0)
        self.duration_m = Entry(self.root, width=10)
        self.duration_m.insert(0,0)
        self.duration_s = Entry(self.root, width=10)
        self.duration_s.insert(0,10)

        self.timedelta = timedelta(
            days = int(self.duration_d.get()),
            hours = int(self.duration_h.get()),
            minutes = int(self.duration_m.get()),
            seconds = int(self.duration_s.get()) )

        self.starttime = datetime.strptime(
            self.startdateEntry.get()+self.starttimeEntry.get(),
            "%Y-%m-%d%H:%M:%S" )

        self.startDateLabel = Label(self.root, text=self.starttime)
        self.timeDeltaLabel = Label(self.root, text=self.timedelta)
        self.endDateLabel = Label(self.root, text=self.starttime+self.timedelta)

        self.decimationLabel = Label(self.root, text="Down-sample to:")
        self.decimation = StringVar()
        self.decimation_drop = OptionMenu(self.root, self.decimation, list(self.decimationVal.keys())[0], *list(self.decimationVal.keys()))

        self.saveFileButton = Button(self.root, text="Start Save", command=self.saveButtonClick )

        self.interruptButton = Button(self.root, text="Interrupt Save", command=self.interruptButtonClick, state=DISABLED)

        self.usercommentFrame = Frame(self.root)
        self.usercommentBox = Text(self.usercommentFrame,wrap=WORD,height=5)
        self.consoleFrame = Frame(self.root)
        self.consoleBox = scrolledtext.ScrolledText(self.consoleFrame,wrap=WORD)

    def placeWidgets(self):
        ### ROW 0
        self.filetypeLabel.grid(row=0,column=0,sticky=W,pady=2)
        self.filetype_drop.grid(row=0,column=1,sticky=W,pady=2)

        ### ROW 1
        self.directoryLabel.grid(row=1,column=0,sticky=W,pady=2)
        self.directory.grid(row=1,column=1,sticky=W,pady=2,columnspan=4)

        ### ROW 2
        self.startdateLabel.grid(row=2,column=0,sticky=W,pady=2)
        self.startdateEntry.grid(row=2,column=1,sticky=W,pady=2,columnspan=4)


        ### ROW 3
        self.starttimeLabel.grid(row=3,column=0,sticky=W,pady=2)
        self.starttimeEntry.grid(row=3,column=1,sticky=W,pady=2,columnspan=4)

        ### ROW 4
        self.channelSelectLabel.grid(row=4, column=0, stick=W)
        self.channelSelectButton.grid(row=4, column=1, sticky=W)
        self.channelSelectResult.grid(row=4, column=2, sticky=W, columnspan=3)

        ### ROW 5
        self.durationLabel.grid(row=5,column=0,sticky=W,pady=2)
        self.daysLabel.grid(row=5,column=1,sticky=W,pady=2)
        self.hoursLabel.grid(row=5,column=2,sticky=W,pady=2)
        self.minutesLabel.grid(row=5,column=3,sticky=W,pady=2)
        self.secondsLabel.grid(row=5,column=4,sticky=W,pady=2)

        ### ROW 6
        self.duration_d.grid(row=6,column=1,sticky=W,pady=2)
        self.duration_h.grid(row=6,column=2,sticky=W,pady=2)
        self.duration_m.grid(row=6,column=3,sticky=W,pady=2)
        self.duration_s.grid(row=6,column=4,sticky=W,pady=2)

        ### ROW 7
        self.decimationLabel.grid(row=7,column=0,sticky=W,pady=2)
        self.decimation_drop.grid(row=7,column=1,sticky=W,pady=2)

        self.saveFileButton.grid(row=27,column=1,sticky=W, pady=2)
        self.interruptButton.grid(row=27,column=2,sticky=W, pady=2)

        self.usercommentsLabel.grid(row=47, column=0, sticky=W, pady=2, columnspan=5)
        self.usercommentFrame.grid(row=48,column=0,sticky=W,pady=2,columnspan=5)

        self.usercommentBox.grid(row=49,column=0)
        self.usercommentBox.config(state=NORMAL)

        self.consoleFrame.grid(row=50,column=0,sticky=W,pady=2,columnspan=5)

        self.consoleBox.grid(row=51,column=0)
        self.consoleBox.config(state=DISABLED)
        self.consoleBox.tag_config('warning', foreground='red')
        self.consoleBox.tag_config('normal', foreground='black')

    def saveButtonClick(self):
        filenames = [name + self.filetype.get() for name in self.filenames]
        start, stop, duration, start_dt, stop_dt , duration_dt = self.getTimes()
        filesize = self.decimationVal[self.decimation.get()] * 8 * self.getTimes()[2] * len(self.channels) / 1e6
        samplingRate = self.decimation.get()
        decimationFactor = 16000 / self.decimationVal[samplingRate]

        try:
            if self.badChannelSelection(self.channels, self.filenames):
                raise ChannelError
            if self.dateisPast(stop_dt):
                raise DateError
        except ConfigError as err:
            self.printToConsoleBox(err.__doc__+'\n', 'warning')
            return

        summary = (
                     f"\n###########################################################"
                     f"\nFile save configuration overview."
                     f"\n   This will save data to: {self.directory.get()}"
                     f"\n   Data start time: {start}"
                     f"\n   Data stop time: {stop}"
                     f"\n   Data Duration: {duration}"
                     f"\n   Sampling rate: {samplingRate}\n"
                   )

        if self.overwriteCheck(filenames) and self.oversizeCheck(filesize):
            self.printToConsoleBox(summary)
            self.interruptButton.config(state=NORMAL)
            self.interrupt = False
            self.startSave(self.channels, filenames, start, stop, decimationFactor)
        else:
            self.printToConsoleBox('Save canceled.')

    def startSave(self, channels, filenames, start, stop, decimationFactor):
        alpsdoocslib.save_to_mat_custom(channels, filenames, start=start, stop=stop)

    def interruptButtonClick(self):
        self.interrupt = True
        self.interruptButton.config(state=DISABLED)

    def openChannelSelect(self):
        selectionWindow = ChannelSelectWindow(self)
        selectionWindow.root.mainloop()

    def printToConsoleBox(self, message, type='normal'):
        self.consoleBox.config(state=NORMAL)
        self.consoleBox.insert('insert', message, type)
        self.consoleBox.see(END)
        self.consoleBox.config(state=DISABLED)

    def getTimes(self):
        start = self.startdateEntry.get() + 'T' + self.starttimeEntry.get()
        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")

        duration_dt = timedelta(
            days = int(self.duration_d.get()),
            hours = int(self.duration_h.get()),
            minutes = int(self.duration_m.get()),
            seconds = int(self.duration_s.get()) )
        duration = duration_dt.seconds

        stop_dt = (start_dt + duration_dt)
        stop = stop_dt.strftime("%Y-%m-%dT%H:%M:%S")

        return start, stop, duration, start_dt, stop_dt, duration_dt

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
                overwrite = overwrite or askyesno("Overwrite","A file with this name already exists. Do you want to overwrite?")
                if not overwrite: break
        return overwrite

    def oversizeCheck(self, filesize):
        writeoversize = True
        if filesize > 1e9:
           writeoversize = askyesno("Oversize","The expected filesize is "+str(round(filesize/1e3,-1))+" GB. Are you sure you want to proceed?")
        return writeoversize

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    myapp = SaveApp()
    myapp.run()
