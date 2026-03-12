"""
Project that implements a control interface for the Programmable Multi-Channel Voltage Source

Project assumes that Multi-Channel Voltage Source PCB is controlled via IBM4
Expected output is between 0V and 5V
....

R. Sheehan 12 - 3 - 2024
"""

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


MOD_NAME_STR = "uHeatCtrl"

def main():
    pass

if __name__ == '__main__':
    main()

    pwd = os.getcwd() # get current working directory

    print(pwd)