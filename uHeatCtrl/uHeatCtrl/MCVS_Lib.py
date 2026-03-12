"""
Library that implements the code needed to control the Multi-Channel Voltage Source

R. Sheehan 12 - 3 - 2026
"""

MOD_NAME_STR = "MCVS_Lib"

# import packages
import os
import sys
import glob
import re
import serial # this package is actually called pyserial, install using py -m pip install pyserial
import time
import numpy
import math
import Common
import Plotting
import Sweep_Interval
import IBM4_Lib # IBM4 interface based on Serial

def Four_Channel_Board_Calibration():
    """
    Calibration routine for the 4-channel board

    R. Sheehan 12 - 3 - 2026
    """

    # As part of the development process I made a 4-channel version of the board
    # The idea here being that I could use the 4 IBM4 AI channels to do real time measurements of the 
    # voltage being output by the board
    # [V1, V2, V3, V4] are connected to [PWM9, PWM10, PWM11, PWM12]
    # PWMX is filtered, voltage amplified and current amplified then VX is connected to DUT
    # The voltage amplified version of the output is connected to an AI via a buffer and voltage divider for reading
    # AI measures VX / 2
    # [V1 / 2, V2 / 2, V3 / 3, V4 / 4] are connected to [A5, A4, A3, A2]
    # R. Sheehan 12 - 3 - 2026

    FUNC_NAME = ".Four_Channel_Board_Calibration()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
         # instantiate an object that interfaces with the IBM4
        the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4

        if the_dev.CommsStatus():
            the_dev.ZeroIBM4()

        else:
            pass
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Four_Channel_Board_Operation():

    pass

def Eight_Channel_Board_Operation():

    pass