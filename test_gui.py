#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 13:15:16 2022

@author: todd
"""

from tkinter import *
import numpy as np
from tkcalendar import DateEntry
from datetime import datetime
from datetime import timedelta
import save_to_file
import os.path

root = Tk()
root.title('ALPS DOOCS Save Data')
root.geometry("400x600")


### entry field labels
filetypeLabel = Label(root,text="Filetype: ")
directoryLabel = Label(root,text="Dir: ")
filenameLabel = Label(root,text="Filename: ")
startdateLabel = Label(root,text="Data start date: ")
durationLabel = Label(root,text="Measurement Duration: ")
daysLabel = Label(root,text="Days:")
hoursLabel = Label(root,text="Hours:")
minutesLabel = Label(root,text="Minutes:")
secondsLabel = Label(root,text="Seconds:")

### filetype dropdown menu
filetype = StringVar()
filetype.set(".mat")
filetype_options = [
        ".mat",
        ".csv"
        ] 
filetype_drop = OptionMenu(root, filetype, *filetype_options)
filetype_drop.pack()
###

### destination directory entry field
directory = Entry(root,width=50,justify='right')
directory.insert(0,"/home/todd/sync_desy/disseration_material/software/python/alps-doocs/")
directory.pack()
directory.xview_moveto(1)
### 

### file name entry field
filename = Entry(root,width=50)
filename.pack()
filename.insert(0,"default_filename")
### 

### start date entry field
startdate = Entry(root,width=50)
startdate.pack()
startdate.insert(0,datetime.today().strftime('%Y-%m-%d'))
### 

### start time entry field
starttime = Entry(root,width=50)
starttime.pack()
starttime.insert(0,datetime.today().strftime('%H:%M:%S'))
### 

### duration days entry field
duration_d = Entry(root,width=50)
duration_d.pack()
duration_d.insert(0,0)

### duration hours entry field
duration_h = Entry(root,width=50)
duration_h.pack()
duration_h.insert(0,0)

### duration minutes entry field
duration_m = Entry(root,width=50)
duration_m.pack()
duration_m.insert(0,0)

### duration seconds entry field
duration_s = Entry(root,width=50)
duration_s.pack()
duration_s.insert(0,10)

#starttime = Entry(root,width=50)
#starttime.pack()
#starttime.insert(0,"202)

mytimedelta=timedelta(days=int(duration_d.get()),hours=int(duration_h.get()),minutes=int(duration_m.get()),seconds=int(duration_s.get()))
mystarttime=datetime.strptime(startdate.get()+starttime.get(), "%Y-%m-%d%H:%M:%S")

myFileLabel = Label(root,text=filename.get()+filetype.get())
myStartDateLabel = Label(root,text=mystarttime)
myTimeDeltaLabel = Label(root,text=mytimedelta)
myEndDateLabel = Label(root,text=mystarttime+mytimedelta)

class saveConfig(object):
    pass
myConfig = saveConfig()

def UpdateConfig():
    global myConfig
    myConfig.filename=filename.get()
    myConfig.filetype=filetype.get()
    myConfig.days=int(duration_d.get())
    myConfig.hours=int(duration_h.get())
    myConfig.minutes=int(duration_m.get())
    myConfig.seconds=int(duration_s.get())
    myConfig.mytimedelta = timedelta(days=myConfig.days,hours=myConfig.hours,minutes=myConfig.minutes,seconds=myConfig.seconds)
    myConfig.start_datetime = datetime.strptime(startdate.get()+starttime.get(), "%Y-%m-%d%H:%M:%S")
    myConfig.stop_datetime = myConfig.start_datetime + myConfig.mytimedelta
    myConfig.input_start = myConfig.start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
    myConfig.input_stop = myConfig.stop_datetime.strftime('%Y-%m-%dT%H:%M:%S')
    myConfig.path = directory.get()+myConfig.filename+myConfig.filetype
    
    myFileLabel.config(text=myConfig.filename+myConfig.filetype)
    myStartDateLabel.config(text=myConfig.start_datetime)
    myTimeDeltaLabel.config(text=myConfig.mytimedelta)
    myEndDateLabel.config(text=myConfig.stop_datetime)
    myConfig.testdatalength=testdata.get()
    myConfig.decimation=decimation.get()
    
    myTestDataLabel.config(text="Length of test data: "+myConfig.testdatalength)
    myDecimationLabel.config(text="Decimate to sampling frequency of: "+myConfig.decimation)
    
    saveFileButton.config(state = NORMAL)
    
#def overwriteCheck(filename):
#    if os.path.exists(filename):
        
        
  
def SaveButtonClick():
    global myConfig
#    overwriteCheck(myConfig.filename)
    mySaveLabel = Label(root,text="File saved as: "+myConfig.filename).pack()
    print('saving some data! filename: '+myConfig.path)
    
    sampledata = np.arange(int(myConfig.testdatalength))
    
    if myConfig.filetype == ".csv":
        print('saving as a csv file')
        save_to_file.save_to_csv(sampledata,myConfig.path)
    if myConfig.filetype == ".mat":
        print('saving as a mat file')
        save_to_file.save_to_mat(sampledata,myConfig.path)
        
    saveFileButton.config(state=DISABLED)

myFileLabel.pack()
myStartDateLabel.pack()
myTimeDeltaLabel.pack()
myEndDateLabel.pack()

myTestDataLabel = Label(root,text="Length of test data: ")
myTestDataLabel.pack()
### test data entry field
testdata = Entry(root,width=50)
testdata.pack()
testdata.insert(0,10)
###


myDecimationLabel = Label(root,text="Decimate to sampling frequency of:")
myDecimationLabel.pack()
### filetype dropdown menu
decimation = StringVar()
decimation.set("16kHz")
decimation_options = [
        "16kHz",
        "8kHz",
        "4kHz",
        "2kHz",
        "1kHz",
        "500Hz",
        "64Hz",
        "32Hz"
        ] 
decimation_drop = OptionMenu(root, decimation, *decimation_options)
decimation_drop.pack()
###


#input_stop = 
#input_duration = 

updateConfigButton = Button(root, text="Update Save Configuration", command=UpdateConfig)
updateConfigButton.pack()


saveFileButton = Button(root, text="Save File",command=SaveButtonClick, state = DISABLED)
saveFileButton.pack()

root.mainloop()

