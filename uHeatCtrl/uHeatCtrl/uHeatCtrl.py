"""
Project that implements a control interface for the Programmable Multi-Channel Voltage Source

Project assumes that Multi-Channel Voltage Source PCB is controlled via IBM4
Expected output is between 0V and 5V
....

R. Sheehan 12 - 3 - 2024
"""

# import packages
import os
import MCVS_Lib

MOD_NAME_STR = "uHeatCtrl"

def main():
    pass

if __name__ == '__main__':
    main()

    pwd = os.getcwd() # get current working directory

    print(pwd)

    CALIBRATE_BOARD = False
    if CALIBRATE_BOARD:
        board_name = 'Through_Hole'
        pinOuts = ["V1", "V2", "V3", "V4"]
        MCVS_Lib.Multi_Channel_Calibration(board_name, pinOuts)

    OPERATE_BOARD = False
    if OPERATE_BOARD:
        board_name = 'Through_Hole'
        pinOuts = ["V1", "V2", "V3", "V4"]
        IBM4Read = False
        NIDAQRead = True
        Loud = False
        MCVS_Lib.Board_Operation(board_name, pinOuts, IBM4Read, NIDAQRead, Loud)

    LONG_MEAS = False
    if LONG_MEAS:
        board_name = 'Four_Channel_PCB'
        pinOuts = ["V1", "V2", "V3", "V4"]
        Time = 45 # total time for meas in minutes
        Nmeas = 101 # total no. measurements
        Loud = False
        MCVS_Lib.Long_Measurement(board_name, pinOuts, Time, Nmeas, Loud)

    OFFSET_CALIB = False
    if OFFSET_CALIB:
        board_name = 'Through_Hole'
        pinOuts = ["V1", "V2", "V3", "V4"]
        Nmeas = 1001 # total no. measurements
        zero_outputs = False
        Loud = True
        MCVS_Lib.Offset_Calibration(board_name, pinOuts, Nmeas, zero_outputs, Loud)

    OFFSET_CALIB_ANAL = False
    if OFFSET_CALIB_ANAL:
        board_name = 'Four_Channel_PCB'
        pinOuts = ["V1", "V2", "V3", "V4"]
        Nmeas = 1001 # total no. measurements
        zero_outputs = True
        Loud = True
        MCVS_Lib.Offset_Calibration_Analysis(board_name, pinOuts, Nmeas, Loud)