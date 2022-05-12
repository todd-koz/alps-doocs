import pydoocs
import pydaq

import csv
import sys
import time
from struct import pack
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import ExitStack, contextmanager
from traceback import format_exc

from scipy import signal
import numpy as np

############################### get_doocs_data ####################################
### This function, adapted from a script written by Sven Karstensen, communicates
### with the DOOCS DAQ server via the function "pydaq.connect" and pulls the data
### via the function "pydaq.getdata()". The data retrieved via this command has a
### dictionary structure with 500 data points contained in channels[0]['data']
### This modified script appends multiple instances of the getdata() output to
### generate a large, continuous data file containing all the data for each channel
### for the time duration specified. unisgned_to_signed is necessary to adapt the 
### DAQ output from unsigned integers to signed integers.
###################################################################################
def unsigned_to_signed(number, maxbits):
    maxn = 2<<(maxbits - 1)
    middle = 2<<(maxbits - 1) - 1
    if number < middle:
        return number
    else:
        return number - maxn

def get_doocs_data(DOOCS_addresses, start, stop,
                   daq="/daq_data/alps",server="ALPS.DAQ/DAQ.SERVER1/DAQ.DATA.SVR/"): 
    try:
        err = pydaq.connect(start=start, stop=stop, ddir=daq, exp='alps', chans=DOOCS_addresses, daqservers=server, local=True)
            
    except pydaq.PyDaqException:
        return format_exc()
    
    if err == []:
        emptycount = 0
        total = 0
        stats_list = []
        chan_all = [[] for ch in DOOCS_addresses]
        summary = ''

        while (emptycount < 1000000):
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
                    subchan  = len(chan)
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

                    data_array=chan[0]['data']
                    data_array_int = np.zeros(len(data_array[0]),int)
                    i=0
                    for x in data_array[0]:
                        data_array_int[i] = unsigned_to_signed(x, 16)
                        i = i+1

                    which = DOOCS_addresses.index(daqname)
                    chan_all[which].append(data_array_int)

            except Exception as err:
                summary += format_exc() + '\n'
                break

        for i in range(len(chan_all)):
            chan_all[i] = np.ravel(chan_all[i])

        summary += f"Total events: {total}, emptycount: {emptycount}\n"
        for stats in stats_list:
            summary += stats['daqname'] + ':\t' + str(stats['events']) + ' events\n'

        pydaq.disconnect()
        return chan_all, summary

########################## get_doocs_data_continuous ##############################
### This function is adapted from a script by Sven Karstensen that communicates
### with the DAQ server via "pydaq.connect()" and pulls data via "pydaq.getdata()".
### This version turns the script into a wrapper for any process that acts on the
### batch of data obtained immediately after each call to "pydaq.getdata()".
###
### This is achieved by accepting another function as one of its arguments called
### "subroutine". If the subroutine requires its own arguments, they can be passed
### as a tuple to an argument of this function called "sub_args". When defining a
### subroutine, it must expect at least 1 argument: a list of dictionaries, each
### with keys 'data', 'daqname', 'macropulse', 'timestamp'.
###
### Finally, this function allows data-processing to be interrupted. It accepts an
### argument called "interrupt", which is any function that returns True/False. By
### default, it is a function that always returns False, which never interrupts.
###################################################################################

def get_doocs_data_continuous(DOOCS_addresses, subroutine, start, stop,
                              sub_args=None,
                              interrupt=lambda : False,
                              daq="/daq_data/alps",
                              server="ALPS.DAQ/DAQ.SERVER1/DAQ.DATA.SVR/"):

    try:
        err = pydaq.connect(start=start, stop=stop, ddir=daq, exp='alps', chans=DOOCS_addresses, daqservers=server, local=True)

    except pydaq.PyDaqException:
        return format_exc()

    if err == []:
        emptycount = 0
        total = 0
        stats_list = []
        summary = ''

        while (emptycount < 1000000):
            try:
                channels = pydaq.getdata()
                if channels == []:
                    emptycount += 1
                    time.sleep(0.001)
                    continue
                if channels == None:
                    break
                total += 1
                
                data_to_subroutine = []

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

                    data_to_subroutine.append( {'data':data_array_int, 'daqname':daqname, 'macropulse':macropulse, 'timestamp':timestamp} )

                if sub_args == None:
                    subroutine(data_to_subroutine)
                else:
                    subroutine(data_to_subroutine, *sub_args)

            except Exception as err:
                summary += format_exc() + '\n'
                break

            if interrupt():
                break

        summary += f"Total events: {total}, emptycount: {emptycount}\n"
        for stats in stats_list:
            summary += stats['daqname'] + ':\t' + str(stats['events']) + ' events\n'

        pydaq.disconnect()
        return summary

################################### MatWriter ###################################
### This class is a custom file-writing handler for .mat files, an alternative to
### scipy's "savemat" function. Scipy's function and the .mat format is not well-
### suited for writing multiple channels of data continuously. As of the current
### version, this class introduces the functionality of saving data continuously
### at the cost of only one channel per file. Thus, every channel of data should
### be saved in its own file when using this class. The variable name in the file
### is fixed as "data". When loading multiple files in MATLAB, one should assign
### each array a new variable name to distinguish between them.
################################################################################

class MatWriter():
    def __init__(self, file, header='MATLAB File'):
        self.file = file
        header = header.strip()
        if len(header) > 124:
            header = header[:124]
        else:
            l = len(header)
            header = header + ' '*(124-l)
        self.header = header
        self.tagcomplete = False

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

    def write(self, arr):
        if not type(arr)==np.ndarray:
            arr = np.array(arr, dtype=np.int16)
        elif not arr.dtype == np.int16:
            arr = arr.astype(np.int16)
        self.file.write( arr.tobytes() )

    ### IMPORTANT: this method must be called after all data is written, before you close the file.
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

        self.tagcomplete = True

    def close(self):
        if self.tagcomplete:
            self.update_tags()
        self.file.close()

@contextmanager
def open_mat_context(path, header):
    f = open(path, 'wb')
    mat_writer = MatWriter(f, header)
    mat_writer.write_preamble()
    try:
        yield mat_writer
    finally:
        mat_writer.update_tags()
        mat_writer.close()

####################### EXAMPLE #######################
### using "get_doocs_data_continuous()" and MatWriter()

### define the subroutine
def save_mat_subroutine(data_dict, channels, writers, decimationFactor=1):
    for i in range(len(data_dict)):
        decimated_data = downsample(data_dict[i]['data'], decimationFactor)
        which = channels.index( data_dict[i]['daqname'] )
        writers[which].write( decimated_data )

### Main program
def save_mat_custom(channels, filepaths, start, stop,
                    daq="/daq_data/alps", server="ALPS.DAQ/DAQ.SERVER1/DAQ.DATA.SVR/"):

    ### appending '.mat' extension if not already there
    filepaths = [fpath + '.mat'*(not fpath[-4:]=='.mat') for fpath in filepaths]

    ### using ExitStack as the context manager because there are variable number of files to open
    with ExitStack() as stack:
        files = [stack.enter_context(open(fpath, 'wb')) for fpath in filepaths]
        mat_writers = []

        for i in range(len(files)):
            header_text = channels[i] + ' from ' + start + ' until ' + stop
            mat_writers.append( MatWriter(files[i], header=header_text) )
            mat_writers[i].write_preamble()

        result = get_doocs_data_continuous(channels, save_mat_subroutine,
                                           start=start, stop=stop,
                                           daq=daq, server=server,
                                           sub_args=(channels, mat_writers))

        ### IMPORTANT: always call the .update_tags() method at the end of writing files
        for i in range(len(mat_writers)):
            mat_writers[i].update_tags()

    return result

#########################################################################
### The following code uses the pydoocs.read() function to save data from
### DOOCS channels to CSV files. These DOOCS channels are ones not on a
### DAQ server. It is assumed that they have an associated channel with
### the same address but suffixed by ".HIST" and that the sampling rates
### are slow.

### Reading a ".HIST" address returns a dict with an item labeled "data",
### which is a list of tuples of the form (timestamp, data, macropulse).
### The length of the list is fixed and past data is no longer available
### after some time. Thus the following code only records data starting
### at the time of call. If saving multiple channels of data, the tasks
### must be run in parallel to reduce the risk of data from one channel
### being removed while data from another channel is being logged. Thus,
### the tasks are handled by ThreadPoolExecutor from the python module
### "concurrent.futures".

### The difference in time between each timestamp can vary. Thus, both
### the timestamps and data are recorded. Each row of the file is a time-
### data pair, separated by a comma.
#########################################################################

def remove_overlap_timestamp(past_data, new_data):
    latest_timestamp = past_data[-1,0]
    new_timestamps = new_data[:,0]

    new_start_pos = len(new_data)

    for i in range(start=len(new_data)-1, stop=-1, step=-1):
        if new_timestamps[i] <= latest_timestamp:
            break
        else:
            new_start_pos -= 1
    return new_data[new_start_pos:,:]

def pydoocs_save_csv(channel, filepath, duration):
    hist = np.array(pydoocs.read(channel+'.HIST')['data'])[:,:2]
    past = np.zeros(hist.shape)
    t0 = hist[0,0]

    with open(filepath, 'w', newline='') as file:
        writer = csv.writer(file)
        while True:
            dt = hist[-1,0] - t0
            if dt <= duration:
                hist_timechecked = remove_overlap_timestamp(past, hist)
                if any(hist_timechecked):
                    writer.writerows(hist_timechecked)
                past = hist
                hist = np.array(pydoocs.read(channel+'.HIST')['data'])[:,:2]
            else:
                stop = len(hist)-1
                while hist[stop,0] - t0 > duration:
                    stop -= 1
                hist = hist[:stop+1,:]
                hist_timechecked = remove_overlap_timestamp(past, hist)
                if any(hist_timechecked):
                    writer.writerows(hist_timechecked)
    return t0, hist[-1,0]

def pydoocs_save_csv_multiple(channels, filepaths, duration):
    nch = len(channels)
    executor = ThreadPoolExecutor(max_workers=nch)
    tasks = [executor.submit(pydoocs_save_csv,
                             channels[i],
                             filepaths[i],
                             duration) for i in range(nch)]
    done = [False]*nch
    result = [None]*nch
    while sum(done) < nch:
        for i in range(len(tasks)):
            if not done[i]:
                try:
                    out = tasks[i].result(timeout=1)
                    done[i] = True
                    result[i] = out
                except TimeoutError:
                    continue
            else: continue
    return result

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

################ miscellaneous utility functions ################

def downsample(arr, factor):
    factor = int(factor)
    #### scipy's advice to run decimate multiple times if factor is big
    while factor > 8:
        arr = signal.decimate(arr, 8)
        factor = factor // 8
    if factor > 1:
        arr = signal.decimate(arr, factor)
    return arr
