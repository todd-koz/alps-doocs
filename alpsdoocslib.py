import pydoocs
import pydaq

import csv
import sys
import time
from struct import pack, unpack
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import ExitStack, contextmanager
from traceback import format_exc

from scipy import signal
import numpy as np


def unsigned_to_signed(number, maxbits):
    maxn = 2<<(maxbits - 1)
    middle = 2<<(maxbits - 1) - 1
    if number < middle:
        return number
    else:
        return number - maxn

def get_doocs_data(DOOCS_addresses, start, stop,
                   daq="/daq_data/alps", server="ALPS.DAQ/DAQ.SERVER1/DAQ.DATA.SVR/"): 
    """
    This function, adapted from a script written by Sven Karstensen, communicates
    with the DOOCS DAQ server via the function "pydaq.connect" and pulls the data
    via the function "pydaq.getdata()". The data retrieved via this command has a
    dictionary structure with 500 data points contained in channels[0]['data']
    This modified script appends multiple instances of the getdata() output to
    generate a large, continuous data file containing all the data for each channel
    for the time duration specified. unisgned_to_signed is necessary to adapt the 
    DAQ output from unsigned integers to signed integers.
    """

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


def get_doocs_data_continuous(DOOCS_addresses, subroutine, start, stop,
                              sub_args=None,
                              interrupt=lambda : False,
                              daq="/daq_data/alps",
                              server="ALPS.DAQ/DAQ.SERVER1/DAQ.DATA.SVR/"):
    """
    This function is adapted from a script by Sven Karstensen that communicates
    with the DAQ server via "pydaq.connect()" and pulls data via "pydaq.getdata()".
    This version turns the script into a wrapper for any process that acts on the
    batch of data obtained immediately after each call to "pydaq.getdata()".
   
    This is achieved by accepting another function as one of its arguments called
    "subroutine". If the subroutine requires its own arguments, they can be passed
    as a tuple to an argument of this function called "sub_args". When defining a
    subroutine, it must expect at least 1 argument: a list of dictionaries, each
    with keys 'data', 'daqname', 'macropulse', 'timestamp'.
   
    Finally, this function allows data-processing to be interrupted. It accepts an
    argument called "interrupt", which is any function that returns True/False. By
    default, it is a function that always returns False, which never interrupts.
    """

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

############################################################

class BaseMatNpyFile():
    MCLASS         = {'double': 6          , 'int16': 10}
    MTYPE          = {'double': 9          , 'int16': 3}
    BYTES          = {'double': 8          , 'int16': 2}
    NPY_TYPE       = {'double': np.float64 , 'int16': np.int16}
    NPY_TYPE_LABEL = {'double': '<f8'      , 'int16': '<i2'}

class BaseMatNpyReader(BaseMatNpyFile):
    def __init__(self, filepath, dtype):
        super().__init__()
        self.file = open(filepath, 'rb')
        self.bytes_per_num = self.BYTES[dtype]
        self.dtype = self.NPY_TYPE[dtype]

    def tell(self):
        return self.file.tell()

    def seek(self, pos):
        self.file.seek(pos)

    def close(self):
        self.file.close()

class MatReader(BaseMatNpyReader):
    def __init__(self, filepath, dtype):
        super().__init__(filepath, dtype)
        self.file.seek(180)
        self.EOF_pos = unpack('I', self.file.read(4))[0] + 184

    def read(self, N):
        B = N*self.bytes_per_num
        if B + self.tell() > self.EOF_pos:
            b = self.file.read( self.EOF_pos - self.tell() )
        else:
            b = self.file.read( B )
        if b==b'':
            raise EOFError
        else:
            nums = np.frombuffer(b, dtype=self.dtype)
            return nums

class NpyReader(BaseMatNpyReader):
    def __init__(self, filepath, dtype):
        super().__init__(filepath, dtype)
        self.file.seek(128)

    def read(self, N):
        B = N*self.bytes_per_num
        b = self.file.read( B )
        if b==b'':
            raise EOFError
        else:
            nums = np.frombuffer(b, dtype=self.dtype)
            return nums

class MatWriter(BaseMatNpyFile):
    """
    This class is a custom file-writing handler for .mat files, an alternative to
    scipy's "savemat" function. Scipy's function and the .mat format is not well-
    suited for writing multiple channels of data continuously. As of the current
    version, this class introduces the functionality of saving data continuously
    at the cost of only one channel per file. Thus, every channel of data should
    be saved in its own file when using this class. The variable name in the file
    is fixed as "data". When loading multiple files in MATLAB, one should assign
    each array a new variable name to distinguish between them.
    """

    def __init__(self, filepath, dtype, header='MATLAB File'):
        super().__init__()
        self.file = open(filepath, 'wb')
        header = header.strip()
        if len(header) > 124:
            header = header[:124]
        else:
            l = len(header)
            header = header + ' '*(124-l)
        self.header = header
        self.mclass = self.MCLASS[dtype]
        self.mtype = self.MTYPE[dtype]
        self.bytes_per_num = self.BYTES[dtype]
        self.dtype = self.NPY_TYPE[dtype]
        self.tagcomplete = False

    def write_preamble(self):
        header = self.header.encode('ascii')
        version = pack('H', 256)
        endian = np.ndarray(shape=(), dtype='S2', buffer=np.uint16(0x4d49)).tobytes()
        tagMatrix = pack('II', 14, 0)
        tagClass = pack('II', 6, 8)
        valueClass = pack('II', self.mclass, 0)
        tagDimensions = pack('II', 5, 8)
        valueDimensions = pack('ii', 1, 0)
        matrixName = np.array((1, 0, 4, 0, 0x64, 0x61, 0x74, 0x61), dtype=np.uint8 ).tobytes()
        tagActualData = pack('II', self.mtype, 0)

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
        if not isinstance(arr, np.ndarray):
            arr = np.array(arr, dtype=self.dtype)
        elif not arr.dtype == self.dtype:
            arr = arr.astype(self.dtype)
        self.file.write( arr.tobytes() )

    def update_tags(self):
        current_pos = self.file.tell()
        pos = {'byte count tot': 132, 'dims': 164, 'byte count vector': 180}

        byte_count_vec = current_pos - pos['byte count vector'] - 4
        size = byte_count_vec // self.bytes_per_num
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
        if not self.tagcomplete:
            self.update_tags()
        self.file.close()

class NpyWriter(BaseMatNpyFile):
    def __init__(self, filepath, dtype):
        super().__init__()
        self.file = open(filepath, 'wb')

        self.descHead = "{'descr': '" + self.NPY_TYPE_LABEL[dtype] + "', 'fortran_order': False, 'shape': ("
        self.tagPos = len(self.descHead) + 10
        self.tagEnd = ",), }"
        self.tagcomplete = False
        self.bytes_per_num = self.BYTES[dtype]
        self.dtype = self.NPY_TYPE[dtype]

    def write_preamble(self):
        description_text = self.descHead + "20" + self.tagEnd
        l = len(description_text)
        description_text = description_text + ' '*(117-l) + '\n'

        header = np.array((0x93, 0x4E, 0x55, 0x4D, 0x50, 0x59, 0x01, 0x00, 0x76, 0x00), dtype=np.uint8 ).tobytes()
        description_bytes = description_text.encode('ascii')

        self.file.write(header)
        self.file.write(description_bytes)

    def write(self, arr):
        if not isinstance(arr, np.ndarray):
            arr = np.array(arr, dtype=self.dtype)
        elif not arr.dtype == self.dtype:
            arr = arr.astype(self.dtype)
        self.file.write( arr.tobytes() )

    def update_tags(self):
        current_pos = self.file.tell()
        data_start_pos = 128

        num_of_nums = (current_pos - data_start_pos) // self.bytes_per_num

        self.file.seek( self.tagPos )
        self.file.write( (str(num_of_nums)+self.tagEnd).encode('ascii') )

        self.file.seek( current_pos )

        self.tagcomplete = True

    def close(self):
        if not self.tagcomplete:
            self.update_tags()
        self.file.close()

class OpenMatNpyFileError(IOError):
    pass

@contextmanager
def open_mat(path, mode, dtype='double', header=''):
    """
    Context manager and factory function for MATLAB
    reader and writer objects.
    """
    if mode == 'r':
        file = MatReader(path, dtype)
    elif mode == 'w':
        file = MatWriter(path, dtype, header)
    else:
        raise OpenMatNpyFileError("File mode must be either read ('r') or write ('w')")
    try:
        yield file
    finally:
        file.close()

@contextmanager
def open_npy(path, mode, dtype='double'):
    """
    Context manager and factory function for Numpy
    reader and writer objects.
    """
    if mode == 'r':
        file = NpyReader(path, dtype)
    elif mode == 'w':
        file = NpyWriter(path, dtype)
    else:
        raise OpenMatNpyFileError("File mode must be either read ('r') or write ('w')")
    try:
        yield file
    finally:
        file.close()

class CSVWriter():
    def __init__(self, filepath):
        self.file = open(filepath, 'w', newline='')
        self.writer = csv.writer(self.file, delimiter='\n')
    def write(self, arr):
        self.writer.writerows(arr)
    def close(self):
        self.file.close()

@contextmanager
def open_csvwrite(path):
    file = CSVWriter(path)
    try:
        yield file
    finally:
        file.close()

############################## EXAMPLE ##############################
### using "get_doocs_data_continuous" and MatWriter or NpyWriter

### define the subroutine
def save_subroutine(data_dict, channels, writers, decimationFactor=1):
    """
    A subroutine that can be used with any of the writer classes
    defined above. Decimation is not yet implemented because the
    writer classes only take signed 16-bit integers as data (the
    data type from DAQ servers) but scipy's decimation will turn
    the data type into 64-bit floating point.
    """
    for i in range(len(data_dict)):
        if decimationFactor > 1:
            decimated_data = downsample(data_dict[i]['data'], decimationFactor)
        else:
            decimated_data = data_dict[i]['data']
        which = channels.index( data_dict[i]['daqname'] )
        writers[which].write( decimated_data )

### Main program
def save_custom(channels, filepaths, start, stop, ftype='.npy',
                daq="/daq_data/alps", server="ALPS.DAQ/DAQ.SERVER1/DAQ.DATA.SVR/"):

    ### appending extension if not already there
    filepaths = [fpath + ftype*(not fpath[-len(ftype):]==ftype) for fpath in filepaths]

    ### using ExitStack as the context manager because there are variable number of files to open
    with ExitStack() as stack:
        if ftype=='.mat':
            writers = [stack.enter_context(open_mat(fpath, 'w', 'double', header_text)) for fpath in filepaths]
        elif ftype=='.npy':
            writers = [stack.enter_context(open_npy(fpath, 'w', 'double')) for fpath in filepaths]

        result = get_doocs_data_continuous(channels, save_subroutine,
                                           start=start, stop=stop,
                                           daq=daq, server=server,
                                           sub_args=(channels, writers))

        ### IMPORTANT: always call the .update_tags() method at the end of writing files
        for i in range(len(writers)):
            writers[i].update_tags()

    return result

############################ END EXAMPLE ############################

def remove_overlap_timestamp(past_data, new_data):
    """
    Removes data points from `new_data` with the same timestamp as those in `past_data`.
    """

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
    """
    Saves time-stamped data to CSV live from a DOOCS channel not on a DAQ server.
    """

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
    """
    The following code uses the pydoocs.read() function to save data from
    DOOCS channels to CSV files. These DOOCS channels are ones not on a
    DAQ server. It is assumed that they have an associated channel with
    the same address but suffixed by ".HIST" and that the sampling rates
    are slow.

    Reading a ".HIST" address returns a dict with an item labeled "data",
    which is a list of tuples of the form (timestamp, data, macropulse).
    The length of the list is fixed and past data is no longer available
    after some time. Thus the following code only records data starting
    at the time of call. When saving from multiple channels, the tasks
    must be run in parallel to reduce the risk of data from one channel
    being removed while data from another channel is being logged. Thus,
    the tasks are handled by ThreadPoolExecutor from the python module
    "concurrent.futures".

    The difference in time between each timestamp can vary. Thus, both
    the timestamps and data are recorded. Each row of the file is a time-
    data pair, separated by a comma.
    """

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


def signal_process(data,fs=16000,t0=0,process="None",filtertype="None",filterfreq=0,flow=0,fhigh=0,zeros=[],poles=[],gain=0):
    """
    Uses the GWpy library of signal processing tools to filter and analyze data 
    by converting to a TimeSeries object, then subjecting it to GWpy function to 
    filter or generate FrequencySeries objects. Returns raw data for plotting.
    """

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

########## MISCELLANEOUS UTILITY FUNCTIONS AND CONSTANTS ##########

def downsample(arr, factor):
    """Custom decimation function, heeding Scipy's advice to run multiple times if factor is bigger than 13"""

    if factor > 13:
        arr = signal.decimate(arr, 4)
        factor = factor // 4
    if factor > 1:
        arr = signal.decimate(arr, factor)
    return arr

BASE_ADDRESS = "ALPS.DIAG/ALPS.ADC."

NR_ADDRESSES = [f"NR/CH_1.{i:02d}" for i in range(32)]
NL_ADDRESSES = [f"NL/CH_1.{i:02d}" for i in range(32)]
HN_ADDRESSES = [f"HN/CH_1.{i:02d}" for i in range(32)]

DECIMATION_VALUES = {
    "16 kHz": 16000,
    "8 kHz": 8000,
    "4 kHz": 4000,
    "2 kHz": 2000,
    "1 kHz": 1000,
    "500 Hz": 500 }
