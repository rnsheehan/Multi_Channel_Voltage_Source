"""
Python library for interfacing to the NI-DAQ USB-600x

R. Sheehan 21 - 11 - 2025
"""

# The aim is to establish comms with NI-DAQ USB 6001
# It appears that the code will also work for other NI-DAQ variants if configured correctly
# Official Documentation: https://nidaqmx-python.readthedocs.io/en/stable/
# Examples with explanation: https://nidaqmx-python.readthedocs.io/en/stable/#python-examples
# Nice introduction: https://www.halvorsen.blog/documents/programming/python/resources/powerpoints/DAQ%20with%20Python.pdf
# Examples online: https://github.com/ni/nidaqmx-python/tree/master

# Originally I was going to write a class that would interface with the NI-DAQ, however, given that nidaqmx already defines a class for interfacing to the NI-DAQ any
# class I would write would basically be a worse version of the nidaqmx class, essentially just a wrapper that would be less flexible than nidaqmx.
# Instead of writing an inferior wrapper class I'm going to implement a library performs some common tasks that the NI-DAQ is used for
# R. Sheehan 3 - 12 - 2025

# import required libraries
from ast import Try
import os
from pickle import FALSE
from tkinter import EXCEPTION
import wave

import nitypes.waveform

os.environ["NIDAQMX_ENABLE_WAVEFORM_SUPPORT"] = "1"

import re
import glob
import math
import numpy
import scipy
import time
import nidaqmx
import nitypes
import random

import Sweep_Interval
import Plotting
import Common

MOD_NAME_STR = "NI_DAQ_Lib"
AI_SR_MAX = 20000 # max sample rate on single AI channel, units of Hz
AO_SR_MAX = 5000 # max sample rate on single AO channel, units of Hz

# Dictionary for Accessing the Different Waveform Types
Waveforms = {"Sine":0, "Square":1, "Triangle":2, "Ramp":3, "Sawtooth":4,  "Square Unipolar":5, "Triangle Unipolar":6, "PRBS":7, "Random":8}

# Actual routines that you would want with a DAQ

def Generate_Sine_Waveform(sample_rate, no_smpls, t_start = 0.0, frequency = 1.0, amplitude = 1.0, phase = 0.0):
    """
    Generate a sine waveform

    Inputs
    sample_rate(int) and no_smpls(int) to be determined by NI-DAQ AO
    t_start(float) time at which sine wave must start in units of second
    frequency(float) in units of Hz
    amplitude(float) in units of volt in range [-10, 10]
    phase(float) is dimensionless

    Output is a tuple with the following items
    timeInterval(SweepSpace object) that contains the data needed to generate time samples using numpy.linspace
    w_vals(float numpy array) contains sine waveform values

    R. Sheehan 4 - 12 - 2025
    """
    
    FUNC_NAME = ".Generate_Sine_Waveform()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if sample_rate > 0 else False
        c2 = True if no_smpls > 0 else False
        c3 = True if frequency > 0 else False
        c4 = True if math.fabs(amplitude) <= 10 else False
        c10 = c1 and c2 and c3 and c4

        if c10:
            deltaT = ( 1.0 / float(sample_rate) )
            t0 = t_start
            two_pi_nu = 2.0 * math.pi * frequency
            t_vals = numpy.array([]) # instantiate an empty numpy array
            w_vals = numpy.array([]) # instantiate an empty numpy array
            count = 0
            while count < no_smpls:
                sval = amplitude * math.sin(two_pi_nu * t0 + phase)
                w_vals = numpy.append(w_vals, sval )
                t0 += deltaT
                count += 1

            # instantiate a SweepSpace object to enable time samples to be generated later using 
            # numpy.linspace(timeInterval.start, timeInterval.stop, timeInterval.Nsteps, endpoint=True, retstep=True)
            timeInterval = Sweep_Interval.SweepSpace(no_smpls, t_start, t0)
            
            return (timeInterval, w_vals)
        else:
            if c1 is False: ERR_STATEMENT += '\nsample_rate is negative'
            if c2 is False: ERR_STATEMENT += '\nno_smpls is negative'
            if c3 is False: ERR_STATEMENT += '\nfrequency is negative'
            if c4 is False: ERR_STATEMENT += '\namplitude is out of range for NI-DAQ'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Generate_Square_Waveform(sample_rate, no_smpls, t_start = 0.0, frequency = 1.0, amplitude = 1.0, phase = 0.0, unipolar = False):
    """
    Generate a square waveform

    Inputs
    sample_rate(int) and no_smpls(int) to be determined by NI-DAQ AO
    t_start(float) time at which square wave must start in units of second
    frequency(float) in units of Hz
    amplitude(float) in units of volt in range [-10, 10]
    phase(float) is dimensionless
    unipolar(boolean) decides whether or not output is all positive, or a mix of positive and negative

    Output is a tuple with the following items
    timeInterval(SweepSpace object) that contains the data needed to generate time samples using numpy.linspace
    w_vals(float numpy array) contains square waveform values

    R. Sheehan 4 - 12 - 2025
    """

    # notes on square waves
    # https://en.wikipedia.org/wiki/Square_wave_(waveform)
    # https://mathworld.wolfram.com/SquareWave.html
    
    FUNC_NAME = ".Generate_Square_Waveform()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if sample_rate > 0 else False
        c2 = True if no_smpls > 0 else False
        c3 = True if frequency > 0 else False
        c4 = True if math.fabs(amplitude) <= 10 else False
        c10 = c1 and c2 and c3 and c4

        if c10:
            deltaT = ( 1.0 / float(sample_rate) )
            t0 = t_start
            two_pi_nu = 2.0 * math.pi * frequency
            t_vals = numpy.array([]) # instantiate an empty numpy array
            w_vals = numpy.array([]) # instantiate an empty numpy array
            count = 0
            while count < no_smpls:
                sval = math.sin(two_pi_nu * t0 + phase)
                # python does not have a built-in signum function, but it does have copysign which can be used
                # copysign(x,y): Return x with the sign of y
                val = math.copysign(amplitude, sval) # sq wave = signum (sine wave)
                if unipolar:
                    w_vals = numpy.append(w_vals, val if val > 0.0 else 0.0 ) # only want positive portion of sq wave
                else:
                    w_vals = numpy.append(w_vals, val)
                t0 += deltaT
                count += 1

            # instantiate a SweepSpace object to enable time samples to be generated later using 
            # numpy.linspace(timeInterval.start, timeInterval.stop, timeInterval.Nsteps, endpoint=True, retstep=True)
            timeInterval = Sweep_Interval.SweepSpace(no_smpls, t_start, t0)
            
            return (timeInterval, w_vals)
        else:
            if c1 is False: ERR_STATEMENT += '\nsample_rate is negative'
            if c2 is False: ERR_STATEMENT += '\nno_smpls is negative'
            if c3 is False: ERR_STATEMENT += '\nfrequency is negative'
            if c4 is False: ERR_STATEMENT += '\namplitude is out of range for NI-DAQ'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Generate_Triangle_Waveform(sample_rate, no_smpls, t_start = 0.0, frequency = 1.0, amplitude = 1.0, phase = 0.0, unipolar = False):
    """
    Generate a triangle waveform

    Inputs
    sample_rate(int) and no_smpls(int) to be determined by NI-DAQ AO
    t_start(float) time at which triangle wave must start in units of second
    frequency(float) in units of Hz
    amplitude(float) in units of volt in range [-10, 10]
    phase(float) is dimensionless
    unipolar(boolean) decides whether or not output is all positive, or a mix of positive and negative

    Output is a tuple with the following items
    timeInterval(SweepSpace object) that contains the data needed to generate time samples using numpy.linspace
    w_vals(float numpy array) contains triangle waveform values

    R. Sheehan 4 - 12 - 2025
    """

    # notes on triangular wave
    # https://en.wikipedia.org/wiki/Triangle_wave
    # https://mathworld.wolfram.com/TriangleWave.html
    
    FUNC_NAME = ".Generate_Pulse_Waveform()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if sample_rate > 0 else False
        c2 = True if no_smpls > 0 else False
        c3 = True if frequency > 0 else False
        c4 = True if math.fabs(amplitude) <= 10 else False
        c10 = c1 and c2 and c3 and c4

        if c10:
            deltaT = ( 1.0 / float(sample_rate) )
            t0 = t_start
            two_pi_nu = 2.0 * math.pi * frequency
            amp = (2.0 * amplitude) / math.pi
            t_vals = numpy.array([]) # instantiate an empty numpy array
            w_vals = numpy.array([]) # instantiate an empty numpy array
            count = 0
            while count < no_smpls:
                sval = math.sin(two_pi_nu * t0 + phase)
                val = amp * math.asin( sval )
                if unipolar:
                    w_vals = numpy.append(w_vals, math.fabs(val) ) # convert to strictly positive triangular pulses by taking math.fabs(val)
                else:
                    w_vals = numpy.append(w_vals, val )
                t0 += deltaT
                count += 1

            # instantiate a SweepSpace object to enable time samples to be generated later using 
            # numpy.linspace(timeInterval.start, timeInterval.stop, timeInterval.Nsteps, endpoint=True, retstep=True)
            timeInterval = Sweep_Interval.SweepSpace(no_smpls, t_start, t0)
            
            return (timeInterval, w_vals)
        else:
            if c1 is False: ERR_STATEMENT += '\nsample_rate is negative'
            if c2 is False: ERR_STATEMENT += '\nno_smpls is negative'
            if c3 is False: ERR_STATEMENT += '\nfrequency is negative'
            if c4 is False: ERR_STATEMENT += '\namplitude is out of range for NI-DAQ'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Generate_Ramp_Waveform(sample_rate, no_smpls, t_start = 0.0, frequency = 1.0, amplitude = 1.0, phase = 0.0):
    """
    Generate a ramp or sawtooth waveform

    Inputs
    sample_rate(int) and no_smpls(int) to be determined by NI-DAQ AO
    t_start(float) time at which triangle wave must start in units of second
    frequency(float) in units of Hz
    amplitude(float) in units of volt in range [-10, 10]
    phase(float) is dimensionless

    Output is a tuple with the following items
    timeInterval(SweepSpace object) that contains the data needed to generate time samples using numpy.linspace
    w_vals(float numpy array) contains triangle waveform values

    R. Sheehan 26 - 2 - 2026
    """

    # notes on ramp wave
    # https://en.wikipedia.org/wiki/Triangle_wave
    # https://mathworld.wolfram.com/SawtoothWave.html
    # https://docs.python.org/3/library/math.html#math.modf
    
    FUNC_NAME = ".Generate_Ramp_Waveform()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if sample_rate > 0 else False
        c2 = True if no_smpls > 0 else False
        c3 = True if frequency > 0 else False
        c4 = True if math.fabs(amplitude) <= 10 else False
        c10 = c1 and c2 and c3 and c4

        if c10:
            deltaT = ( 1.0 / float(sample_rate) )
            t0 = t_start
            two_pi_nu = 2.0 * math.pi * frequency
            t_vals = numpy.array([]) # instantiate an empty numpy array
            w_vals = numpy.array([]) # instantiate an empty numpy array
            count = 0
            while count < no_smpls:
                sval = two_pi_nu * t0 + phase
                val = amplitude * (sval - math.floor(sval))
                #val = amplitude * math.modf( sval )[0]
                w_vals = numpy.append(w_vals, val)
                t0 += deltaT
                count += 1

            # instantiate a SweepSpace object to enable time samples to be generated later using 
            # numpy.linspace(timeInterval.start, timeInterval.stop, timeInterval.Nsteps, endpoint=True, retstep=True)
            timeInterval = Sweep_Interval.SweepSpace(no_smpls, t_start, t0)
            
            return (timeInterval, w_vals)
        else:
            if c1 is False: ERR_STATEMENT += '\nsample_rate is negative'
            if c2 is False: ERR_STATEMENT += '\nno_smpls is negative'
            if c3 is False: ERR_STATEMENT += '\nfrequency is negative'
            if c4 is False: ERR_STATEMENT += '\namplitude is out of range for NI-DAQ'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Generate_Random_Pulse_Waveform(sample_rate, no_smpls, t_start = 0.0, amplitude = 1.0, t_pulse = 0.1, uniform = True):
    """
    Generate a random pulse waveform

    Inputs
    sample_rate(int) and no_smpls(int) to be determined by NI-DAQ AO
    t_start(float) time at which triangle wave must start in units of second
    
    amplitude(float) in units of volt in range [0, 10]
    t_pulse(float) in units of second
    uniform(boolean) specifies equal amplitude pulses when True, arbitrary amplitude value when False
    
    Output is a tuple with the following items
    timeInterval(SweepSpace object) that contains the data needed to generate time samples using numpy.linspace
    w_vals(float numpy array) contains random pulse waveform values

    R. Sheehan 23 - 2 - 2026
    """

    # Assume pulses are of finite width t_pulse (ms), where t_pulse_min > (1/SR)
    # Within each pulse period decide randomly if the next pulse period will be On / Off
    # Assign a pulse value to each time step
    # This will be periodic by default, is the answer to make the waveform duration very long?
    # For notes on random number generation in python see: https://docs.python.org/3/library/random.html
    # On seeding: https://stackoverflow.com/questions/817705/pythons-random-what-happens-if-i-dont-use-seedsomevalue
    # On seeding: https://stackoverflow.com/questions/33849960/is-it-necessary-to-call-seed-when-using-random-in-python
    
    FUNC_NAME = ".Generate_Random_Pulse_Waveform()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        deltaT = ( 1.0 / float(sample_rate) ) # time interval between AO samples in units of second
        
        c1 = True if sample_rate > 0 else False
        c2 = True if no_smpls > 0 else False
        c3 = True if t_pulse > deltaT else False
        c4 = True if math.fabs(amplitude) <= 10 else False
        c10 = c1 and c2 and c3 and c4
        
        if c10:
            t0 = t_start
            t_vals = numpy.array([]) # instantiate an empty numpy array
            w_vals = numpy.array([]) # instantiate an empty numpy array
            random.seed() # seed the rng with the current system time
            count = 0
            ndT = t_pulse * sample_rate # How many deltaT fit inside t_pulse? 
            while count < no_smpls:
                # decide if the pulse is On / Off
                # randomise every time t0 is integer multiple of t_pulse
                if count % ndT == 0:
                    if uniform:
                        val = amplitude if random.random() >= 0.5 else 0.0
                    else:
                        val = -10.0 + 20.0 * random.random() # generate random number in range [-10, +10] using formula a + (b - a) * random()
                w_vals = numpy.append(w_vals, val )
                t0 += deltaT
                count += 1

            # instantiate a SweepSpace object to enable time samples to be generated later using 
            # numpy.linspace(timeInterval.start, timeInterval.stop, timeInterval.Nsteps, endpoint=True, retstep=True)
            timeInterval = Sweep_Interval.SweepSpace(no_smpls, t_start, t0)
            
            return (timeInterval, w_vals)
        else:
            if c1 is False: ERR_STATEMENT += '\nsample_rate is negative'
            if c2 is False: ERR_STATEMENT += '\nno_smpls is negative'
            if c3 is False: ERR_STATEMENT += '\nt_pulse is too short'
            if c4 is False: ERR_STATEMENT += '\namplitude is out of range for NI-DAQ'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Extract_Sample_Rate(physical_channel_str, device_name, loud = False):
    """
    Extract the AI / AO sample rate based on the data contained in the physical_channel string descriptor
    Always want to set sample rate to be at its maximum
    
    Methods aims to process physical_channel string descriptors of the form
    'device_name/a<x><v1>', single channel operation
    'device_name/a<x><v1>:<v2>', multiple sequential channel operation
    'device_name/axv1, device_name/axv2, ..., device_name/axvn', multiple channel operation
    'device_name/a<x><v1>:<v2>, device_name/axv3, ..., device_name/axvn', multiple channel operation
    'device_name/a<x><v1>:<v2>, device_name/a<x><v3>:<v4>', multiple channel operation
    
    <x> = i or o
    <v1>, <v2> indicate the sequential channel numbers on the DAQ
    
    If a user inputs physical_channel_str with mix of ao and ai channels an exception will be thrown by nidaqmx
    
    R. Sheehan 27 - 11 - 2025
    """

    FUNC_NAME = ".Extract_Sample_Rate()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c10 = c1 and c2

        if c10:
            SR_MAX = AI_SR_MAX if 'i' in physical_channel_str else AO_SR_MAX
            
            reduced_str = physical_channel_str.replace( device_name+'/', '' ) # strip out the device_name from the physical_channel_str
            if loud: print("Physical Channels: ",reduced_str)

            if ',' in physical_channel_str and ':' not in physical_channel_str:
                # physical_channel_str is of the form 'device_name/axv1, device_name/axv2, ..., device_name/axvn'
                ch_nums = list ( set ( map ( int, re.findall(r"[-+]?\d+[\.]?\d*", reduced_str ) ) ) ) # set removes duplicates from the list if they exist
                no_ch = len(ch_nums)
                SR = int(SR_MAX / no_ch)
            elif ':' in physical_channel_str and ',' not in physical_channel_str:
                # physical_channel_str is of the form 'device_name/axv1:v2'
                # <x> = i or o
                # <v1>, <v2> indicate the sequential channel numbers on the DAQ
                ch_nums = list ( map ( int, re.findall(r"[-+]?\d+[\.]?\d*", reduced_str ) ) )
                no_ch = 1 + ( max(ch_nums) - min(ch_nums) ) # use this in case v1 != 0
                SR = int(SR_MAX / no_ch)
            elif ':' in physical_channel_str and ',' in physical_channel_str:
                # physical_channel_str is of the form 'device_name/a<x><v1>:<v2>, device_name/axv3, ..., device_name/axvn'
                # physical_channel_str is of the form 'device_name/a<x><v1>:<v2>, device_name/a<x><v3>:<v4>'
                # <x> = i or o
                # <v1>, ..., <vn> indicate the channel numbers on the DAQ, not necessarily sequential
                ch_nums = []
                for item in reduced_str.split(','):
                    if ":" in item:
                        nums = list ( map ( int, re.findall(r"[-+]?\d+[\.]?\d*", item) ) )
                        ch_nums.extend( range( nums[0], 1+nums[1], 1 ) )
                    else:
                        ch_nums.extend(list ( map ( int, re.findall(r"[-+]?\d+[\.]?\d*", item) ) ) )
                ch_nums = list( set( ch_nums ) ) # set removes duplicates from the list if they exist
                no_ch = len(ch_nums)
                SR = SR_MAX / no_ch
            else:
                # physical_channel_str is of the form 'device_name/a<x><v1>'
                # indicating a single channel is being used
                # <x> = i or o
                # <v1> indicates the channel number on the DAQ
                ch_nums = list ( map ( int, re.findall(r"[-+]?\d+[\.]?\d*", reduced_str ) ) )
                no_ch = 1
                SR = SR_MAX

            if loud: 
                print("Channels:", ch_nums)
                print("No. Channels:",no_ch)
                print("Sample Rate:", SR)
                print()

            return [SR, no_ch]
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

# Analog Output Methods

def AO_DC_Output(physical_channel_str = 'Dev2/ao0:1', device_name = 'Dev2', voltage = [0.0, 0.0]):

    """
    Configure the NI-DAQ to output DC signal continuously

    physical_channel_str(string) tells the DAQ which channels it wants to work from
    device_name(string) tells the PC what handle has been assigned to the DAQ by the PC
    voltage(float or list) tells the DAQ which voltages should be output on AO channels

    R. Sheehan 25 - 2 - 2026
    """

    FUNC_NAME = ".AO_DC_Output()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c3 = True if 'o' in physical_channel_str else False
        c10 = c1 and c2 and c3

        if c10:
            # Extract the sample rate per channel
            ao_chn_str = physical_channel_str

            ao_SR, ao_no_ch = Extract_Sample_Rate(ao_chn_str, device_name)
            number_of_samples = ao_SR

            # Check that the no. voltages required equals the no. AO channels selected 
            # https://docs.python.org/3/library/functions.html#isinstance
            if isinstance(voltage, list):
                # voltage input as a list and no. elements in list equals no. channels
                # voltage could be a 1- or 2-element list
                c11 = len(voltage) == ao_no_ch
            else:
                # voltage input as a float and no. channels equals one
                c11 = Common.isfloat(voltage) and ao_no_ch == 1 

            if c11:
                # Configure the analog output to write continuously
                ao_task = nidaqmx.Task()

                ao_task.ao_channels.add_ao_voltage_chan(ao_chn_str, min_val = -10, max_val = +10)

                # technically this is not necessary for DC output since you are not outputting a waveform
                # ao_task.timing.cfg_samp_clk_timing(rate = ao_SR, sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS, 
                #                                    samps_per_chan = number_of_samples, active_edge = nidaqmx.constants.Edge.RISING)
                # actual_sampling_rate = ao_task.timing.samp_clk_rate # read the actual sample rate

                ao_task.start()

                ao_task.write(voltage) # NI-DAQ will persist with last set DC value
            
                ao_task.stop()

                ao_task.close()
            else:
                ERR_STATEMENT += "\nNo. AO channels != No. Voltages"
                raise Exception
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            if c3 is False: ERR_STATEMENT += '\nAnalog Output not possible using ' + physical_channel_str
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def AO_AC_Output(physical_channel_str = 'Dev2/ao1', device_name = 'Dev2', waveform_choice = 'Sine', frequency = 10.0, amplitude = 1.0, offset = 0.0, phase = 0.0):

    """
    Configure the NI-DAQ to output AC signal continuously

    physical_channel_str(string) tells the DAQ which channels it wants to work from
    device_name(string) tells the PC what handle has been assigned to the DAQ by the PC
    waveform_choice(string) string describing the choice of waveform output
    frequency(float) operating frequency of the AC output in units of Hz
    amplitude(float) operating amplitude of the AC output in units of V
    offset(float) DC offset of the AC output in units of V
    phase(float) phase offset for the AC output, dimensionless

    R. Sheehan 26 - 2 - 2026
    """

    FUNC_NAME = ".AO_AC_Output()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c3 = True if 'o' in physical_channel_str else False
        # Theoretically possible to output at f <= SR / 2, practically speaking require f < SR / 8 for smooth output
        c4 = True if frequency < AO_SR_MAX>>3 else False
        c5 = True if math.fabs(amplitude) + math.fabs(offset) < 10.0 else False
        c6 = True if 0.0 < math.fabs(amplitude) < 10.0 else False
        c7 = True if 0.0 <= math.fabs(offset) < 10.0 else False
        c8 = True if waveform_choice in Waveforms else False
        c10 = c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8

        if c10:
            # Extract the sample rate per channel
            ao_chn_str = physical_channel_str

            ao_SR, ao_no_ch = Extract_Sample_Rate(ao_chn_str, device_name)
            number_of_samples = ao_SR

            if ao_no_ch == 1:
                # Configure the analog output to write continuously
                ao_task = nidaqmx.Task()

                ao_task.ao_channels.add_ao_voltage_chan(ao_chn_str, min_val = -10, max_val = +10)

                ao_task.timing.cfg_samp_clk_timing(rate = ao_SR, sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS, 
                                                   samps_per_chan = number_of_samples, active_edge = nidaqmx.constants.Edge.RISING)
                actual_sampling_rate = ao_task.timing.samp_clk_rate # read the actual sample rate

                # Generate the waveform data
                t0 = 0.0
                if waveform_choice == 'Sine':
                    _, data = Generate_Sine_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase)
                elif waveform_choice == 'Square':
                    _, data = Generate_Square_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase)
                elif waveform_choice == 'Triangle':
                    _, data = Generate_Triangle_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase)
                elif waveform_choice == 'Square Unipolar':
                    _, data = Generate_Square_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase, unipolar = True)
                elif waveform_choice == 'Triangle Unipolar':
                    _, data = Generate_Triangle_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase, unipolar = True)
                elif waveform_choice == 'Ramp' or waveform_choice == 'Sawtooth':
                    _, data = Generate_Ramp_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase)
                else:
                    _, data = Generate_Sine_Waveform(ao_SR, number_of_samples, t0, frequency, amplitude, phase)

                if offset != 0.0:
                    data = data + offset

                ao_task.write(data)

                ao_task.start()
                
                input("NI-DAQ 6001 outputting continuously. Press Enter to stop.\n")

                ao_task.stop()

                ao_task.close()
            else:
                ERR_STATEMENT += "\nNo. AO channels != 1"
                raise Exception
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            if c3 is False: ERR_STATEMENT += '\nAnalog Output not possible using ' + physical_channel_str
            if c4 is False: ERR_STATEMENT += '\nAnalog Output not possible for f > %(v1)d ( Hz )'%{"v1":AO_SR_MAX>>3}
            if c5 is False: ERR_STATEMENT += '\nAnalog Output not possible for |amp| + |off| > 10 ( V )'
            if c6 is False: ERR_STATEMENT += '\nAnalog Output not possible for |amp| > 10 ( V )'
            if c7 is False: ERR_STATEMENT += '\nAnalog Output not possible for |off| > 10 ( V )'
            if c8 is False: ERR_STATEMENT += '\nAnalog Output not possible for waveform ' + waveform_choice
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def AO_Random_Output(physical_channel_str = 'Dev2/ao0', device_name = 'Dev2', waveform_choice = 'PRBS', pulse_width = 0.01, amplitude = 1.0):

    """
    Configure the NI-DAQ to output a sequence of random pulses

    physical_channel_str(string) tells the DAQ which channels it wants to work from
    device_name(string) tells the PC what handle has been assigned to the DAQ by the PC
    waveform_choice(string) string describing the choice of waveform output
    pulse_width(float) minimal pulse width in units of seconds
    amplitude(float) operating amplitude of the AO output in units of V

    R. Sheehan 26 - 2 - 2026
    """

    FUNC_NAME = ".AO_Random_Output()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c3 = True if 'o' in physical_channel_str else False
        c6 = True if 0.0 < math.fabs(amplitude) < 10.0 else False
        c8 = True if waveform_choice in Waveforms else False
        c10 = c1 and c2 and c3 and c6 and c8

        if c10:
            # Extract the sample rate per channel
            ao_chn_str = physical_channel_str

            ao_SR, ao_no_ch = Extract_Sample_Rate(ao_chn_str, device_name)
            number_of_samples = ao_SR
            dT = 1.0 / float(ao_SR)

            c11 = ao_no_ch == 1
            c12 = True if pulse_width > dT else False

            if c11 and c12:
                # Configure the analog output to write continuously
                ao_task = nidaqmx.Task()

                ao_task.ao_channels.add_ao_voltage_chan(ao_chn_str, min_val = -10, max_val = +10)

                ao_task.timing.cfg_samp_clk_timing(rate = ao_SR, sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS, 
                                                    samps_per_chan = number_of_samples, active_edge = nidaqmx.constants.Edge.RISING)
                actual_sampling_rate = ao_task.timing.samp_clk_rate # read the actual sample rate
                try:
                    print("Pulse width = %(v1)0.2f ( ms ), Pulse width minimum = %(v2)0.2f ( ms )"%{"v1":1000.0*pulse_width, "v2":1000.0*dT})
                    print("NI-DAQ 6001 outputting continuously. Press Ctrl + C to stop.\n")
                    count = 0
                    tf = 0.0
                    while True:
                        # Generate the waveform data
                        t0 = 0.0 if count == 0 else tf
                        tf = t0 + number_of_samples * dT
                        if waveform_choice == 'PRBS':
                            _, data = Generate_Random_Pulse_Waveform(ao_SR, number_of_samples, t0, amplitude, pulse_width, uniform = True)
                        elif waveform_choice == 'Random':
                            _, data = Generate_Random_Pulse_Waveform(ao_SR, number_of_samples, t0, amplitude, pulse_width, uniform = False)
                        else:
                            _, data = Generate_Random_Pulse_Waveform(ao_SR, number_of_samples, t0, amplitude, pulse_width, uniform = False)

                        ao_task.write(data)

                        ao_task.start()

                        ao_task.stop()
                
                    # If you were running the while loop for a finite number of calls you would release resources associated with NI-DAQ here
                    #ao_task.close()

                except KeyboardInterrupt:
                    # Ordinarily, you can ignore any errors associated with KeyboardInterrupt, use pass to ignore them
                    # pass
                    # Release the resources associated with NI-DAQ after KeyboardInterrupt
                    ao_task.stop()
                    ao_task.close()
            else:
                if c11 is False: ERR_STATEMENT += "\nNo. AO channels != 1"
                if c12 is False: ERR_STATEMENT += '\nt_pulse is too short'
                raise Exception
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            if c3 is False: ERR_STATEMENT += '\nAnalog Output not possible using ' + physical_channel_str
            if c6 is False: ERR_STATEMENT += '\nAnalog Output not possible for |amp| > 10 ( V )'
            if c8 is False: ERR_STATEMENT += '\nAnalog Output not possible for waveform ' + waveform_choice
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

# Analog Input Methods

def AI_DC_Read(physical_channel_str = 'Dev2/ai0:3', device_name = 'Dev2', loud = False):
    """
    Use NI-DAQ to perform single DC measurement

    differential read is assumed on all channels

    Output
    avg_arr (type: numpy array) contains average measured value across all channels

    R. Sheehan 18 - 3 - 2026
    """

    FUNC_NAME = ".AI_DC_Read()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c10 = c1 and c2

        if c10:
            # Configure the NI-DAQ for AI read

            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = Extract_Sample_Rate(ai_chn_str, device_name)

            # Configure Analog Input
            ai_task = nidaqmx.Task()        

            # If ai_chn_str is not correctly defined an exception will be thrown by nidaqmx
            ai_task.ai_channels.add_ai_voltage_chan(ai_chn_str, terminal_config = nidaqmx.constants.TerminalConfiguration.DIFF, min_val = -10.0, max_val = +10.0)
            
            # Configure the sampling timing
            # Note that when reading data later no. samples to be read must equal samps_per_chan as defined
            # Otherwise an exception will be thrown by nidaqmx
            ai_task.timing.cfg_samp_clk_timing(ai_SR, sample_mode = nidaqmx.constants.AcquisitionType.FINITE, 
                                                samps_per_chan = ai_SR, active_edge = nidaqmx.constants.Edge.RISING)

            # create arrays for storing measured data
            avg_arr = numpy.zeros(ai_no_ch)
            stdev_arr = numpy.zeros(ai_no_ch)
            
            # read the available data
            data = ai_task.read(nidaqmx.constants.READ_ALL_AVAILABLE)
            for i in range(0, ai_no_ch, 1):
                avg = numpy.mean(data[i])
                stdev = numpy.std(data[i], ddof = 1)
                avg_arr[i] = avg
                stdev_arr[i] = stdev
                out_str = "ai%(v1)d: %(v2)0.3f +/- %(v3)0.3f ( V )"%{"v1":i, "v2":avg, "v3":stdev}
                if loud: print(out_str)
            if loud:print()

            # AI Channel Monitoring Measurement END
            # Close off the ai_task
            ai_task.close()

            return avg_arr
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def AI_Monitor(physical_channel_str = 'Dev2/ai0:3', device_name = 'Dev2', loud = False):
    """
    Use NI-DAQ to measure multiple real-time AI

    differential read is assumed on all channels

    R. Sheehan 3 - 12 - 2025
    """

    FUNC_NAME = ".AI_Monitor()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c10 = c1 and c2

        if c10:
            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = Extract_Sample_Rate(ai_chn_str, device_name)

            # Configure Analog Input
            ai_task = nidaqmx.Task()        

            # If ai_chn_str is not correctly defined an exception will be thrown by nidaqmx
            ai_task.ai_channels.add_ai_voltage_chan(ai_chn_str, terminal_config = nidaqmx.constants.TerminalConfiguration.DIFF, 
                                                    min_val = -10, max_val = +10)
            
            # Configure the sampling timing
            # Note that when reading data later no. samples to be read must equal samps_per_chan as defined
            # Otherwise an exception will be thrown by nidaqmx
            ai_task.timing.cfg_samp_clk_timing(ai_SR, sample_mode = nidaqmx.constants.AcquisitionType.FINITE, 
                                               samps_per_chan = ai_SR, active_edge = nidaqmx.constants.Edge.RISING)

            # AI Channel Monitoring
            DELAY = 10
            N_meas = 7
            count = 0
            while count < N_meas:

                count += 1

            # Close off the ai_task
            ai_task.close()
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def AI_Timed_DC_Measurement(physical_channel_str = 'Dev2/ai0:3', device_name = 'Dev2', total_time = 10, no_meas = 10, loud = False):
    """
    Use NI-DAQ to measure multiple AI for specified time period, with delay between measurements

    differential read is assumed on all channels

    total_time (type: float) duration for which NI-DAQ was sampling, units of minutes
    no_meas (type: int) number of measurement taken during period total_time

    R. Sheehan 27 - 1 - 2026
    """

    FUNC_NAME = ".AI_Timed_DC_Measurement()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if physical_channel_str != '' else False
        c2 = True if device_name != '' else False
        c3 = True if total_time > 0 else False
        c3 = True if no_meas > 3 else False
        c10 = c1 and c2

        if c10:
            # Configure the NI-DAQ for AI read

            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = Extract_Sample_Rate(ai_chn_str, device_name)

            # Configure Analog Input
            ai_task = nidaqmx.Task()        

            # If ai_chn_str is not correctly defined an exception will be thrown by nidaqmx
            ai_task.ai_channels.add_ai_voltage_chan(ai_chn_str, terminal_config = nidaqmx.constants.TerminalConfiguration.DIFF, 
                                                    min_val = -10, max_val = +10)
            
            # Configure the sampling timing
            # Note that when reading data later no. samples to be read must equal samps_per_chan as defined
            # Otherwise an exception will be thrown by nidaqmx
            ai_task.timing.cfg_samp_clk_timing(ai_SR, sample_mode = nidaqmx.constants.AcquisitionType.FINITE, 
                                               samps_per_chan = ai_SR, active_edge = nidaqmx.constants.Edge.RISING)

            # AI Channel Monitoring Measurement

            # Compute DELAY time between measurements
            DELAY = (60 * total_time) / no_meas # compute delay time in seconds
            
            print("No. Measurement Channels =", ai_no_ch)
            print("AI Sample Rate =", ai_SR/1000,"( kHz )")                
            print("Delay Time =", DELAY,"( s )")

            # create arrays for storing measured data
            if ai_no_ch > 1:
                avg_arr = numpy.zeros((no_meas, ai_no_ch))
                stdev_arr = numpy.zeros((no_meas, ai_no_ch))
                counts_arr = numpy.full((no_meas, ai_no_ch), ai_SR)
            else:
                avg_arr = numpy.zeros(no_meas)
                stdev_arr = numpy.zeros(no_meas)
                counts_arr = numpy.repeat(ai_SR, no_meas)

            # AI Channel Monitoring Measurement START

            # Loop over all measurements with time DELAY between measurements
            count = 0
            while count < no_meas:
                time.sleep(DELAY)
                # read data into memory
                # ai_task.read returns a numpy array of size (ai_SR rows * ai_no_ch cols)
                # documentation for read https://nidaqmx-python.readthedocs.io/en/stable/task.html#nidaqmx.task.InStream.read
                data = ai_task.read(nidaqmx.constants.READ_ALL_AVAILABLE)

                # avg_file = open(filename_avg, 'a')
                # avg_file.write("Measurement %(v1)d\n"%{"v1":count})

                print("Measurement ",count)

                if ai_no_ch > 1:
                    # Multi-channel measurement parsing
                    for i in range(0, ai_no_ch, 1):
                        avg = numpy.mean(data[i])
                        stdev = numpy.std(data[i], ddof = 1)
                        avg_arr[count][i] = avg
                        stdev_arr[count][i] = stdev
                        out_str = "ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f ( V )"%{"v1":i, "v2":avg, "v3":stdev}
                        if loud: print(out_str)                        
                    if loud: print()

                else:
                    # Single-channel measurement parsing
                    avg = numpy.mean(data)
                    stdev = numpy.std(data, ddof = 1)
                    avg_arr[count] = avg
                    stdev_arr[count] = stdev
                    out_str = "ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f ( V )"%{"v1":0, "v2":avg, "v3":stdev}
                    if loud: print(out_str)                     

                # You could write the measured data to a file
                # Open the file in append mode, then call numpy.savetxt
                # numpy.savetxt truncates by default
                # with open(filename, 'a') as the_file:
                #     numpy.savetxt(the_file, data, "%0.9f", delimiter = ',')

                # forcefully remove data from memory, remember that ai_task.read returns a numpy array of size (ai_SR rows * ai_no_ch cols)
                del data; 

                count += 1

            # AI Channel Monitoring Measurement END
            # Close off the ai_task
            ai_task.close()

            filename_avg = "AI_DC_Meas_Avg_%(v1)s_Tmeas_%(v2)d_Nmeas_%(v3)d.txt"%{"v1":ai_chn_str.replace('/','_').replace(':',''), "v2":total_time, "v3":no_meas}

            filename_stdev = "AI_DC_Meas_Stdev_%(v1)s_Tmeas_%(v2)d_Nmeas_%(v3)d.txt"%{"v1":ai_chn_str.replace('/','_').replace(':',''), "v2":total_time, "v3":no_meas}

            filename_stat = "AI_DC_Meas_%(v1)s_Tmeas_%(v2)d_Nmeas_%(v3)d_Statistics.txt"%{"v1":ai_chn_str.replace('/','_').replace(':',''), "v2":total_time, "v3":no_meas}

            SAVE_DATA = True
            if SAVE_DATA:
                # Write the measured averages and measured stdev to their respective files
                # create files for storing data locally
                # Recall numpy.savetxt truncates by default
                
                Save_Timed_DC_Measurement_Data(physical_channel_str, device_name, total_time, no_meas, filename_avg, filename_stdev, filename_stat, avg_arr, stdev_arr, counts_arr)

            ANALYSE_DATA = True
            if ANALYSE_DATA:
                # Process the data, make plots and reports etc
                # Plot the time series of the measured data
                # Plot the histogram of the measured data

                Analyse_Timed_DC_Measurement(physical_channel_str, device_name, total_time, no_meas, filename_avg, avg_arr, loud)
            
            # forcefully remove the arrays from memory
            del avg_arr; del stdev_arr; del counts_arr; 

            MOVE_FILES = False
            if MOVE_FILES:
                # This can be optional
                # Move the files to a more convenient location
                # The location must exist on your computer, otherwise the files won't be moved
                #DATA_HOME = 'c:/users/robertsheehan/Research/Electronics/uHeater_Control/'
                DATA_HOME = 'D:/Rob/Research/Electronics/uHeater_Control/'

                txt_files = glob.glob("AI_DC_Meas*.txt")

                Common.Move_Files(DATA_HOME, txt_files)

                png_files = glob.glob("AI_DC_Meas*.png")
                Common.Move_Files(DATA_HOME, png_files)
        else:
            if c1 is False: ERR_STATEMENT += '\nNo data contained in physical_channel_str'
            if c2 is False: ERR_STATEMENT += '\nNo data contained in device_name'
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Save_Timed_DC_Measurement_Data(physical_channel_str = 'Dev2/ai0:3', device_name = 'Dev2', total_time = -1, no_meas = 2, filename_avg = '', filename_stdev = '', filename_stat = '', avg_arr = numpy.array([]), stdev_arr = numpy.array([]), counts_arr = numpy.array([])):

    """
    Save the average measured data, and the std. dev. of each measurement, to files

    Write the measured averages and measured stdev to their respective files
    create files for storing data locally
    Recall numpy.savetxt truncates by default

    total_time (type: float) duration for which NI-DAQ was sampling, units of minutes
    no_meas (type: int) number of measurement taken during period total_time 
    filename_avg (type: str) is the location where you want the averaged data to be saved
    filename_stdev (type: str) is the location where you want the std. dev. data to be saved
    avg_arr (type: numpy array float) contains average measured values from each read channel
    stdev_arr (type: numpy array float) contains std. dev. of measured values from each read channel
    counts_arr (type: numpy array int) contains no. of samples measured by NI-DAQ to obtain average measured value from each read channel

    avg_arr, stdev_arr, counts_arr are arrays with no_meas rows and between 1 and 4 columns

    R. Sheehan 28 - 1 - 2026
    """

    FUNC_NAME = ".Save_Timed_DC_Measurement_Data()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if total_time > 0 else False
        c2 = True if no_meas > 3 else False
        c3 = True if len(avg_arr) > 0 else False
        c4 = True if filename_avg != '' else False
        c5 = True if filename_stdev != '' else False
        c6 = True if filename_stat != '' else False
        c7 = True if len(stdev_arr) > 0 else False
        c8 = True if len(counts_arr) > 0 else False
        c10 = c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8

        if c10:
            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = Extract_Sample_Rate(ai_chn_str, device_name)

            # Recall numpy.savetxt truncates by default
            # You could change this by opening the file in append mode first, then subsequently writing to the file
            # In general you'd want one file for one measurement
            #the_file = open(filename_avg,'w') # open the file for writing, truncating it first
            #the_file.close()
            print("Writing to", filename_avg)
            numpy.savetxt(filename_avg, avg_arr, fmt = "%0.9f", delimiter = ',')

            # Recall numpy.savetxt truncates by default            
            # You could change this by opening the file in append mode first, then subsequently writing to the file
            # In general you'd want one file for one measurement
            #the_file = open(filename_stdev,'w') # open the file for writing, truncating it first
            #the_file.close()
            print("Writing to", filename_stdev)
            numpy.savetxt(filename_stdev, stdev_arr, fmt = "%0.9f", delimiter = ',')

            # Combine the averages and std. devs. into a single value for the entire measurement
            avg_file = open(filename_stat, 'a')
            avg_file.write("Combined Values\n")
            print("Combined Values")
            if ai_no_ch > 1:
                for i in range(0, ai_no_ch, 1):
                    avg, stdev = Common.Combine_Statistics(avg_arr[:,i], stdev_arr[:,i], counts_arr[:,i])
                    out_str = "ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f (V)\n"%{"v1":i, "v2":avg, "v3":stdev}
                    avg_file.write(out_str)
                    print(out_str)
            else:
                avg, stdev = Common.Combine_Statistics(avg_arr, stdev_arr, counts_arr)
                out_str = "ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f (V)\n"%{"v1":0, "v2":avg, "v3":stdev}
                avg_file.write(out_str)
                print(out_str)
            avg_file.close()
        else:
            if c1 != True: ERR_STATEMENT += "\ntotal_time value is not correct"
            if c2 != True: ERR_STATEMENT += "\nno_meas value is not correct"
            if c3 != True: ERR_STATEMENT += "\navg_arr is empty"
            if c4 != True: ERR_STATEMENT += "\nfilename_avg is not defined"
            if c5 != True: ERR_STATEMENT += "\nfilename_stdev is not defined"
            if c6 != True: ERR_STATEMENT += "\nfilename_stat is not defined"
            if c7 != True: ERR_STATEMENT += "\nstdev_arr is empty"
            if c8 != True: ERR_STATEMENT += "\ncounts_arr is empty"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Analyse_Timed_DC_Measurement(physical_channel_str = 'Dev2/ai0:3', device_name = 'Dev2', total_time = -1, no_meas = 2, filename_avg = '', avg_arr = numpy.array([]), loud = False):
    """
    Analyse the data produced by a timed DC measurement
    Process the data, make plots and reports etc
    Plot the time series of the measured data
    Plot the histogram of the measured data

    Inputs
    total_time (type: float) duration for which NI-DAQ was sampling, units of minutes
    no_meas (type: int) number of measurement taken during period total_time 
    filename_avg (type: str) is the location where you want the averaged data to be saved
    avg_arr (type: numpy array float) contains average measured values from each read channel
    avg_arr is an array with no_meas rows and between 1 and 4 columns

    R. Sheehan 9 - 2 - 2026
    """
    
    FUNC_NAME = ".Analyse_Timed_DC_Measurement()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if total_time > 0 else False
        c2 = True if no_meas > 3 else False
        c3 = True if len(avg_arr) > 0 else False
        c4 = True if filename_avg != '' else False
        c10 = c1 and c2 and c3 and c4

        if c10:
            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = Extract_Sample_Rate(ai_chn_str, device_name)

            # Compute DELAY time between measurements
            DELAY = total_time / no_meas # compute delay time in minutes

            times = numpy.arange(0, total_time, DELAY) # meas. times in units of minutes

            if ai_no_ch > 1:
                hv_data = []
                sub_avg = numpy.array([])
                sub_stdev = numpy.array([])
                for i in range(0, ai_no_ch, 1):
                    hv_data.append([times, avg_arr[:,i]])

                    # Compute the averages of the data
                    savg = numpy.mean(avg_arr[:,i])
                    sstdev = numpy.std(avg_arr[:,i], ddof = 1)

                    # Store them for scaling later
                    sub_avg = numpy.append(sub_avg, savg)
                    sub_stdev = numpy.append(sub_stdev, sstdev)

                    # examine whether or not the data is correlated with time
                    # To convert slope from ( V / min ) to ( mV / hr ) multiply slope by 60 * 1.0e+3 = 6.0e+4
                    model = scipy.stats.linregress(times, avg_arr[:,i])

                    print("ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f (V), m = %(v4)0.2f ( mV / hour ), c = %(v5)0.4f ( V ), R^{2} = %(v6)0.2f"%{"v1":i, "v2":savg,"v3":sstdev,"v4":6.0e+4*model.slope,"v5":model.intercept,"v6":model.rvalue**2})
                    # # In all cases there is a time-dependence on the order of less than 1 mV / hours
                    # alpha = 0.05
                    # if model.pvalue < alpha:
                    #     print("Reject H_{0}: model slope is significantly different from m = 0\nThere is a time dependence in the model")
                    # else:
                    #     print("Accept H_{0}: model slope is not significantly different from m = 0\nThere is no time dependence in the model")

                PLOT_TIME_SER = True
                if PLOT_TIME_SER:
                    # Make a time-series plot of the averaged data
                    args = Plotting.plot_arg_multiple()

                    args.loud = loud
                    args.crv_lab_list = ["ai%(v1)d"%{"v1":c} for c in range(0, ai_no_ch, 1)]
                    args.mrk_list = [Plotting.labs_lins[i] for i in range(0, ai_no_ch, 1)]
                    args.x_label = 'Time ( mins )'
                    args.y_label = 'Voltage ( V )'
                    #args.plt_range = [0, total_time, Vmin, Vmax]
                    #args.plt_title = r'Input Cap = %(v1)0.1f ( $\mu$F )'%{"v1":cap_vals[count]} 
                    args.fig_name = filename_avg.replace('.txt','') + '_time'

                    Plotting.plot_multiple_curves(hv_data, args)


                PLOT_TIME_SER_HIST = True
                if PLOT_TIME_SER_HIST:
                    # Make a plot of the scaled histogram of the measured data

                    # Use Sturges' Rule to compute the no. of bins required
                    n_bins = int( 1.0 + 3.322*math.log( len(avg_arr[:,0]) ) )

                    # scale the data to zero mean and unity std. dev. 
                    hist_data = []
                    for i in range(0, ai_no_ch, 1):
                        hist_data.append( (avg_arr[:,i] - sub_avg[i]) / sub_stdev[i] )

                    args = Plotting.plot_arg_multiple()

                    args.loud = loud
                    args.bins = n_bins
                    #args.plt_range = [-3, 3, 0, 25]
                    args.crv_lab_list = ["ai%(v1)d"%{"v1":c} for c in range(0, ai_no_ch, 1)]
                    args.fig_name = filename_avg.replace('.txt','') + '_hist'

                    Plotting.plot_multi_histogram(hist_data, args)

                    del hist_data

                del hv_data
            else:
                ERR_STATEMENT += "\nNot possible to analyse data when ai_no_ch < 1"
                raise Exception
        else:
            if c1 != True: ERR_STATEMENT += "\ntotal_time value is not correct"
            if c2 != True: ERR_STATEMENT += "\nno_meas value is not correct"
            if c3 != True: ERR_STATEMENT += "\naverage_values is empty"
            if c4 != True: ERR_STATEMENT += "\nfilename_avg is not defined"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)