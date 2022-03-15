#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 16:49:11 2022

Function library for ALPS - DOOCS python software

@author: todd
"""
import csv
from scipy.io import savemat
from scipy import signal
import sys
#import pydoocs
#import pydaq
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

