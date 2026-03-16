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

    #MCVS_Lib.Multi_Channel_Calibration(["D9", "D10"])

    #MCVS_Lib.Get_Volt_Vals(4, 0, 5, True)

    #MCVS_Lib.Board_Operation('Four_Channel_PCB')

    calData = MCVS_Lib.Get_Cal_Curve_Data('Sample')

    MCVS_Lib.Get_PWM_From_Cal_Data(calData, "D9", 2.5)