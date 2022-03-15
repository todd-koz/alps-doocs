#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 16:48:51 2022

@author: todd
"""
from scipy import signal

samplerate = 1.6e4

def decimate_data(data,decimation):
    out = signal.decimate(data,decimation)
    return out