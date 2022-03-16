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
import numpy as np
from tkcalendar import DateEntry
from datetime import datetime
from datetime import timedelta
import alpsdoocslib
import os
import os.path
from example_data import *
from pathlib import Path

root = Tk()
root.title('ALPS DOOCS Save Data')
#root.geometry("400x600")

### generate a class of configuration object
class saveConfig(object):
    pass
myConfig = saveConfig()

### unique exception to be flagged when asking for data that hasn't been recorded yet
class DateError(Exception):
    """The measurement end time has not yet been reached. Measurement end must be in the past."""
    pass

###################### overwriteCheck #########################################
### checks if the file name already exists, and if it does, prompts the user 
### with a pop up asking for explicit overwrite permission. Returns boolean of
### whether to proceed with the save or not.
###############################################################################
def overwriteCheck(filename):
    overwrite = True
    if os.path.exists(filename):
        overwrite = askyesno("Overwrite","A file with this name already exists. Do you want to overwrite?")
        if overwrite == True:
            print('Overwriting file!!')
    return overwrite


###################### dateisPast #############################################
### checks if the projected end of the data pull is in the past. 
###############################################################################
def dateisPast(date):
    return datetime.now()>myConfig.stop_datetime


###################### oversizeCheck ##########################################
### checks if the file expected size is in excess of 1.0GB. If so, it prompts 
### with a pop up asking for explicit permission to continue. Returns boolean of
### whether to proceed with the save or not.
############################################################################### 
def oversizeCheck(filesize):
    writeoversize = True
    if filesize > 1e10:
        writeoversize = askyesno("Oversize","The expected filesize is "+str(round(filesize/1e3,-1))+" GB. Are you sure you want to proceed?")
    return writeoversize


############################### UpdateConfig() ################################
### Function called when pressing the "Update Configuration" button. This function
### populates all the entry parameters provided by the user as attributes of "myConfig" object
def UpdateConfig():
    try:
        global myConfig
        myConfig.channels=[channel1select.get(),channel2select.get(),channel3select.get(),channel4select.get()]
        myConfig.channelcomments=[channel1Comment.get(),channel2Comment.get(),channel3Comment.get(),channel4Comment.get()]  
        myConfig.filename=filename.get()
        myConfig.filetype=filetype.get()
        myConfig.time=[int(duration_d.get()),int(duration_h.get()),int(duration_m.get()),int(duration_s.get())]
        myConfig.mytimedelta = timedelta(days=myConfig.time[0],hours=myConfig.time[1],minutes=myConfig.time[2],seconds=myConfig.time[3])
        myConfig.start_datetime = datetime.strptime(startdate.get()+starttime.get(), "%Y-%m-%d%H:%M:%S")
        myConfig.stop_datetime = myConfig.start_datetime + myConfig.mytimedelta
        myConfig.input_start = myConfig.start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        myConfig.input_stop = myConfig.stop_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        myConfig.path = directory.get()+myConfig.filename+myConfig.filetype
        myConfig.dirpath = directory.get()
        myConfig.usercomment = usercommentBox.get("1.0",END)
        
        ### checks the measurement duration is entirely in the past
        if not dateisPast(myConfig.stop_datetime):
            raise DateError
        
        ### checks the number of channels to save data from, based on how many channels are not left "None"
        numChannels = 0
        if myConfig.channels[0] != "None":
            numChannels += 1
        if myConfig.channels[1] != "None":
            numChannels += 1
        if myConfig.channels[2] != "None":
            numChannels += 1
        if myConfig.channels[3] != "None":
            numChannels += 1
                
        myConfig.decimation=decimation.get()
        myConfig.decimationFactor = 16000 / decimationVal[decimation.get()] #calculates the factor by which data is decimated,
                                                                            # e.g. for downsample from 16kHz to 8kHz, the factor is 2
        
        myConfig.filesize = decimationVal[decimation.get()]*8*myConfig.mytimedelta.total_seconds()*numChannels/1e6 ## estimates the output filesize in MB
        myConfig.configSummary = (
                                    f"\n###########################################################"
                                    f"\nFile save configuration overview."
                                    f"\n   This will save data to: {myConfig.path}"
                                    f"\n   Data start time: {myConfig.start_datetime}"
                                    f"\n   Data stop time: {myConfig.stop_datetime}"
                                    f"\n   Data Duration: {myConfig.mytimedelta}"
                                    f"\n   Sampling rate: {myConfig.decimation}"
                                    f"\n   Saving on Channel 1: {myConfig.channels[0]} ..... channel label: {myConfig.channelcomments[0]}"
                                    f"\n   Saving on Channel 2: {myConfig.channels[1]} ..... channel label: {myConfig.channelcomments[1]}"
                                    f"\n   Saving on Channel 3: {myConfig.channels[2]} ..... channel label: {myConfig.channelcomments[2]}"
                                    f"\n   Saving on Channel 4: {myConfig.channels[3]} ..... channel label: {myConfig.channelcomments[3]}\n"
                                  )
        consoleBox.config(state=NORMAL)
        consoleBox.insert('insert',myConfig.configSummary)
        consoleBox.tag_config('warning',foreground="red")
        if myConfig.filesize > 1e9:
            consoleBox.insert('insert',f"\n   CAUTION!! Estimated output file size: {myConfig.filesize} MB",'warning')
        else:
            consoleBox.insert('insert',f"\n   Estimated output file size: {myConfig.filesize} MB")
        consoleBox.see(END)
        consoleBox.config(state=DISABLED)
        saveFileButton.config(state = NORMAL)
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

    ### strips away channels left as "None" from the daqchannels list    
    myConfig.daqchannels=[value for value in myConfig.channels if value != 'None']
        
    
    
########################### SaveButtonClick() #################################    
### Function called when pressing the "Save Data" button. This function calls the 
### get_doocs_data function (from alpsdoocslib) to populate up to four variables with
### data from DAQ. First checks the file size and file name iwth oversizeCheck and 
### overwriteCheck (both from alpsdoocslib) to make sure the destination file is not
### oversized or overwriting another file without explicit permission.
def SaveButtonClick():
    global myConfig
    if oversizeCheck(myConfig.filesize):   
        if overwriteCheck(myConfig.path):
            print(f'Saving some data! filename: {myConfig.path}')
######### Temporary substitution of sample data for testing ###################
            ch1data = getdata_sample[0]['data']
            ch2data,ch3data,ch4data = [],[],[]
###############################################################################
            channels = ['ALPS.DIAG/ALPS.ADC.'+s for s in myConfig.daqchannels] ### generates channels names in the format desired by get_doocs_data
            start = myConfig.input_start  ### generates start time in the format desired by get_doocs_data
            stop = myConfig.input_stop    ### generates stop time in the format desired by get_doocs_data
#            [ch1data,ch2data,ch3data,ch4data,stats] = alpsdoocslib.get_doocs_data(channels=channels,start=start,stop=stop)
            datas=[ch1data,ch2data,ch3data,ch4data]   ### combines all data from all channels in single list-of-lists 
            datas=[x for x in datas if len(x)>0]      ### strips away all empty data channels
            
            
            ### Calls to the decimate_data function in alpsdoocslib which applies
            ### a decimation algorithm to reduce the data length
            if myConfig.decimation != "16kHz":
                for datas in datas:
                    datas = alpsdoocslib.decimate_data(datas, int(myConfig.decimationFactor))

                                                
            if myConfig.filetype == ".csv":
                print('saving as a csv file')
#                alpsdoocslib.save_to_csv(sampledata,myConfig.path)
            if myConfig.filetype == ".mat":
                print('Saving data as a .mat file.')

                channels=myConfig.daqchannels
                labels=myConfig.channelcomments
                fs=decimationVal[decimation.get()]
                path=myConfig.path
                events=10
                alpsdoocslib.save_to_mat(datas=datas,labels=labels,channels=channels,fs=fs,path=path,events=events)
    saveConfigFile()
    saveFileButton.config(state=DISABLED)


######################### saveConfigFile() ####################################
### saves a text file containing the configuration settings and user comments
def saveConfigFile():
    global myConfig
    with open(myConfig.dirpath+myConfig.filename+'_config_file.txt', 'w') as f:
        f.write(myConfig.configSummary)
        f.write("\n\nUser Comments: \n  ")
        f.write(myConfig.usercomment)
    print('Saving configuration text file!')

########################################################################
########################################################################
########################################################################

### entry field labels
channelsLabel = Label(root,text="Select channels ")
channel1Label = Label(root,text="Channel 1:")
channel2Label = Label(root,text="Channel 2:")
channel3Label = Label(root,text="Channel 3:")
channel4Label = Label(root,text="Channel 4:")
filetypeLabel = Label(root,text="Filetype: ")
directoryLabel = Label(root,text="Save Directory: ")
filenameLabel = Label(root,text="Filename: ")
startdateLabel = Label(root,text="Data start date: ")
starttimeLabel = Label(root,text="Data start time: ")
durationLabel = Label(root,text="Duration: ")
daysLabel = Label(root,text="Days:")
hoursLabel = Label(root,text="Hours:")
minutesLabel = Label(root,text="Minutes:")
secondsLabel = Label(root,text="Seconds:")
usercommentsLabel = Label(root,text="Enter additional user comments about this measurement/data. \nThese additional comments will be saved as a .txt file in the destination directory.")

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


### filetype dropdown menu
filetype = StringVar()
filetype.set(".mat")
filetype_options = [
        ".mat",
        ".csv"
        ] 
filetype_drop = OptionMenu(root, filetype, filetype_options[0], *filetype_options)
###

########### destination directory entry field #################################
directory = Entry(root,width=50,justify='right')
directory.insert(0,os.getcwd())
directory.xview_moveto(1)
###

########### channel user comments #############################################
channel1Comment = Entry(root,width=10)
channel1Comment.insert(0,"")
channel2Comment = Entry(root,width=10)
channel2Comment.insert(0,"")
channel3Comment = Entry(root,width=10)
channel3Comment.insert(0,"")
channel4Comment = Entry(root,width=10)
channel4Comment.insert(0,"")
###

############### file name entry field #########################################
filename = Entry(root,width=50)
filename.insert(0,"default_filename")
### 

### start date entry field
startdate = Entry(root,width=50)
startdate.insert(0,datetime.today().strftime('%Y-%m-%d'))
### 

### start time entry field
starttime = Entry(root,width=50)
starttime.insert(0,datetime.today().strftime('%H:%M:%S'))
### 

### duration days entry field
duration_d = Entry(root,width=10)
duration_d.insert(0,0)

### duration hours entry field
duration_h = Entry(root,width=10)
duration_h.insert(0,0)

### duration minutes entry field
duration_m = Entry(root,width=10)
duration_m.insert(0,0)

### duration seconds entry field
duration_s = Entry(root,width=10)
duration_s.insert(0,10)

mytimedelta=timedelta(days=int(duration_d.get()),hours=int(duration_h.get()),minutes=int(duration_m.get()),seconds=int(duration_s.get()))
mystarttime=datetime.strptime(startdate.get()+starttime.get(), "%Y-%m-%d%H:%M:%S")

myFileLabel = Label(root,text=filename.get()+filetype.get())
myStartDateLabel = Label(root,text=mystarttime)
myTimeDeltaLabel = Label(root,text=mytimedelta)
myEndDateLabel = Label(root,text=mystarttime+mytimedelta)

myDecimationLabel = Label(root,text="Downsample to:")
### filetype dropdown menu
decimation=StringVar()
decimationVal = {
        "16kHz": 16000,
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
##




#input_stop = 
#input_duration = 

updateConfigButton = Button(root, text="Update Save Configuration", command=UpdateConfig)
saveFileButton = Button(root, text="Save File",command=SaveButtonClick, state = DISABLED)

### Labels
filetypeLabel.grid(row=0,column=0,sticky=W,pady=2)
directoryLabel.grid(row=1,column=0,sticky=W,pady=2)
filenameLabel.grid(row=2,column=0,sticky=W,pady=2)
startdateLabel.grid(row=3,column=0,sticky=W,pady=2)
starttimeLabel.grid(row=4,column=0,sticky=W,pady=2)
durationLabel.grid(row=5,column=0,sticky=W,pady=2)
daysLabel.grid(row=5,column=1,sticky=W,pady=2)
hoursLabel.grid(row=5,column=2,sticky=W,pady=2)
minutesLabel.grid(row=5,column=3,sticky=W,pady=2)
secondsLabel.grid(row=5,column=4,sticky=W,pady=2)

### Entry fields
filetype_drop.grid(row=0,column=1,sticky=W,pady=2)
directory.grid(row=1,column=1,sticky=W,pady=2,columnspan=4)
filename.grid(row=2,column=1,sticky=W,pady=2,columnspan=4)
startdate.grid(row=3,column=1,sticky=W,pady=2,columnspan=4)
starttime.grid(row=4,column=1,sticky=W,pady=2,columnspan=4)
duration_d.grid(row=6,column=1,sticky=W,pady=2)
duration_h.grid(row=6,column=2,sticky=W,pady=2)
duration_m.grid(row=6,column=3,sticky=W,pady=2)
duration_s.grid(row=6,column=4,sticky=W,pady=2)

### Buttons
updateConfigButton.grid(row=27,column=1,sticky=W,pady=2,columnspan=3)
saveFileButton.grid(row=80,column=1,sticky=W,pady=2)

### Channels info
channelsLabel.grid(row=14,column=0,sticky=W,pady=2,columnspan=1)
channel1Label.grid(row=15,column=1,sticky=W,pady=2,columnspan=1)
channel2Label.grid(row=15,column=2,sticky=W,pady=2,columnspan=1)
channel3Label.grid(row=15,column=3,sticky=W,pady=2,columnspan=1)
channel4Label.grid(row=15,column=4,sticky=W,pady=2,columnspan=1)

### Channel drops
channel1_drop.grid(row=16,column=1,sticky=W,pady=2,columnspan=1)
channel2_drop.grid(row=16,column=2,sticky=W,pady=2,columnspan=1)
channel3_drop.grid(row=16,column=3,sticky=W,pady=2,columnspan=1)
channel4_drop.grid(row=16,column=4,sticky=W,pady=2,columnspan=1)

### Channel comments
channelComments = Label(root,text="Channel label: ").grid(row=17,column=0,sticky=W,pady=2)

channel1Comment.grid(row=17,column=1,sticky=W,pady=2,columnspan=1)
channel2Comment.grid(row=17,column=2,sticky=W,pady=2,columnspan=1)
channel3Comment.grid(row=17,column=3,sticky=W,pady=2,columnspan=1)
channel4Comment.grid(row=17,column=4,sticky=W,pady=2,columnspan=1)

### Decimation
myDecimationLabel.grid(row=18,column=0,sticky=W,pady=2,columnspan=1)
decimation_drop.grid(row=18,column=1,sticky=W,pady=2,columnspan=1)

### user comments space
usercommentsLabel.grid(row=47,column=0,sticky=W,pady=2,columnspan=5)
usercommentFrame = Frame(root)
usercommentFrame.grid(row=48,column=0,sticky=W,pady=2,columnspan=5)

usercommentBox = Text(usercommentFrame,wrap=WORD,height=5)
usercommentBox.grid(row=49,column=0)
usercommentBox.config(state=NORMAL)

### configuration logging space
consoleFrame = Frame(root)
consoleFrame.grid(row=50,column=0,sticky=W,pady=2,columnspan=5)

consoleBox = scrolledtext.ScrolledText(consoleFrame,wrap=WORD)
consoleBox.grid(row=51,column=0)
consoleBox.config(state=DISABLED)

root.mainloop()

