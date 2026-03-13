"""
Library that implements the code needed to control the Multi-Channel Voltage Source

R. Sheehan 12 - 3 - 2026
"""

MOD_NAME_STR = "MCVS_Lib"

# import packages
import os
import glob
import time
import numpy
import scipy
import Common
import Plotting
import Sweep_Interval
import IBM4_Lib # IBM4 interface based on Serial
import nidaqmx
import NI_DAQ_Lib

def Multi_Channel_Calibration(pwmPins = ["D9", "D10", "D11", "D12"]):
    """
    Calibration routine for multiple-channels of the Micro-Controller Voltage Source
    Calibration is performed using NI-DAQ, which limits the number of channels that can be calibrated at any one time to 4
    Calibration is performed sequentially on each channel, while other channels are at ground


    R. Sheehan 12 - 3 - 2026
    """

    # As part of the development process I made a 4-channel version of the board
    # The idea here being that I could use the 4 IBM4 AI channels to do real time measurements of the 
    # voltage being output by the board [V1, V2, V3, V4] are connected to [PWM9, PWM10, PWM11, PWM12]
    # PWMX is filtered, voltage amplified and current amplified then VX is connected to DUT
    # The voltage amplified version of the output is connected to an AI via a buffer and voltage divider for reading
    # AI measures VX / 2 and [V1 / 2, V2 / 2, V3 / 3, V4 / 4] are connected to [A5, A4, A3, A2]
    #
    # In the general case of the 8-channel board only the NI-DAQ can be used to calibrate 4-channels at a time
    # so you may aswell develop a general calibration routine for the 4-channel and 8-channel varieties 
    # Include the option to perform measurements using the IBM4 AI if it is available

    # R. Sheehan 12 - 3 - 2026

    FUNC_NAME = ".Four_Channel_Calibration()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
         # instantiate an object that interfaces with the IBM4
        the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4

        c1 = the_dev.CommsStatus()
        c2 = len(pwmPins) > 0 and len(pwmPins) < 5
        c10 = c1 and c2

        if c10:
            # Board Name
            board_name = 'Four_Channel_PCB'

            # Name of the NI-DAQ
            device_name = 'Dev2'

            # Ground the IBM4 object
            the_dev.ZeroIBM4()

            # instantiate an object to keep track of the sweep space parameters
            no_steps = 11
            v_start = 0.0
            v_end = 91.0 # this should be equivalent to 3V output
            the_interval = Sweep_Interval.SweepSpace(no_steps, v_start, v_end)

            # Loop over the pwmPins list
            for p in range(0, len(pwmPins), 1):
                physical_channel_str = 'Dev2/ai%(v1)d'%{"v1":p}
                Calibrate_Single_Channel(board_name, pwmPins[p], the_interval, the_dev, physical_channel_str, device_name, True)

            MOVE_FILES = True
            if MOVE_FILES:
                # This can be optional
                # Move the files to a more convenient location
                # The location must exist on your computer, otherwise the files won't be moved
                DATA_HOME = 'c:/users/robertsheehan/Research/Electronics/uHeater_Control/'
                #DATA_HOME = 'D:/Rob/Research/Electronics/uHeater_Control/'

                txt_files = glob.glob("%(v1)s*.txt"%{"v1":board_name})

                Common.Move_Files(DATA_HOME, txt_files)

                png_files = glob.glob("%(v1)s*.png"%{"v1":board_name})
                Common.Move_Files(DATA_HOME, png_files)
        else:
            if not c1: ERR_STATEMENT += "\nCould not instantiate IBM4 object"
            if not c2: ERR_STATEMENT += "\nNo. pwm pins is outside range [1, 4]"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Calibrate_Single_Channel(brdName, pwmChnnl, swpIntrvl:Sweep_Interval.SweepSpace, uCtrlObj:IBM4_Lib.Ser_Iface, physical_channel_str = 'Dev2/ai0:3', device_name = 'Dev2', loud = False):

    """
    Routine for performing calibration measurement on a multi-channel micro-controller voltage source

    Inputs
    brdName (type: string) label for whichever board is being tested
    pwmChnnl (type: string) label for one of the available PWM channels from which voltage is sourced
    swpIntrvl (type: SweepSpace object) instantiated SweepSpace object
    uCtrlObj (type: Ser_Iface object) instantiated IBM4 object
    physical_channel_str(string) tells the DAQ which channels it wants to work from
    device_name(string) tells the PC what handle has been assigned to the DAQ by the PC

    Outputs
    cal_data (type: numpy array) array of size swpIntrvl.Nsteps * 3 with measurement data saved row-wise in the form [pwmVal, avg, stdev]

    R. Sheehan 13 - 3 - 2026
    """

    # Will need to know which channels are operational
    # Will need to know the calibration curve data for each channel

    FUNC_NAME = ".Sweep_Single_Channel()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = swpIntrvl.defined
        c2 = uCtrlObj.CommsStatus()
        c3 = pwmChnnl in uCtrlObj.PWM_Chnnls
        c10 = c1 and c2 and c3

        if c10:
            # Configure the NI-DAQ for AI read

            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = NI_DAQ_Lib.Extract_Sample_Rate(ai_chn_str, device_name)

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

            # create arrays for storing measured data
            cal_data = numpy.zeros((swpIntrvl.Nsteps, 3))

            pwmVal = swpIntrvl.start
            for i in range(0, swpIntrvl.Nsteps, 1):
                print("Writing PWM =",pwmVal)

                uCtrlObj.WriteAnyPWM(pwmChnnl, pwmVal)
                
                time.sleep(1) # Give the output time to settle

                # read the available data
                data = ai_task.read(nidaqmx.constants.READ_ALL_AVAILABLE)
                avg = numpy.mean(data)
                stdev = numpy.std(data, ddof = 1)
                cal_data[i] = numpy.array([pwmVal, avg, stdev])
                
                if loud: 
                    out_str = "ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f ( V )"%{"v1":0, "v2":avg, "v3":stdev}
                    print(out_str)

                pwmVal += swpIntrvl.delta

            ai_task.close()

            # process the calibration data
            Calibrate_Single_Channel_Processing(brdName, pwmChnnl, cal_data, loud)
        else:
            if not c1: ERR_STATEMENT += "\nswpintrvl object is not defined"
            if not c2: ERR_STATEMENT += "\nuCtrlObj object is not defined"
            if not c3: ERR_STATEMENT += "\npwmChnnl is not a defined in PWM_Chnnl"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Calibrate_Single_Channel_Processing(brdName, pwmChnnl, calData, loud = False):

    """
    Routine for processing calibration measurement data on a multi-channel micro-controller voltage source

    Inputs
    brdName (type: string) label for whichever board is being tested
    pwmChnnl (type: string) label for one of the available PWM channels from which voltage is sourced
    calData (type: numpy array) array of size swpIntrvl.Nsteps * 3 with measurement data saved row-wise in the form [pwmVal, avg, stdev]

    R. Sheehan 13 - 3 - 2026
    """

    # Will need to know which channels are operational
    # Will need to know the calibration curve data for each channel

    FUNC_NAME = ".Calibrate_Single_Channel_Processing()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = True if len(calData) > 0 else False

        if c1:
            # Export the data to memory
            handle = '%(v1)s_Pin_%(v2)s'%{"v1":brdName, "v2":pwmChnnl}
            filename = '%(v1)s_Pin_%(v2)s_Cal_Data.txt'%{"v1":brdName, "v2":pwmChnnl}
            if loud: print("Writing to", filename)
            numpy.savetxt(filename, calData, fmt = "%0.9f", delimiter = ',')

            # Compute linear fit to the dataset
            model = scipy.stats.linregress(calData[:,0], calData[:,1])

            # Export the computed cal curves to a file for future reference
            filename = '%(v1)s_Cal_Curves.txt'%{"v1":brdName}
            # open a file for writing, create file if necessary
            avg_file = open(filename, 'a' if os.path.exists(filename) else 'w')
            out_str = '%(v1)s, %(v2)0.9f, %(v3)0.9f\n'%{"v1":pwmChnnl, "v2":model.slope, "v3":model.intercept}
            if loud: print('\n'+out_str)
            avg_file.write(out_str)
            avg_file.close()            

            # Make a plot of the data with its linear fit
            args = Plotting.plot_arg_single()

            args.loud = loud
            # weirdly awkward to get python to print percentage symbol
            # https://www.geeksforgeeks.org/python/different-ways-to-escape-percent-in-python-strings/
            args.x_label = r'PWM value ( % )' 
            args.y_label = 'Output Voltage ( V )'
            args.curve_label = r'V$_{out}$ = %(v1)0.2f PWM %(v2)s %(v3)0.2f'%{"v1":model.slope, "v2":'+' if model.intercept > 0 else '-', "v3":abs(model.intercept)}
            args.plt_range = [0, 100, 0, 6]

            args.fig_name = '%(v1)s_Pin_%(v2)s_Cal_Curve'%{"v1":brdName, "v2":pwmChnnl}

            Plotting.plot_single_linear_fit_curve_with_errors(calData[:,0], calData[:,1], calData[:,2], args)
        else:
            if c1 != True: ERR_STATEMENT += "\ncalData is empty"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Board_Operation(pwmPins = ["D9", "D10", "D11", "D12"]):

    """
    Routine for operating a multi-channel micro-controller voltage source

    Inputs
    pins is an array of strings identifying the operational channels
    volts is an array of floats specifying the voltage values to be output on each channel

    """

    # Will need to know which channels are operational
    # Will need to know the calibration curve data for each channel

    FUNC_NAME = ".Board_Operation()" # use this in exception handling messages
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