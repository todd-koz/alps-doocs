#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 16:49:11 2022

Function library for ALPS - DOOCS python software

@author: todd, daniel
"""
import csv
from scipy.io import savemat
from scipy import signal
import sys
import time
from struct import pack
from datetime import datetime, timedelta
import pydoocs
import pydaq
import numpy as np

########################### save_to_csv #######################################
### This function
###############################################################################
def save_to_csv(data,path):
    with open(path,'w') as f:
            writer = csv.writer(f)
            writer.writerow(data)
     
        
########################### save_to_mat #######################################
### This function saves data to a .mat file. The scipy function "savemat" accepts
### a single keyed dictionary. The format of this dictionary is as follows:
### {"fs": sampling frequency
###  "t0": start time, in seconds UTC time
###  "channeln_label": label for each channel n
###  "channeln_channelname": the DAQ channel name for each channel n
###  "channeln_data": the full raw data for each channel n
### }
###############################################################################
def save_to_mat(datas,channels,path,events,labels,fs=16000,starttime=0):
    matlabVariable = {"fs":fs,"t0":starttime}
    for i in range(len(datas)):
        matlabVariable[f'channel{i+1}_label'] = labels[i]
        matlabVariable[f'channel{i+1}_channelname'] = channels[i]
        matlabVariable[f'channel{i+1}_data'] = datas[i]        
    savemat(path,matlabVariable)


###################### decimate_data ##########################################
### decimates data using signal.decimate function
###############################################################################
def decimate_data(data,decimation):
    out = signal.decimate(data,decimation)
    return out


############################# get_doocs_data ##################################
### This function, adapted from a script written by Sven Karstensen, communicates
### with the DOOCS DAQ server via the function "pydaq.connect" and pulls the data
### via the function "pydaq.getdata()". The data retrieved via this command has a
### dictionary structure with 500 data points contained in channels[0]['data']
### This modified script appends multiple instances of the getdata() output to
### generate a large, continuous data file containing all the data for each channel
### for the time duration specified. unisgned_to_signed is necessary to adapt the 
### DAQ output from unsigned integers to signed integers.
###############################################################################
def unsigned_to_signed(number, maxbits):
    maxn = 2<<(maxbits - 1)
    middle = 2<<(maxbits - 1) - 1
    if number < middle:
        return number
    else:
        return number - maxn

def get_doocs_data(chans,start,stop,daq="/daq_data/alps",server="TTF2.DAQ/DAQ.SERVER5/DAQ.DATA.SVR/"):
#    chans=['ALPS.DIAG/ALPS.ADC.HN/CH_1.00','ALPS.DIAG/ALPS.ADC.HN/CH_1.01']
#    start_time="2022-01-03T12:23:00"
#    stop_time= "2022-01-03T12:23:01"  
    try:
       # for NAF environment on NAF cluster
        err = pydaq.connect(start=start, stop=stop, ddir=daq_taking_data, exp='alps', chans=chans, daqservers=daqservers)
            
    except pydaq.PyDaqException as err:
        print('Something wrong with daqconnect... exiting')
        print(err)
        sys.exit(-1)
    
    
    if err == []:
        stop = False
        emptycount = 0
        total = 0
        stats_list = []
        chan1_all = []
        chan2_all = []
        chan3_all = []
        chan4_all = []
        while not stop and (emptycount < 1000000):    
            try:
                channels = pydaq.getdata()
                if channels == []:
                    emptycount += 1
                    time.sleep(0.001)
                    continue
                if channels == None:
                    break
                total += 1
                
                print("\nEvent: %d"%total)
                for chan in channels:
                    subchan  = len(chan)
                    daqname = chan[0]['miscellaneous']['daqname']
                    macropulse = chan[0]['macropulse']
                    timestamp = chan[0]['timestamp']
                    found = False
                    chtotal = 0
                    for stats in stats_list:
                        if stats['daqname'] == daqname:
                            stats['events'] += 1
                            chtotal = stats['events']
                            found = True
                            break
                    if not found:
                        entry = {}
                        entry['daqname'] = daqname
                        entry['events'] = 1
                        chtotal = entry['events']
                        stats_list.append(entry)
                        
                    #print("daqname = " + daqname)
                    print("\nmacropulse = " + str(macropulse) + "  prop:" + daqname + "  time:"+ str(timestamp))
                    data_array=chan[0]['data']
                    data_array_int = np.zeros(len(data_array[0]),int)
                    i=0
                    
                    # !!! IMPORTANT !!! convert from unsigned to signed.
                    for x in data_array[0]:
                        data_array_int[i] = unsigned_to_signed(x, 16)
                        i=i+1
                    
                    if daqname == chans[0]:
                        chan1_all = np.append(chan1_all,data_array_int)
                    if daqname == chans[1]:
                        chan2_all = np.append(chan2_all,data_array_int)
                    if daqname == chans[2]:
                        chan3_all = np.append(chan3_all,data_array_int)
                    if daqname == chans[3]:
                        chan4_all = np.append(chan4_all,data_array_int)
                    print('length of macropulse data = ' + str(len(data_array_int)))
                emptycount = 0
            except Exception as err:    
                print('Something wrong ... stopping %s'%str(err))
                stop = True
    
    
        print('\nSummary:\nTotal events: %d emptycount %d'% (total, emptycount))
        for stats in stats_list:
            print(stats['daqname'], ':\t', stats['events'], 'events')
        pydaq.disconnect()
        
    return chan1_all,chan2_all,chan3_all,chan4_all,stats_list


########################## signal_process #####################################
### Uses the GWpy library of signal processing tools to filter and analyze data
### by converting to a TimeSeries object, then subjecting it to GWpy function to
### filter or generate FrequencySeries objects. Returns raw data for plotting.
###############################################################################
def signal_process(data,fs=16000,t0=0,process="None",filtertype="None",filterfreq=0,flow=0,fhigh=0,zeros=[],poles=[],gain=0):
    myTS = TimeSeries(data=data[0])
    if filtertype=="lowpass":
        myTS = myTS.lowpass(frequency=filterfreq)
    if filtertype=="highpass":
        myTS = myTS.highpass(frequency=filterfreq)
    if filtertype=="bandpass":
        myTS = myTS.bandpass(flow=flow,fhigh=fhigh)
    if filtertype=="zpk":
        myTS = myTS.zpk(zeros=zeros,poles=poles,gain=gain)
        
    if process=="None":
        print('Plotting a time series')
        return myTS
    if process=="ASD":
        myASD = myTS.asd(fftlength,overlap,window,method)
        return myASD
    if process=="PSD":
        myPSD = myTS.psd(fftlength,overlap,window,method)
        return myPSD

######################### process_doocs_data_continuous #########################
### This function is adapted from a script by Sven Karstensen and Todd Kozlowski
### that communicates with the DAQ server via "pydaq.connect()" and pulls data
### via "pydaq.getdata()". This version turns the script into a wrapper for any
### process that acts on the batch of data obtained immediately after each call
### to "pydaq.getdata()".
###
### This is achieved by accepting another function as one of its arguments called
### "subroutine". If the subroutine requires its own arguments, they can be passed
### as a tuple to an argument of this function called "sub_args". When defining
### a subroutine, at least 5 arguments are required: data, daqname, macropulse,
### timestamp, and event_count. These 5 will be automatically passed to the sub-
### routine before those contained in "sub_args" are passed.
##################################################################################

def process_doocs_data_continuous(DOOCS_addresses,
                                   subroutine,
                                   start="2022-03-01T00:00:01",
                                   stop="2022-03-01T00:01:01",
                                   daq="/daq_data/alps",
                                   server="TTF2.DAQ/DAQ.SERVER5/DAQ.DATA.SVR/",
                                   sub_args=(None,)):

    try:
       # for NAF environment on NAF cluster
        err = pydaq.connect(start=start, stop=stop, ddir=daq, exp='alps', chans=DOOCS_addresses, daqservers=server)

    except pydaq.PyDaqException as err:
        print('Something wrong with daqconnect... exiting')
        print(err)
        sys.exit(-1)

    if err == []:

        stop = False
        emptycount = 0
        total = 0
        stats_list = []
        while not stop and (emptycount < 1000000):
            try:
                channels = pydaq.getdata()
                if channels == []:
                    emptycount += 1
                    time.sleep(0.001)
                    continue
                if channels == None:
                    break
                total += 1

                for chan in channels:
                    daqname = chan[0]['miscellaneous']['daqname']
                    macropulse = chan[0]['macropulse']
                    timestamp = chan[0]['timestamp']
                    found = False
                    for stats in stats_list:
                        if stats['daqname'] == daqname:
                            stats['events'] += 1
                            found = True
                            break
                    if not found:
                        entry = {}
                        entry['daqname'] = daqname
                        entry['events'] = 1
                        stats_list.append(entry)

                    data_array = chan[0]['data']
                    data_array_int = np.zeros(len(data_array[0]), np.int16)
                    i = 0
                    for x in data_array[0]:
                        data_array_int[i] = unsigned_to_signed(x, 16)
                        i += 1

                    if sub_args==(None,):
                        subroutine(data_array_int, daqname, macropulse, timestamp, total)
                    else:
                        subroutine(data_array_int, daqname, macropulse, timestamp, total, *sub_args)

            except Exception as err:
                print('Something wrong ... stopping %s'%str(err))
                stop = True

        print('\nSummary:\nTotal events: %d emptycount %d'% (total, emptycount))
        for stats in stats_list:
            print(stats['daqname'], ':\t', stats['events'], 'events')
        pydaq.disconnect()

################################### MatWriter ###################################
### This is a custom file writing handler for .mat files, to be an alternative to
### scipy's "savemat" function. Scipy's function and the .mat binary format itself
### ill-suited for writing multiple channels of data in batches. As of the current
### version, this class introduces the functionality of saving data in batches, at
### the cost of being only able to save one channel of data per file. Thus, every
### channel of data should be saved in its own file when using this class.
###
### As of this current version, the variable name assigned to the array is "data"
### by default. To access the array in Matlab, one should call "load()" with the
### string "data" passed as an argument. The first 124 bytes of a .mat binary is
### human-readable text, and can be accessed on Unix-based terminals with the
### command "head -c 124 filename.mat". Meta-data can be saved into the file at
### the end, after data-collection is done (but this has yet to be implemented).
################################################################################

class MatWriter():
    def __init__(self, file, header=' '*124):
        self.file = file
        if len(header) > 124:
            print(f"Header text is too long. Truncated to \"{header[:124]}\"")
            header = header[:124]
        else:
            l = len(header)
            header = header + ' '*(124-l)
        self.header = header

    def write_preamble(self):
        header = pack('124c', *[self.header[i].encode('ascii') for i in range(124)])
        version = pack('H', 256)
        endian = np.ndarray(shape=(), dtype='S2', buffer=np.uint16(0x4d49)).tobytes()
        tagMatrix = pack('II', 14, 0)
        tagClass = pack('II', 6, 8)
        valueClass = pack('II', 10, 0)
        tagDimensions = pack('II', 5, 8)
        valueDimensions = pack('ii', 1, 0)
        matrixName = np.array((1, 0, 4, 0, 0x64, 0x61, 0x74, 0x61), dtype=np.uint8 ).tobytes()
        tagActualData = pack('II', 3, 0)

        self.file.write(header)
        self.file.write(version)
        self.file.write(endian)
        self.file.write(tagMatrix)
        self.file.write(tagClass)
        self.file.write(valueClass)
        self.file.write(tagDimensions)
        self.file.write(valueDimensions)
        self.file.write(matrixName)
        self.file.write(tagActualData)

    def write_data(self, arr):
        self.file.write( arr.tobytes() )

#   ### IMPORTANT: this method must be called after all data is written, before you close the file.
    def update_tags(self):
        current_pos = self.file.tell()
        pos = {'byte count tot': 132, 'dims': 164, 'byte count vector': 180}

        byte_count_vec = current_pos - pos['byte count vector'] - 4
        size = byte_count_vec // 2
        byte_count_tot = current_pos - pos['byte count tot'] - 4

        mod_8 = current_pos % 8
        if mod_8:
            file.write(b'\x00' * (8-mod_8))

        byte_count_tot += (8-mod_8)

        self.file.seek( pos['byte count tot'] )
        self.file.write( pack('I', byte_count_tot) )

        self.file.seek( pos['dims'] )
        self.file.write( pack('i', size) )

        self.file.seek( pos['byte count vector'] )
        self.file.write( pack('I', byte_count_vec) )

        self.file.seek( byte_count_tot )

#################### EXAMPLE ####################
# using "process_doocs_data_continuous()" and MatWriter()

def printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 50, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    bar = fill * filledLength + '-' * (length - filledLength)
    if iteration == total:
        print()

### define the subroutine
def save_mat_subroutine(data, daqname, macropulse, timestamp, event_count, channels, writers, total_events):
    if daqname in channels:
        which = channels.index(daqname)
        writers[which].write_data( data )

        if (which == 0) and (event_count % 100 == 0):
            printProgressBar(event_count, total_events, prefix='Progress:', suffix="Complete")

### Main program
def save_to_mat_custom(channels, filenames, comments,
                start, stop, daq="/daq_data/alps", server="TTF2.DAQ/DAQ.SERVER5/DAQ.DATA.SVR/"):

    ### appending '.mat' extension if not already there
    filenames = [filenames[i]+'.mat'*(not filenames[i][-4:]=='.mat') for i in range(len(filenames))]

    # calculate total number of events for progress bar
    starttime = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
    stoptime = datetime.strptime(stop, "%Y-%m-%dT%H:%M:%S")
    duration = (stoptime - starttime).seconds
    tot_events_calc = duration * 32

    ### using ExitStack as the context manager because there are variable number of files to open
    from contextlib import ExitStack
    with ExitStack() as stack:
        files = [stack.enter_context(open(file_name, 'wb')) for file_name in filenames]
        mat_writers = []

        for i in range(len(files)):
            header_text = channels[i] + ' from ' + start + ' until ' + stop + ' ' + comments[i]
            mat_writers.append( MatWriter(files[i], header=header_text) )
            mat_writers[i].write_preamble()

        process_doocs_data_continuous(channels, save_mat_subroutine,
                                      start=start, stop=stop,
                                      daq=daq, server=server,
                                      sub_args=(channels,mat_writers, tot_events_calc))

        ### IMPORTANT: always call the .update_tags() method at the end of writing files
        for i in range(len(mat_writers)):
            mat_writers[i].update_tags()

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
