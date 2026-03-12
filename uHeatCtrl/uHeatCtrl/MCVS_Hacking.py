"""
Initial attempts at hacking together code for the Multi-Channel Voltage Source

R. Sheehan 28 - 10 - 2025
"""

MOD_NAME_STR = "MCVS_Hacking"

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

def Calibrate_PWM_Filtered_DC_Conversion():
    
    # Calibrate the PWM- Filtered DC Conversion
    # Assumes that A2 - Filtered PWM and A3 - GND
    # R. Sheehan 28 - 10 - 2025

    # instantiate an object to keep track of the sweep space parameters
    no_steps = 5
    v_start = 0.0
    v_end = 100.0
    the_interval = Sweep_Interval.SweepSpace(no_steps, v_start, v_end)
    
    # instantiate an object that interfaces with the IBM4
    the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4
    
    # define some other constants
    DELAY = 0.25 # timed delay value in units of seconds
    no_reads = 25 # no. averages reads needed
    voltage_data = numpy.array([]) # instantiate an empty numpy array to store the sweep data
    pwmPin = "D13"
    pwmSet = the_interval.start # initiliase the PWM value
    count = 0
    while pwmSet < the_interval.stop+1:
        step_data = numpy.array([]) # instantiate an empty numpy array to hold the data for each step of the sweep
        the_dev.WriteAnyPWM(pwmPin, pwmSet)
        time.sleep(DELAY) # Apply a fixed delay
        pwmFilt = the_dev.DiffReadAverage('A2', 'A3', no_reads)
        # save the data
        step_data = numpy.append(step_data, pwmSet) # store the set-voltage value for this step
        step_data = numpy.append(step_data, pwmFilt) # store the  measured voltage values for this step
        # store the  set-voltage and the measured voltage values from all channels for this step
        # use append on the first step to initialise the voltage_data array
        # use vstack on subsequent steps to build up the 2D array of data
        voltage_data = numpy.append(voltage_data, step_data) if count == 0 else numpy.vstack([voltage_data, step_data])        
        pwmSet = pwmSet + the_interval.delta
        count = count + 1 if count == 0 else count # only need to increment count once to build up the array
    
    the_dev.ZeroIBM4() # ground the analog outputs
    #print('Sweep complete')
    #print(voltage_data.transpose())
    
    # Make a linear fit to the filtered PWM vs DC val data
    inter, slope = Common.linear_fit(voltage_data.transpose()[0], voltage_data.transpose()[1], [1,1])
    
    #print('Slope: %(v1)0.4f'%{"v1":slope})
    #print('Intercept: %(v1)0.4f'%{"v1":inter})
    print('Sweep complete')
    print('filtPWM_%(v1)s = %(v2)0.4f DC + %(v3)0.4f'%{"v1":pwmPin, "v2":slope, "v3":inter})
    
def Plot_Save_PWM_Calibration_Data(pwmPin, pwmData, INCLUDE_PWM_FILT = True, loud = False):
    
    # Make a plot of the measured PWM calibration data
    # pwmData is stored in the form [pwmSet, pwmFilt, pwmFilt_error, pwmAmp, pwmAmp_error] 
    # R. Sheehan 29 - 10 - 2025
    
    # Write the measured data to a file
    filename = '%(v1)s_PWM_T_Filt_Amp_Data.txt'%{"v1":pwmPin}
    numpy.savetxt(filename, pwmData, delimiter = '\t')

    # Declare the lists needed to generate the plots
    hv_data = []
    labels = []
    marks = []
    
    if INCLUDE_PWM_FILT:
        hv_data.append([pwmData.transpose()[0], pwmData.transpose()[1], pwmData.transpose()[2]])
        labels.append('%(v1)s Filt'%{"v1":pwmPin}); marks.append(Plotting.labs_pts[0]); 
        hv_data.append([pwmData.transpose()[0], pwmData.transpose()[3], pwmData.transpose()[4]])
        labels.append('%(v1)s Amp'%{"v1":pwmPin}); marks.append(Plotting.labs_pts[1]);
    else:
        hv_data.append([pwmData.transpose()[0], pwmData.transpose()[1], pwmData.transpose()[2]])
        labels.append('%(v1)s Amp'%{"v1":pwmPin}); marks.append(Plotting.labs_pts[1]); 

    # Generate the combined plot with error bars
    args = Plotting.plot_arg_multiple()
    
    args.loud = loud
    args.crv_lab_list = labels
    args.mrk_list = marks
    args.x_label = 'PWM Duty Cycle (%)'
    args.y_label = 'PWM Output (V)'
    args.plt_range = [0, 105, 0, 6]
    args.fig_name = filename.replace('.txt','')
    
    Plotting.plot_multiple_linear_fit_curves(hv_data, args)

def Linear_Fit_PWM_Calibration_Data(pwmPin, pwmData, INCLUDE_PWM_FILT = True, loud = False):

    # Perform a linear fit to the measured PWM calibration data
    # pwmData is stored in the form [pwmSet, pwmFilt, pwmFilt_error, pwmAmp, pwmAmp_error] 
    # R. Sheehan 29 - 10 - 2025
    
    # Make a linear fit to the filtered PWM vs DC val data
    if INCLUDE_PWM_FILT:
        interPWM, slopePWM = Common.linear_fit(pwmData.transpose()[0], pwmData.transpose()[1], [1,1])
        interAmp, slopeAmp = Common.linear_fit(pwmData.transpose()[0], pwmData.transpose()[3], [1,1])
    else:
        interAmp, slopeAmp = Common.linear_fit(pwmData.transpose()[0], pwmData.transpose()[1], [1,1])
    
    if loud:
        print('Sweep complete %(v1)s'%{"v1":pwmPin})
        if INCLUDE_PWM_FILT:
            print('filtPWM_%(v1)s = %(v2)0.4f DC + %(v3)0.4f'%{"v1":pwmPin, "v2":slopePWM, "v3":interPWM})
        print('ampPWM_%(v1)s = %(v2)0.4f DC + %(v3)0.4f'%{"v1":pwmPin, "v2":slopeAmp, "v3":interAmp})
    
    # Write the computed fit coefficients to a file
    lin_coeff_file = 'PWM_T_DC_AMP_Fit_Parameters.txt'
    
    if glob.glob(lin_coeff_file):
        # file exists, open it and append data to it
        the_file = open(lin_coeff_file, "a")
        if INCLUDE_PWM_FILT:
            the_file.write("%(v1)s, %(v2)0.9f, %(v3)0.9f, %(v4)0.9f, %(v5)0.9f\n"%{"v1":pwmPin, "v2":slopePWM, "v3":interPWM, "v4":slopeAmp, "v5":interAmp})
        else:
            the_file.write("%(v1)s, %(v4)0.9f, %(v5)0.9f\n"%{"v1":pwmPin, "v4":slopeAmp, "v5":interAmp})
    else:
        # file does not exist, create it, and write data to it
        the_file = open(lin_coeff_file, "w")
        if INCLUDE_PWM_FILT:
            the_file.write("PWM Pin No., DC Slope, DC Intercept, Amp Slope, Amp Intercept\n")
            the_file.write("%(v1)s, %(v2)0.9f, %(v3)0.9f, %(v4)0.9f, %(v5)0.9f\n"%{"v1":pwmPin, "v2":slopePWM, "v3":interPWM, "v4":slopeAmp, "v5":interAmp})
        else:
            the_file.write("PWM Pin No., Amp Slope, Amp Intercept\n")
            the_file.write("%(v1)s, %(v4)0.9f, %(v5)0.9f\n"%{"v1":pwmPin, "v4":slopeAmp, "v5":interAmp})

def Calibrate_PWM_Filtered_DC_Amp_Conversion(loud = False):
    
    # Calibrate the PWM- Filtered DC - Amp output Conversion
    # Assumes that A2 - Filtered PWM and A3 - Reduced Amp output and A4, A5, D2 are GND
    # R. Sheehan 28 - 10 - 2025

    # instantiate an object to keep track of the sweep space parameters
    no_steps = 50
    v_start = 0.0
    v_end = 55.0
    the_interval = Sweep_Interval.SweepSpace(no_steps, v_start, v_end)
    
    # instantiate an object that interfaces with the IBM4
    the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4
    
    # define some other constants
    DELAY = 0.1 # timed delay value in units of seconds
    no_reads = 25 # no. averages reads needed
    R1 = 9.87 # voltage divider R1
    R2 = 9.93 # voltage divider R2
    sf = R2 / (R1 + R2) # voltage divider scale factor
    fs = 1.0 / sf # inverse of voltage divider scale factor
    voltage_data = numpy.array([]) # instantiate an empty numpy array to store the sweep data
    pwmPin = "D9"
    pwmSet = the_interval.start # initiliase the PWM value
    print('Calibrating PWM pin:%(v1)s'%{"v1":pwmPin})
    count = 0

    INCLUDE_PWM_FILT = False # switch to include measurement of filtered PWM output
    
    start = time.time() # start the measurement timer
    
    while pwmSet < the_interval.stop+1:
        step_data = numpy.array([]) # instantiate an empty numpy array to hold the data for each step of the sweep
        the_dev.WriteAnyPWM(pwmPin, pwmSet)
        time.sleep(DELAY) # Apply a fixed delay
        #pwmFilt = the_dev.ReadAverageVoltageAllChnnl(no_reads)
        if INCLUDE_PWM_FILT:
                pwmFilt = the_dev.DiffReadMultiple('A2', 'A4', no_reads)
        pwmAmp = the_dev.DiffReadMultiple('A3', 'A4', no_reads) # this value is being read through a voltage divider
        # save the data
        step_data = numpy.append(step_data, pwmSet) # store the set-voltage value for this step
        if INCLUDE_PWM_FILT:
            step_data = numpy.append(step_data, pwmFilt[0]) # store the measured voltage for this step
            step_data = numpy.append(step_data, pwmFilt[1]) # store the measured error for this step
        step_data = numpy.append(step_data, fs * pwmAmp[0]) # store the measured voltage for this step
        step_data = numpy.append(step_data, fs * pwmAmp[1]) # store the measured error for this step
        # store the  set-voltage and the measured voltage values from all channels for this step
        # use append on the first step to initialise the voltage_data array
        # use vstack on subsequent steps to build up the 2D array of data
        voltage_data = numpy.append(voltage_data, step_data) if count == 0 else numpy.vstack([voltage_data, step_data])        
        pwmSet = pwmSet + the_interval.delta
        count = count + 1 if count == 0 else count # only need to increment count once to build up the array
    
    end = time.time() # end the measurement timer
    deltaT = end-start # total measurement time
    measT = deltaT/(float(no_steps)) # single measurement time 
    print('Sweep complete\n')
    print("\n%(v1)d measurements performed in %(v2)0.3f seconds"%{"v1":no_steps, "v2":deltaT})
    print("%(v1)0.4f secs / measurement\n"%{"v1":measT})
        
    the_dev.ZeroIBM4() # ground the analog outputs
    
    if loud: print(voltage_data.transpose())
    
    # Write the measured data to a file and generate a plot of the measured data
    Plot_Save_PWM_Calibration_Data(pwmPin, voltage_data, INCLUDE_PWM_FILT)
    
    # Make a linear fit to the measured data
    Linear_Fit_PWM_Calibration_Data(pwmPin, voltage_data, INCLUDE_PWM_FILT, loud = True)
    
def Compute_Average_Cal_Parameters():
    
    # Import the data for the calibration curves for each PWM pin
    # Find the average over all the calibration curves
    # R. Sheehan 29 - 10 - 2025

    filename = 'PWM_DC_AMP_Fit_Parameters.txt'
    
    if glob.glob(filename):
        theData = numpy.loadtxt(filename, unpack = True, delimiter = ',',skiprows = 1, usecols=(1, 2, 3, 4))
                
        # Is the cal curve for D13 actually that different? 
        # Yes the value computed from D13 is sufficiently different 17 (mV)
        # to warrant it's being treated differently
        
        m1 = numpy.mean(theData[0][0:-2]); c1 = numpy.mean(theData[1][0:-2]); 
        m2 = numpy.mean(theData[0]); c2 = numpy.mean(theData[1]); 
        m3 = numpy.mean(theData[2][0:-2]); c3 = numpy.mean(theData[3][0:-2]); 
        m4 = numpy.mean(theData[2]); c4 = numpy.mean(theData[3]); 
        
        DC = 30
        v1 = m1*DC+c1; v2 = m2*DC+c2; pwmErr = math.fabs(v1-v2); 
        v3 = m3*DC+c3; v4 = m4*DC+c4; ampErr = math.fabs(v3-v4); 
        
        print('PWM Slope:',m1,', PWM Intercept:',c1)
        print('PWM Slope Alt:',m2,', PWM Intercept Alt:',c2)
        print('Amp Slope:',m3,', Amp Intercept:',c3)
        print('Amp Slope:',m4,', Amp Intercept:',c4)        
        
        print('\nPWM val: %(v1)0.3f (V), PWM val: %(v2)0.3f (V), Err: %(v3)0.3f (V)'%{"v1":v1, "v2":v2, "v3":pwmErr})
        print('Amp val: %(v1)0.3f (V), Amp val: %(v2)0.3f (V), Err: %(v3)0.3f (V)'%{"v1":v3, "v2":v4, "v3":ampErr})

def Long_Voltage_Measure():

    # Perform a long-time voltage measurement using the uCtrl PCB
    # Use the available read channels to read 3 different values
    # Use an external power supply with constant voltage for comparison
    # R. Sheehan 15 - 12 - 2025

    # As it is I can use 2-PWM channels to output DC signal
    pwmPin1 = 'D1'
    pwmPin2 = 'D7'
    pwmSet = 25
    T_sep = 10 # time between measurements in sec
    N_meas = 100 # total no. meas
    N_reads = 10
    voltage_data = numpy.array([]) # instantiate an empty numpy array to store the sweep data

    # instantiate an object that interfaces with the IBM4
    the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4

    # output voltage on both pwmPins
    the_dev.ZeroIBM4()
    the_dev.WriteAnyPWM(pwmPin1, pwmSet) 
    the_dev.WriteAnyPWM(pwmPin2, pwmSet)
    print(the_dev.ReadAverageVoltageAllChnnl(N_reads))
    time.sleep(T_sep)    

    ACTUALLY_RUN_MEAS = True

    if ACTUALLY_RUN_MEAS:
        count = 0
        start_meas = time.time() # start of measurement
        while count < N_meas:
            step_data = numpy.array([]) # instantiate an empty numpy array to store the sweep data
            # read an averaged voltage reading across all channels
            # It's being assumed that A2 -> External Power Supply Reference Voltage, A3 -> pwmPin1, A4 -> pwmPin2, A5 ->  GND, D2 -> GND
            # Want to save the differential readings relative to GND
            step_data = the_dev.ReadAverageVoltageAllChnnl(N_reads)        
            this_meas = time.time() # record time since start of measurement
            elapsed = (this_meas - start_meas) / 60.0 # time since start of measurement in minutes
            step_data = 2.0*(step_data[0:3] - step_data[-1]) # subtract the ground value from all readings, re-scale and drop the values you don't want        
            step_data = numpy.insert(step_data, 0, elapsed) # save elapsed time, External Power Supply Reference Voltage, pwmPin1, pwmPin2
            # store the time-data and the measured voltage values from all channels for this step
            # use append on the first step to initialise the voltage_data array
            # use vstack on subsequent steps to build up the 2D array of data
            voltage_data = numpy.append(voltage_data, step_data) if count == 0 else numpy.vstack([voltage_data, step_data])        
            time.sleep(T_sep)
            count += 1

        end_meas = time.time() # end of measurement

        del the_dev

        print()
        print("Measurement complete. Total Time: ",(end_meas - start_meas) / 60.0," minutes")
        print()

        filename = 'PCB_PWM_Test_Data_%(v1)s_%(v2)s.txt'%{"v1":pwmPin1, "v2":pwmPin2}
        numpy.savetxt(filename, voltage_data, delimiter = '\t')

        # Report on the data
        averages = numpy.array([])
        stdevs = numpy.array([])
        voltages = ['Reference', pwmPin1, pwmPin2]
        hv_data = []; marks = [];
        # remember that voltage_data is saved in row-format
        # no-columns equals no-elements in each row
        # probably easier just to work with the transpose of the array
        # but I like using the list-slice grammar, probably more efficient than taking a transpose
        for i in range(1, len(voltage_data[0]), 1):
            averages = numpy.append(averages, numpy.mean(voltage_data[:,i]) ) # select the columns
            stdevs = numpy.append(stdevs, numpy.std(voltage_data[:,i], ddof = 1) )
        
            hv_data.append([voltage_data[:,0], voltage_data[:,i]])
            marks.append(Plotting.labs_lins[i])

        print("\nAverage Measured Values")
        for i in range(0, len(averages), 1):
            print('%(v1)s: %(v2)0.3f +/- %(v3)0.3f (V)'%{"v1":voltages[i], "v2":averages[i], "v3":stdevs[i]})

        # Make a time series plot of the data
        args = Plotting.plot_arg_multiple()

        args.loud = False
        args.mrk_list = marks
        args.crv_lab_list = voltages
        args.x_label = 'Time ( min )'
        args.y_label = 'Voltage ( V )'
        args.fig_name = 'PCB_Output_%(v1)s_%(v2)s'%{"v1":pwmPin1, "v2":pwmPin2}

        Plotting.plot_multiple_curves(hv_data, args)

        # Make a histogram of the data
        # scale the data horizontally so that the distributions sit on top of one another
        # emphasise the similarities between the distributions

        # Use Sturges' Rule to compute the no. of bins required
        n_bins = int( 1.0 + 3.322*math.log( len(voltage_data[:,0]) ) )

        scl_data = numpy.array([])
        for i in range(0, len(averages), 1):
            scl_data = numpy.append(scl_data, (voltage_data[:,i+1] - averages[i] ) / stdevs[i] ) if i==0 else numpy.vstack([scl_data, (voltage_data[:,i+1] - averages[i] ) / stdevs[i] ])

        plt.hist(scl_data[0], bins = n_bins, label = r'%(v1)s $\sigma$ = %(v2)0.2f mV'%{"v1":voltages[0], "v2":1000.0*stdevs[0]}, alpha=0.9, color = 'red', edgecolor = 'black', linestyle = '-')
        plt.hist(scl_data[1], bins = n_bins, label = r'%(v1)s $\sigma$ = %(v2)0.2f mV'%{"v1":voltages[1], "v2":1000.0*stdevs[1]}, alpha=0.65, color = 'green' , edgecolor = 'black', linestyle = '--')
        plt.hist(scl_data[2], bins = n_bins, label = r'%(v1)s $\sigma$ = %(v2)0.2f mV'%{"v1":voltages[2], "v2":1000.0*stdevs[2]}, alpha=0.6, color = 'blue', edgecolor = 'black', linestyle = ':' )
        plt.xlim(xmin=-3, xmax = 3)
        plt.xlabel(r'Scaled Measurements $( V_{i} - \mu ) / \sigma$', fontsize = 14)
        plt.ylabel('Counts', fontsize = 14)
        plt.legend(loc = 'best')
        plt.savefig('Historgram_PCB_Output_%(v1)s_%(v2)s'%{"v1":pwmPin1, "v2":pwmPin2})
        #plt.show()            
        plt.clf()
        plt.cla()
        plt.close()

def PCB_Voltage_Control():

    # Control the voltage output of the PCB 
    # R. Sheehan 7 - 1 - 2026

    ERR_STATEMENT = "Error: PCB_Voltage_Control"

    try:
        # instantiate an object that interfaces with the IBM4
        the_dev = IBM4_Lib.Ser_Iface() # this version should find the first connected IBM4

        if the_dev.CommsStatus():

            DELAY = 0.1 # timed delay value in units of seconds
            Vmin = 0.0
            Vmax = 6.0
            pwmPin = "D9"

            # fit parameters for converting PWM DC to Vout
            # Vout = m1 DC + c1
            m1 = 0.108221577
            c1 = -0.121880690

            # fit parameters for converting Vout to PWM DC
            # DC = m2 * Vout - c2
            m2 = (1.0 / m1)
            c2 = ( c1 / m1)

            do = True
            while do:
                action = int( input( PCBPrompt() ) )
                if action == -1:
                    print('\nEnd Program\n')
                    the_dev.ZeroIBM4()
                    do = False
                elif action == 1:
                    print('\nSet PCB Voltage\n')
                    axvolt = float( input('Enter a voltage value between 0V and 6V: ') )
                    axvolt = max( min(axvolt, Vmax), Vmin)
                    pwmSet = int( ( ( m2 * axvolt ) - c2 ) )
                    the_dev.WriteAnyPWM(pwmPin, pwmSet)
                    time.sleep(DELAY) # Apply a fixed delay
                    continue
                elif action == 2:
                    print('\nGround PCB\n')
                    the_dev.ZeroIBM4()
                    continue
                else:
                    continue
        else:
            ERR_STATEMENT = ERR_STATEMENT + '\nCannot proceed, unable to connect to IBM4 device'
            raise Exception        
    except Exception as e:
        print(ERR_STATEMENT)
        print(e)

def PCBPrompt():
    """
    text processing for the PCB Option prompt
    """
        
    start = '\nVoltage Output Using PCB:\n';
    message = '\nInput Value to Indicate Option You Require: ';
    newline = '\n'

    option1 = 'Set PCB Voltage Output'; # Set voltage at D9
    option2 = 'Ground PCB'; # Gnd all outputs
    option3 = 'Close Comms'; # End multimeter mode
    
    theOptions = [option1, option2, option3]
    
    theValues = ['1', '2', '-1']
    
    width = max(len(item) for item in theOptions) + 5
        
    prompt = start
    for i in range(0, len(theOptions), 1):
        prompt = prompt + theOptions[i].ljust(width) + theValues[i] + newline
    prompt = prompt + message
        
    return prompt