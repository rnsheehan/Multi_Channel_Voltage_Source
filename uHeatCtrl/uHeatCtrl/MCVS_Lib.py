"""
Library that implements the code needed to control the Multi-Channel Voltage Source

R. Sheehan 12 - 3 - 2026
"""

MOD_NAME_STR = "MCVS_Lib"

# import packages
from asyncio.windows_events import ERROR_CONNECTION_ABORTED
import os
import glob
import time
import numpy
import scipy
import random
import Common
import Plotting
import Sweep_Interval
import IBM4_Lib # IBM4 interface based on Serial
import nidaqmx
import NI_DAQ_Lib
import pandas

pwmChnnlList = {"D0":0, "D1":1, "D7":7, "D9":9, "D10":10, "D11":11, "D12":12, "D13":13}

def Pin_Mapping(brdName = 'Four_Channel_PCB', voltChnnls = ['V1', 'V2', 'V3', 'V4']):

    """
    Map the voltage channels to the PWM pins on the IBM4 board
    Use dictionary to create a general mapping

    R. Sheehan 18 - 3 - 2026
    """

    FUNC_NAME = ".Pin_Mapping()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        if brdName == 'Four_Channel_PCB':
            mapping = {'V1':'D7', 'V2':'D9', 'V3':'D10', 'V4':'D11'}
            #return [mapping[v] for v in voltChnnls]
        elif brdName == 'Eight_Channel_PCB':
            mapping = {'V1':'D0', 'V2':'D1', 'V3':'D7', 'V4':'D9', 'V5':'D10', 'V6':'D11', 'V7':'D12', 'V8':'D13'}
            #return [mapping[v] for v in voltChnnls]
        else:
            ERR_STATEMENT += '\nBoard: %(v1)s not recognised'%{"v1":brdName}
            raise Exception
        # select the pins that map V* onto PWM*
        # general method to prevent duplicates
        # an exception is thrown if voltChnnls contains inappropriate entry
        seen = set()
        pwmPins = []
        for v in voltChnnls:
            d = mapping[v]
            if d not in seen:
                seen.add(d)
                pwmPins.append(d)
        return pwmPins        
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Multi_Channel_Calibration(brdName, voltChnnls = ['V1', 'V2', 'V3', 'V4']):
    """
    Calibration routine for multiple-channels of the Micro-Controller Voltage Source
    Calibration is performed using NI-DAQ, which limits the number of channels that can be calibrated at any one time to 4
    Calibration is performed sequentially on each channel, while other channels are at ground

    Inputs
    pwmPins (type: str list) list containing the names of the PWM pins being calibrated

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

    FUNC_NAME = ".Multi_Channel_Calibration()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
         # instantiate an object that interfaces with the IBM4
        the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4
        pwmPins = Pin_Mapping(brdName, voltChnnls) # map voltage channels onto the IBM4 digital outputs

        c1 = the_dev.CommsStatus()
        c2 = len(pwmPins) > 0 and len(pwmPins) < 5
        c10 = c1 and c2

        if c10:
            # Board Name
            #board_name = 'Four_Channel_PCB'
            #board_name = 'Eight_Channel_PCB'

            # Name of the NI-DAQ
            device_name = 'Dev1'

            # Ground the IBM4 object
            the_dev.ZeroIBM4()

            # instantiate an object to keep track of the sweep space parameters
            no_steps = 51
            v_start = 0.0
            v_end = 91.0 # this should be equivalent to 3V output
            the_interval = Sweep_Interval.SweepSpace(no_steps, v_start, v_end)

            # Loop over the pwmPins list
            for p in range(0, len(pwmPins), 1):
                physical_channel_str = '%(v1)s/ai%(v2)d'%{"v1":device_name, "v2":p}
                Calibrate_Single_Channel(brdName, pwmPins[p], the_interval, the_dev, physical_channel_str, device_name)

            MOVE_FILES = False
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

    FUNC_NAME = ".Calibrate_Single_Channel()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = swpIntrvl.defined
        c2 = uCtrlObj.CommsStatus()
        c3 = pwmChnnl in uCtrlObj.PWM_Chnnls
        c4 = brdName != ''
        c10 = c1 and c2 and c3 and c4

        if c10:
            # Configure the NI-DAQ for AI read

            # Extract the sample rate per channel
            ai_chn_str = physical_channel_str

            ai_SR, ai_no_ch = NI_DAQ_Lib.Extract_Sample_Rate(ai_chn_str, device_name)

            # Configure Analog Input
            ai_task = nidaqmx.Task()        

            # If ai_chn_str is not correctly defined an exception will be thrown by nidaqmx
            ai_task.ai_channels.add_ai_voltage_chan(ai_chn_str, terminal_config = nidaqmx.constants.TerminalConfiguration.DIFF, min_val = -10, max_val = +10)
            
            # Configure the sampling timing
            # Note that when reading data later no. samples to be read must equal samps_per_chan as defined
            # Otherwise an exception will be thrown by nidaqmx
            ai_task.timing.cfg_samp_clk_timing(ai_SR, sample_mode = nidaqmx.constants.AcquisitionType.FINITE, 
                                                samps_per_chan = ai_SR, active_edge = nidaqmx.constants.Edge.RISING)

            # create arrays for storing measured data
            cal_data = numpy.zeros((swpIntrvl.Nsteps, 3))

            pwmVal = swpIntrvl.start
            
            print("\nCalibrating on pin:",pwmChnnl)
            for i in range(0, swpIntrvl.Nsteps, 1):
                if loud: print("Writing PWM =",pwmVal)

                uCtrlObj.WriteAnyPWM(pwmChnnl, pwmVal)
                
                time.sleep(3) # Give the output time to settle, this is quite necessary

                # read the available data
                data = ai_task.read(nidaqmx.constants.READ_ALL_AVAILABLE)
                avg = numpy.mean(data)
                stdev = numpy.std(data, ddof = 1)
                cal_data[i] = numpy.array([pwmVal, avg, stdev])
                
                if loud: 
                    out_str = "ai%(v1)d: %(v2)0.4f +/- %(v3)0.4f ( V )"%{"v1":0, "v2":avg, "v3":stdev}
                    print(out_str)

                pwmVal += swpIntrvl.delta

            uCtrlObj.WriteAnyPWM(pwmChnnl, 0.0) # reset PWM val to 0.0

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
        c1 = brdName != ''
        c2 = pwmChnnl in pwmChnnlList
        c3 = len(calData) > 0
        c10 = c1 and c2 and c3

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
            #avg_file = open(filename, 'a' if os.path.exists(filename) else 'w')
            writeTitle = False
            if os.path.exists(filename):
                # open the file in append mode
                avg_file = open(filename, 'a')
            else:
                # open /create the file in write mode
                writeTitle = True
                avg_file = open(filename, 'w')
            title_str = r'Pin, Slope (V / %), Intercept (V)\n'
            out_str = '%(v1)s, %(v2)0.9f, %(v3)0.9f\n'%{"v1":pwmChnnl, "v2":model.slope, "v3":model.intercept}
            if loud: print('\n'+out_str)
            # put the titles at the tope of the file when writing to the file for the first time
            if writeTitle:
                avg_file.write(title_str)
                writeTitle = False
            avg_file.write(out_str)
            avg_file.close()            

            # Make a plot of the data with its linear fit
            args = Plotting.plot_arg_single()

            args.loud = loud
            # weirdly awkward to get python to print percentage symbol
            # https://www.geeksforgeeks.org/python/different-ways-to-escape-percent-in-python-strings/
            args.x_label = r'PWM value ( % )' 
            args.y_label = 'Output Voltage ( V )'
            args.curve_label = r'V$_{out}$ = %(v1)0.4f PWM %(v2)s %(v3)0.4f'%{"v1":model.slope, "v2":'+' if model.intercept > 0 else '-', "v3":abs(model.intercept)}
            args.plt_range = [0, 100, 0, 6]

            args.fig_name = '%(v1)s_Pin_%(v2)s_Cal_Curve'%{"v1":brdName, "v2":pwmChnnl}

            Plotting.plot_single_linear_fit_curve_with_errors(calData[:,0], calData[:,1], calData[:,2], args)
        else:
            if not c1: ERR_STATEMENT += "\ncalData is empty"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Board_Operation(brdName, voltChnnls = ['V1', 'V2', 'V3', 'V4'], includeIBM4read = False, includeNIDAQread = False, loud = False):

    """
    Routine for operating a multi-channel micro-controller voltage source

    Inputs
    brdName (type: string) label for whichever board is being tested
    pwmPins (type: str list) list containing the names of the PWM pins being calibrated

    R. Sheehan 13 - 3 - 2026
    """

    # Will need to know which channels are operational
    # Will need to know the calibration curve data for each channel
    # Try to set this up with some kind of interruptable loop so that the values can be changed without comms having to be constantly reset

    FUNC_NAME = ".Board_Operation()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
         # instantiate an object that interfaces with the IBM4
        the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4

        pwmPins = Pin_Mapping(brdName, voltChnnls) # map voltage channels onto the IBM4 digital outputs

        lower = 0.0
        upper = 5.0
        noPins = len(pwmPins) # record the no. pins required

        c1 = the_dev.CommsStatus()
        c2 = noPins > 0 and noPins < 9
        c10 = c1 and c2

        if c10:
            the_dev.ZeroIBM4()

            # Read the calibration curve data for PCB brdName
            calData = Get_Cal_Curve_Data(brdName)

            try:
                while True:
                    input("\nPress Enter to proceed with voltage selection. \nPress Ctrl+C to stop.\n")
                    # Create an array for holding the voltage values
                    voltVals = Get_Volt_Vals(noPins, lower, upper, True)

                    # Write the voltage values to the PCB
                    Assign_Volt_Vals(calData, pwmPins, voltVals, the_dev)

                    # Read the assigned values using the IBM4 itself, only possible for 'Four_Channel_PCB'
                    if includeIBM4read: Perform_IBM4_Read(pwmPins, the_dev)

                    # Read the output values using the NI-DAQ
                    if includeNIDAQread: 
                        physical_channel_str = 'Dev1/ai0:3'
                        device_name = 'Dev1'
                        measVals = NI_DAQ_Lib.AI_DC_Read(physical_channel_str, device_name, loud = True)

                        for i in range(0, len(measVals), 1):
                            deltaV = voltVals[i] - measVals[i]
                            print("Delta V = %(v1)0.1f ( mV )"%{"v1":1000.0*deltaV})

            except KeyboardInterrupt:
                    # Ordinarily, you can ignore any errors associated with KeyboardInterrupt, use pass to ignore them
                    # Release the resources associated with IBM4 after KeyboardInterrupt
                    the_dev.ZeroIBM4()
        else:
            if not c1: ERR_STATEMENT += "\nCould not instantiate IBM4 object"
            if not c2: ERR_STATEMENT += "\nNo. pwm pins is outside range [1, 8]"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Get_Volt_Vals(noVals, limLow = 0.0, limHigh = 5.0, randomVals = False):
    """
    Method for populating a numpy array using keyboard input
    Values entered will be forced between limits limLow <= X <= limHigh
    Alternatively, a set of random voltages between limits limLow <= X <= limHigh can be assigned

    R. Sheehan 13 - 3 - 2026
    """

    FUNC_NAME = ".Get_Volt_Vals()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = noVals > 0 and noVals < 9

        if c1:
            voltVals = numpy.zeros(noVals)
            if not randomVals:
                # let user specify voltVals
                print("Please enter %(v1)d voltage values in the range [ %(v2)0.1f, %(v3)0.1f ]"%{"v1":noVals, "v2":limLow, "v3":limHigh})
                for i in range(0, noVals, 1):
                    qry_str = "Voltage %(v1)d: "%{"v1":i}
                    value = float( input( qry_str ) )
                    # Force input value into the range [ limLow, limHigh ]
                    voltVals[i] = min( max(limLow, value), limHigh)
            else:
                # randomly assign values to voltVals
                print("Generating %(v1)d random voltage values in the range [ %(v2)0.1f, %(v3)0.1f ]"%{"v1":noVals, "v2":limLow, "v3":limHigh})
                random.seed() # seed the rng with the current system time
                for i in range(0, noVals, 1):
                    voltVals[i] = limLow + (limHigh - limLow) * random.random() # generate random number in range [limLow, limHigh] using formula a + (b - a) * random()
            print("Voltage set values:",voltVals)

            return voltVals
        else:
            if not c1: ERR_STATEMENT += "\nNo. voltage values is outside range [1, 8]"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Get_Cal_Curve_Data(brdName):

    """
    Read the calibration curve data from file

    Input
    brdName (type str) string for identifying the cal-curve data for a particular board
    cal-data is stored in file with name in the form calFile = '%(v1)s_Cal_Curves.txt'%{"v1":brdName}

    Outputs
    calData (type data frame) with data stored in the form [pins, slopes, intercepts]
    
    pins is a list of strings indicating which pins have been calibrated
    slopes, intercepts are numpy arrays containing the cal-curve values for each pin
    cal-curve is linear of the form V = m PWM + c

    R. Sheehan 16 - 3 - 2026
    """

    FUNC_NAME = ".Get_Cal_Curve_Data()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        calFile = '%(v1)s_Cal_Curves.txt'%{"v1":brdName}
        c1 = brdName != ''
        c2 = os.path.exists(calFile)
        c10 = c1 and c2

        if c10:
            # Read the data into memory from the file, treat the data as a data frame
            # Data is stored in the file in the form
            # out_str = '%(v1)s, %(v2)0.9f, %(v3)0.9f\n'%{"v1":pwmChnnl, "v2":model.slope, "v3":model.intercept}
            calData = pandas.read_csv(calFile)

            # Could return the data as individual items, but why bother
            # Just use the dataFrame to do the computations that you need since you have to keep all the data in memory anyway
            # titles = list(data)
            # pins = data[titles[0]].to_list() 
            # slopes = data[titles[1]].to_numpy() 
            # intercepts = data[titles[2]].to_numpy() 

            return calData
        else:
            if not c1: ERR_STATEMENT += "\nbrdName is not defined"
            if not c2: ERR_STATEMENT += "\n%(v1)s cannot be found"%{"v1":calFile}
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Get_PWM_From_Cal_Data(calDF, pwmPin, voltVal):
    """
    Compute the PWM value needed to generate a desired voltage value

    Inputs
    calDF (type data frame) DF containing the cal-curve data
    
    
    R. Sheehan 16 - 3 - 2026
    """

    FUNC_NAME = ".Get_PWM_From_Cal_Data()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = not calDF.empty

        if c1:
            titles = list(calDF)

            # alternatively convert the DF data to lists and work from that
            # pins = data[titles[0]].to_list() 
            # slopes = data[titles[1]].to_numpy() 
            # intercepts = data[titles[2]].to_numpy() 

            if pwmPin in calDF[titles[0]].values:
                pcValMin = 0.0 # lower bound for PWM val
                pcValMax = 91.0 # upper bound for PWM val
                # Extract the DF subset that contains the cal-data for pwmPin
                x = calDF.loc[calDF[titles[0]] == pwmPin]
                # extract cal-curve data for pwmPin
                slope = x[ titles[1] ].values[0]
                intercept = x[ titles[2] ].values[0]
                # compute pwmVal by inverting the cal-curve
                pwmVal = (voltVal / slope) - (intercept / slope)
                # ensure that pwmVal is selected within appropriate bounds
                return min( pcValMax, max( pcValMin, pwmVal ) )
            else:
                ERR_STATEMENT += "\nCalibration data not available for %(v1)s"%{"v1":pwmPin}
                raise Exception
        else:
            if not c1: ERR_STATEMENT += "\ncalDF is empty, calculation cannot proceed"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Assign_Volt_Vals(calDF, pwmPins, voltVals, uCtrlObj:IBM4_Lib.Ser_Iface):
    """
    Assign the desired voltage values to the pins

    R. Sheehan 13 - 3 - 2026
    """

    FUNC_NAME = ".Board_Operation()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c1 = not calDF.empty
        c2 = len(pwmPins) > 0
        c3 = len(voltVals) == len(pwmPins)
        c4 = uCtrlObj.CommsStatus()
        c10 = c1 and c2 and c3 and c4

        if c10:
            # Assign the voltage value to the pins
            deltaV = 0.0 # offset that needs to be applied to make PWM output match user input
            for i in range(0, len(pwmPins), 1):
                # compute the PWM percentage value from the calibration curve data
                pcVal = Get_PWM_From_Cal_Data(calDF, pwmPins[i], voltVals[i]-deltaV)
                uCtrlObj.WriteAnyPWM(pwmPins[i], pcVal)
                time.sleep(3) # Induce a known delay between voltage value changes
        else:
            if not c1: ERR_STATEMENT += "\ncalDF is empty, calculation cannot proceed"
            if not c2: ERR_STATEMENT += "\npwmPins is not defined"
            if not c3: ERR_STATEMENT += "\nvoltVals is not defined"
            if not c4: ERR_STATEMENT += "\nuCtrlObj object is not defined"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def Perform_IBM4_Read(pwmPins, uCtrlObj:IBM4_Lib.Ser_Iface):
    """
    Use the IBM4 to perform a read operation on the PWM outputs
    Note this is only possible where the PCB has been configured to enable this
    For now only possible with 'Four_Channel_PCB'

    R. Sheehan 18 - 3 - 2026
    """

    FUNC_NAME = ".Perform_IBM4_Read()" # use this in exception handling messages
    ERR_STATEMENT = "Error: " + MOD_NAME_STR + FUNC_NAME

    try:
        c2 = len(pwmPins) > 0        
        c4 = uCtrlObj.CommsStatus()
        c10 = c2 and c4

        if c10:
            time.sleep(1)
            
            print("IBM4 Readings")
            readings = uCtrlObj.ReadAverageVoltageAllChnnl()
            #print(readings[::-1]) # print the array in reverse order
            for i in range(0, len(readings)-1, 1):
                readings[i] = 2.0*readings[i] - readings[-1]
            for i in range(0, len(readings)-1, 1):
                print("V%(v1)d = %(v2)0.2f ( V )"%{"v1":i+1, "v2":readings[::-1][i+1]})
            print()
            
        else:
            if not c2: ERR_STATEMENT += "\npwmPins is not defined"
            if not c4: ERR_STATEMENT += "\nuCtrlObj object is not defined"
            raise Exception
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)
