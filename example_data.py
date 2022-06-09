#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 12:34:13 2022

@author: todd
"""
import sys
#import pydoocs
#import pydaq
import time
import numpy as np
from numpy import *

getdata_sample = [{'data': array([[15559, 15740, 15909, 16072, 16239, 16410, 16558, 16720, 16871,
        17022, 17168, 17314, 17458, 17600, 17727, 17867, 17993, 18128,
        18253, 18384, 18500, 18614, 18730, 18841, 18946, 19061, 19163,
        19259, 19349, 19448, 19534, 19627, 19710, 19792, 19867, 19937,
        20017, 20083, 20155, 20214, 20276, 20324, 20378, 20426, 20473,
        20516, 20556, 20587, 20626, 20659, 20681, 20709, 20731, 20738,
        20760, 20775, 20770, 20778, 20786, 20783, 20774, 20762, 20752,
        20728, 20710, 20694, 20671, 20643, 20608, 20571, 20523, 20490,
        20451, 20402, 20348, 20295, 20237, 20179, 20107, 20038, 19968,
        19903, 19821, 19740, 19658, 19575, 19484, 19395, 19294, 19195,
        19089, 18989, 18883, 18767, 18653, 18545, 18422, 18301, 18172,
        18048, 17913, 17785, 17652, 17508, 17367, 17222, 17074, 16925,
        16773, 16618, 16452, 16301, 16130, 15968, 15794, 15629, 15456,
        15282, 15106, 14921, 14740, 14552, 14374, 14173, 13989, 13790,
        13598, 13398, 13199, 12996, 12792, 12585, 12381, 12168, 11957,
        11740, 11524, 11306, 11090, 10868, 10641, 10420, 10187,  9966,
         9728,  9497,  9271,  9036,  8801,  8561,  8323,  8086,  7843,
         7600,  7356,  7117,  6863,  6614,  6370,  6117,  5877,  5626,
         5376,  5120,  4867,  4618,  4363,  4107,  3846,  3595,  3335,
         3074,  2818,  2552,  2298,  2040,  1783,  1520,  1261,   996,
          737,   475,   213, 65490, 65234, 64973, 64715, 64445, 64180,
        63926, 63670, 63408, 63158, 62894, 62631, 62381, 62122, 61867,
        61608, 61351, 61096, 60842, 60595, 60336, 60078, 59827, 59584,
        59337, 59094, 58842, 58600, 58362, 58111, 57866, 57627, 57385,
        57148, 56908, 56679, 56441, 56209, 55982, 55745, 55521, 55294,
        55065, 54841, 54620, 54394, 54181, 53969, 53756, 53544, 53324,
        53120, 52912, 52707, 52513, 52304, 52102, 51908, 51716, 51532,
        51336, 51148, 50967, 50782, 50602, 50423, 50249, 50076, 49901,
        49735, 49566, 49404, 49239, 49090, 48927, 48779, 48621, 48479,
        48331, 48187, 48053, 47918, 47785, 47657, 47533, 47393, 47273,
        47158, 47039, 46923, 46813, 46716, 46599, 46504, 46400, 46315,
        46219, 46127, 46038, 45956, 45877, 45793, 45732, 45655, 45582,
        45516, 45451, 45394, 45343, 45292, 45242, 45190, 45155, 45113,
        45087, 45042, 45012, 44997, 44961, 44945, 44934, 44914, 44902,
        44900, 44897, 44894, 44897, 44899, 44916, 44926, 44946, 44968,
        44987, 45010, 45035, 45069, 45105, 45147, 45183, 45228, 45276,
        45321, 45375, 45437, 45498, 45568, 45628, 45699, 45772, 45849,
        45933, 46013, 46094, 46182, 46275, 46373, 46473, 46575, 46674,
        46782, 46891, 47008, 47122, 47238, 47356, 47484, 47612, 47749,
        47872, 48009, 48146, 48286, 48434, 48576, 48726, 48879, 49035,
        49193, 49350, 49514, 49678, 49847, 50020, 50188, 50362, 50547,
        50727, 50899, 51086, 51274, 51464, 51651, 51841, 52035, 52235,
        52439, 52643, 52842, 53049, 53256, 53467, 53682, 53891, 54107,
        54330, 54541, 54768, 54986, 55214, 55440, 55668, 55899, 56125,
        56358, 56595, 56828, 57071, 57308, 57545, 57786, 58021, 58269,
        58510, 58762, 59006, 59250, 59502, 59744, 59997, 60242, 60501,
        60752, 61008, 61261, 61514, 61774, 62031, 62287, 62546, 62804,
        63069, 63326, 63580, 63836, 64094, 64363, 64625, 64881, 65143,
        65401,   123,   382,   640,   912,  1167,  1426,  1677,  1935,
         2198,  2453,  2714,  2975,  3232,  3486,  3746,  4005,  4256,
         4511,  4767,  5017,  5275,  5521,  5772,  6027,  6271,  6523,
         6766,  7012,  7263,  7506,  7747,  7993,  8227,  8460,  8702,
         8944,  9170,  9410,  9637,  9867, 10101, 10326, 10550, 10773,
        10994, 11219, 11436, 11651, 11863, 12079, 12292, 12503, 12699,
        12917, 13115, 13309, 13513, 13711, 13909, 14096, 14284, 14475,
        14658, 14846, 15028, 15198, 15382]]), 'type': 'IMAGE', 'timestamp': 1641208980.970772, 'macropulse': 1590942828, 'miscellaneous': {'width': 500, 'height': 1, 'aoi_width': 500, 'aoi_height': 1, 'x_start': 0, 'y_start': 0, 'hbin': 1, 'vbin': 1, 'bpp': 2, 'ebitpp': 16, 'source_format': 0, 'image_format': 0, 'frame': 414029268, 'event': 1590942828, 'scale_x': -1.0, 'scale_y': -1.0, 'image_rotation': 0.0, 'fspare2': 700.0, 'fspare3': 1.9200000762939453, 'fspare4': 0.0, 'ispare2': 1, 'ispare3': 500, 'ispare4': 1, 'length': 1000, 'image_flags': 3, 'status': 0, 'daqname': 'ALPS.DIAG/ALPS.ADC.HN/CH_1.01'}}]

getdata_sample2 = [{'data': array([0.01*np.sin(320 *2*np.pi* np.linspace(0, 1, 1600000))])}]
getdata_sample3 = [{'data': array([0.03*np.sin(122 *2*np.pi* np.linspace(0, 1, 1600000))])}]
getdata_sample4 = [{'data': array(0.1*np.random.rand(1,1600000))+getdata_sample2[0]['data'][0]}]