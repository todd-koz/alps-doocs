#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 13:15:16 2022

@author: todd
"""

from tkinter import *
from tkinter.ttk import *
from tkinter import scrolledtext
from tkinter.messagebox import askyesno
import numpy as np
from tkcalendar import DateEntry
from datetime import datetime
from datetime import timedelta
import alpsdoocslib
import os
import os.path
from example_data import *
from pathlib import Path
import matplotlib.pyplot as plt
from gwpy.timeseries import TimeSeries
from gwpy.frequencyseries import FrequencySeries

root = Tk()
root.title('ALPS DOOCS Autoplotter')
#root.geometry("400x600")

class saveConfig(object):
    pass
myConfig = saveConfig()

class plotConfig():
    pass
pltConfig = plotConfig()

class DateError(Exception):
    """The measurement end time has not yet been reached. Measurement end must be in the past."""
    pass
#


def UpdateConfig():
    try:
        global myConfig
        myConfig.channels=[channel1select.get()]
        myConfig.channellabels=[channel1Comment.get()] 
        myConfig.time=[int(duration_d.get()),int(duration_h.get()),int(duration_m.get()),int(duration_s.get())]
        myConfig.mytimedelta = timedelta(days=myConfig.time[0],hours=myConfig.time[1],minutes=myConfig.time[2],seconds=myConfig.time[3])
        myConfig.start_datetime = datetime.strptime(startdate.get()+starttime.get(), "%Y-%m-%d%H:%M:%S")
        myConfig.stop_datetime = myConfig.start_datetime + myConfig.mytimedelta
        myConfig.input_start = myConfig.start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        myConfig.input_stop = myConfig.stop_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        
        if not dateisPast(myConfig.stop_datetime):
            raise DateError
        
        numChannels = 1
#        if myConfig.channels[0] != "None":
#            numChannels += 1
#        if myConfig.channels[1] != "None":
#            numChannels += 1
#        if myConfig.channels[2] != "None":
#            numChannels += 1
#        if myConfig.channels[3] != "None":
#            numChannels += 1
            
        myConfig.decimation=decimation.get()
        myConfig.decimationFactor = 16000 / decimationVal[decimation.get()]
        
        myConfig.filesize = decimationVal[decimation.get()]*8*myConfig.mytimedelta.total_seconds()*numChannels/1e6 ## in MB
        myConfig.configSummary = (
                                    f"\n###########################################################"
                                    f"\nPlot data preview."
                                    f"\n   Data start time: {myConfig.start_datetime}"
                                    f"\n   Data stop time: {myConfig.stop_datetime}"
                                    f"\n   Data Duration: {myConfig.mytimedelta}"
                                    f"\n   Sampling rate: {myConfig.decimation}"
                                    f"\n   Plotting on y-axis 1: {myConfig.channels[0]} ..... channel label: {myConfig.channellabels[0]}\n"
                                  )
        consoleBox.config(state=NORMAL)
        consoleBox.insert('insert',myConfig.configSummary)
        consoleBox.tag_config('warning',foreground="red")
        if myConfig.filesize > 1e9:
            consoleBox.insert('insert',f"\n   CAUTION!! Estimated data size to plot: {myConfig.filesize} MB",'warning')
        consoleBox.see(END)
        consoleBox.config(state=DISABLED)
    except DateError:
        consoleBox.tag_config('warning',foreground="red")
        consoleBox.config(state=NORMAL)
        consoleBox.insert(END,("\n\nError occured: The measurement end time has not yet been reached. Measurement end must be in the past"),'warning')
        consoleBox.config(state=DISABLED)
        consoleBox.see(END)
    except Exception as e:
        consoleBox.tag_config('warning',foreground="red")
        consoleBox.config(state=NORMAL)
        consoleBox.insert(END,("\n\nError occured: {0} \nPlease check the format of your entries! \n".format(e)),'warning')
        consoleBox.config(state=DISABLED)
        consoleBox.see(END)

        
    myConfig.daqchannels=[value for value in myConfig.channels if value != 'None']

def makePlot():
    fs = 16000
    ch1data = getdata_sample4[0]['data'][0]
    ch1TimeSeries = TimeSeries(data=ch1data,dt=1/fs)
    print(f'{filtfreqEntry.get()} Hz')
    if filtertype1.get() == "lowpass":
        print("hello")
        ch1TimeSeries = ch1TimeSeries.lowpass(float(filtfreqEntry.get()))
    ch1psd = ch1TimeSeries.psd()
    newWindow=Toplevel(root)
    newWindow.title("Plot window")
    newWindow.geometry("600x600")
    Label(newWindow,text="This is a new window").pack()


    t = np.arange(0, len(ch1TimeSeries)/fs, 1/fs)
    fig = plt.figure(figsize=(5, 4), dpi=100)
#    fig.add_subplot(111).plot(t, ch1TimeSeries)
    fig.add_subplot(111)
    plt.plot(ch1psd)
    plt.xscale('log')
    
    
    canvas = FigureCanvasTkAgg(fig, master=newWindow)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
    
    toolbar = NavigationToolbar2Tk(canvas, newWindow)
    toolbar.update()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
########################################################################
########################################################################
########################################################################

### entry field labels
scaleLabel = Label(root,text="polynomial scale factor (a*x + b):")
plotTypeLabel = Label(root,text="Plot type:")
channelsLabel = Label(root,text="channel 1 y-axis")
channel1Label = Label(root,text="Channel select:")
channel2Label = Label(root,text="Channel 2:")
channel3Label = Label(root,text="Channel 3:")
channel4Label = Label(root,text="Channel 4:")
startdateLabel = Label(root,text="Data start date: ")
starttimeLabel = Label(root,text="Data start time: ")
durationLabel = Label(root,text="Duration: ")
daysLabel = Label(root,text="Days:")
hoursLabel = Label(root,text="Hours:")
minutesLabel = Label(root,text="Minutes:")
secondsLabel = Label(root,text="Seconds:")
usercommentsLabel = Label(root,text="Enter additional user comments about this measurement/data. \nThese additional comments will be saved as a .txt file in the destination directory.")
channel1commentLabel = Label(root,text="channel 1 legend:")
channel2commentLabel = Label(root,text="y-axis 2 label")
channel3commentLabel = Label(root,text="y-axis 3 label")
channel4commentLabel = Label(root,text="y-axis 4 label")

### Channel selection dropdown menus
### Channel selection dropdown menus
channel_options = [
        'None',
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
        'HN/CH_1.00',
        ]
channel1select = StringVar()
channel2select = StringVar()
channel3select = StringVar()
channel4select = StringVar()
channel1_drop = OptionMenu(root, channel1select, channel_options[0], *channel_options)
channel2_drop = OptionMenu(root, channel2select, channel_options[0], *channel_options)
channel3_drop = OptionMenu(root, channel3select, channel_options[0], *channel_options)
channel4_drop = OptionMenu(root, channel4select, channel_options[0], *channel_options)
channel1_drop.config(width=10)
channel2_drop.config(width=10)
channel3_drop.config(width=10)
channel4_drop.config(width=10)

### channel user comments
channel1Comment = Entry(root,width=15)
channel1Comment.insert(0,"")
channel2Comment = Entry(root,width=10)
channel2Comment.insert(0,"")
channel3Comment = Entry(root,width=10)
channel3Comment.insert(0,"")
channel4Comment = Entry(root,width=10)
channel4Comment.insert(0,"")

### start date entry field
startdate = Entry(root,width=10)
startdate.insert(0,datetime.today().strftime('%Y-%m-%d'))
### 

### start time entry field
starttime = Entry(root,width=10)
starttime.insert(0,datetime.today().strftime('%H:%M:%S'))
### 

### duration days entry field
duration_d = Entry(root,width=5)
duration_d.insert(0,0)

### duration hours entry field
duration_h = Entry(root,width=5)
duration_h.insert(0,0)

### duration minutes entry field
duration_m = Entry(root,width=5)
duration_m.insert(0,0)

### duration seconds entry field
duration_s = Entry(root,width=5)
duration_s.insert(0,10)

mytimedelta=timedelta(days=int(duration_d.get()),hours=int(duration_h.get()),minutes=int(duration_m.get()),seconds=int(duration_s.get()))
mystarttime=datetime.strptime(startdate.get()+starttime.get(), "%Y-%m-%d%H:%M:%S")

myStartDateLabel = Label(root,text=mystarttime)
myTimeDeltaLabel = Label(root,text=mytimedelta)
myEndDateLabel = Label(root,text=mystarttime+mytimedelta)

scaleA = Entry(root,width=5)
scaleA.insert(0,1)
scaleB = Entry(root,width=5)
scaleB.insert(0,0)

myDecimationLabel = Label(root,text="Downsample to:")
myPlotTypeLabel = Label(root,text="Select type of plot to generate:")

####
decimation = StringVar()
decimationVal = {
        "16kHz": 16000,
        "8kHz": 8000,
        "4kHz": 4000,
        "2kHz": 2000,
        "1kHz": 1000,
        "500Hz": 500,
        "100Hz": 100,
        "64Hz": 64,
        "32Hz": 32
        }
decimation_drop = OptionMenu(root, decimation, list(decimationVal.keys())[0], *list(decimationVal.keys()))
###

plottype = StringVar()
plot_options = {
        "Amplitude Spectral Density (ASD)":"asd",
        "Power Spectral Density (PSD)":"psd",
        "Time Series":"ts"
        }
plottype_drop = OptionMenu(root, plottype, list(plot_options.keys())[2], *list(plot_options.keys()))

def OptionMenu_SelectionEvent(event): # I'm not sure on the arguments here, it works though
    if filtertype1.get() == "lowpass":
        filtfreqLabel = Label(root,text="Lowpass corner frequency (Hz):")
        filtfreqEntry = Entry(root,width=10)
        filtfreqLabel.grid(row=19,column=3,sticky=EW,pady=2,columnspan=2)
        filtfreqEntry.grid(row=20,column=3,sticky=EW,pady=2,columnspan=2)
    if filtertype1.get() == "highpass":
        filtfreqLabel = Label(root,text="Highpass corner frequency (Hz):")
        filtfreqEntry = Entry(root,width=10)
        filtfreqLabel.grid(row=19,column=3,sticky=EW,pady=2,columnspan=2)
        filtfreqEntry.grid(row=20,column=3,sticky=EW,pady=2,columnspan=2)
    if filtertype1.get() == "bandpass":
        filtfreqLabel = Label(root,text="Bandpass low and high frequencies (Hz):")
        filtfreqEntry = Entry(root,width=10)
        filtfreqLabel.grid(row=19,column=3,sticky=EW,pady=2,columnspan=2)
        filtfreqEntry.grid(row=20,column=3,sticky=EW,pady=2,columnspan=2)
    if filtertype1.get() == "None":
        filtfreqLabel = Label(root,text="Corner frequency:")
        filtfreqEntry = Entry(root,width=10)
        filtfreqLabel.grid_remove()
        filtfreqEntry.grid_remove()
        print("None")
    pass

filtfreqLabel = Label(root,text="Corner frequency:")
filtfreqEntry = Entry(root,width=10)

filterLabel = Label(root,text="Select optional signal filter:")
filtertype1,filtertype2,filtertype3,filtertype4=StringVar(),StringVar(),StringVar(),StringVar()
filter_options = [
        "None",
        "lowpass",
        "highpass",
        "notch",
        "bandpass",
        "custom filter (zpk)"
        ]
filtertype1_drop = OptionMenu(root, filtertype1, filter_options[0], *filter_options, command = OptionMenu_SelectionEvent)
filtertype2_drop = OptionMenu(root, filtertype2, filter_options[0], *filter_options)
filtertype3_drop = OptionMenu(root, filtertype3, filter_options[0], *filter_options)
filtertype4_drop = OptionMenu(root, filtertype4, filter_options[0], *filter_options)



############ GUI LAYOUT ################
plotTypeLabel.grid(row=0,column=0,sticky=W,pady=2)
plottype_drop.grid(row=0,column=1,columnspan=3,sticky=EW,pady=2)

### Labels
startdateLabel.grid(row=3,column=0,sticky=W,pady=2)
starttimeLabel.grid(row=4,column=0,sticky=W,pady=2)
durationLabel.grid(row=5,column=0,sticky=W,pady=2)
daysLabel.grid(row=5,column=1,sticky=W,pady=2)
hoursLabel.grid(row=5,column=2,sticky=W,pady=2)
minutesLabel.grid(row=5,column=3,sticky=W,pady=2)
secondsLabel.grid(row=5,column=4,sticky=W,pady=2)

### Entry fields
startdate.grid(row=3,column=1,sticky=EW,pady=2,columnspan=2)
starttime.grid(row=4,column=1,sticky=EW,pady=2,columnspan=2)
duration_d.grid(row=6,column=1,sticky=EW,pady=2)
duration_h.grid(row=6,column=2,sticky=EW,pady=2)
duration_m.grid(row=6,column=3,sticky=EW,pady=2)
duration_s.grid(row=6,column=4,sticky=EW,pady=2)

### y1 configuration
channelsLabel.grid(row=14,column=0,sticky=W,pady=5,columnspan=1)
channel1Label.grid(row=15,column=1,sticky=W,pady=2,columnspan=2)
channel1_drop.grid(row=16,column=1,sticky=EW,pady=2,columnspan=2)
channel1commentLabel.grid(row=15,column=4,sticky=EW, padx=5)
channel1Comment.grid(row=16,column=4,sticky=W,pady=2, padx=5,columnspan=1)
myDecimationLabel.grid(row=15,column=3,sticky=EW,pady=2,columnspan=1)
decimation_drop.grid(row=16,column=3,sticky=EW,pady=2,columnspan=1)
filterLabel.grid(row=19,column=1,sticky=EW,pady=2,columnspan=2)
filtertype1_drop.grid(row=20,column=1,sticky=EW,pady=2,columnspan=2)


scaleLabel.grid(row=30,column=1,sticky=EW,columnspan=3)
scaleA.grid(row=30,column=3)
scaleB.grid(row=30,column=4)


Separator(root,orient=HORIZONTAL).grid(row=2,columnspan=10,sticky="ew",pady=5)
Separator(root,orient=HORIZONTAL).grid(row=8,columnspan=10,sticky="ew",pady=5)
Separator(root,orient=HORIZONTAL).grid(row=18,column=1,columnspan=10,sticky="ew",pady=5)
Separator(root,orient=HORIZONTAL).grid(row=8,columnspan=10,sticky="ew")


### configuration logging space
consoleFrame = Frame(root,height=30)
consoleFrame.grid(row=50,column=0,sticky=W,pady=2,columnspan=10)

consoleBox = scrolledtext.ScrolledText(consoleFrame,wrap=WORD)
consoleBox.grid(row=51,column=0)
consoleBox.config(state=DISABLED)

### Buttons
updateConfigButton = Button(root, text="Update Plot Configuration", command=UpdateConfig)
makePlotButton = Button(root,text="Generate Plot",command=makePlot)
makePlotButton.grid(row=100,column=1)
updateConfigButton.grid(row=52,column=1,sticky=W,pady=2,columnspan=4)

root.mainloop()

