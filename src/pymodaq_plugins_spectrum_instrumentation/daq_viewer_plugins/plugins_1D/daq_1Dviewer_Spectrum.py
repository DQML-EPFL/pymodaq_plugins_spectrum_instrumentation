import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_Single import Spectrum_Wrapper_Single
from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_Multi import Spectrum_Wrapper_Multi
from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_FIFO import Spectrum_Wrapper_FIFO

import time
from scipy import signal

#TODO : Make Post trig variable in multo
#TODO : Make it possible to change params without rebooting card

class DAQ_1DViewer_Spectrum(DAQ_Viewer_base):
    """ Instrument plugin class for a 1D viewer.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """

    params = comon_parameters + [
        {'title': 'Card Type', 'name':'card_type', 'type':'list', 'limits': [ "M2p.5936-x4", "M2p.5933-x4" ], "value":"M2p.5933-x4" },

        {'title': 'Aquisition Mode', 'name':'DAQ_mode', 'type':'list', 'limits': [ "Single", "Multi", "FIFO" ], "value":"FIFO" },

        {'title': 'Channels:', 'name': 'channels', 'type': 'group', 'children':[
            {'title': 'CH0', 'name': 'c0', 'type': 'led_push', 'value': False, 'default': False},
            {'title': 'CH1', 'name': 'c1', 'type': 'led_push', 'value': False, 'default': False},
            {'title': 'CH2', 'name': 'c2', 'type': 'led_push', 'value': True, 'default': True},
            {'title': 'CH3', 'name': 'c3', 'type': 'led_push', 'value': False, 'default': False},
            {'title': 'CH4', 'name': 'c4', 'type': 'led_push', 'value': True, 'default': True},
            {'title': 'CH5', 'name': 'c5', 'type': 'led_push', 'value': False, 'default': False},
            {'title': 'CH6', 'name': 'c6', 'type': 'led_push', 'value': False, 'default': False},
            {'title': 'CH7', 'name': 'c7', 'type': 'led_push', 'value': False, 'default': False},
            {'title': 'Amplitude:', 'name': 'Amp', 'type': 'float', 'value': 5000, 'default': 5000, 'suffix':'mV'},
            {'title': 'Offset:','name': 'Offset','type': 'float','value': 0, 'default': 0, 'suffix':'mV'},
            ], 'expanded': False},

        {'title': 'Acquisition Parameters', 'name': 'timing', 'type': 'group', 'children': [
            {'title': 'Nbr. of laser pulses:', 'name': 'Num_Pulses', 'type': 'int', 'value': 200, 'default': 200, 'children':[
                {'title': 'Laser pulses freq. :', 'name': 'PulseFreq', 'type': 'int', 'value': 1, 'default': 1, 'readonly' : True, 'suffix':'kHz [Read Only]'},
            ], 'expanded': False},
            {'title': 'Nbr. of samples per laser pulse:', 'name': 'Sample_per_Pulse', 'type': 'int', 'value': 200, 'default': 200},
            {'title': 'Sample rate :', 'name': 'sampleRate', 'type': 'float', 'value': 0.2, 'default': 0.2, 'readonly' : True, 'suffix':'MHz [Read Only]'},
            {'title': 'Time range :', 'name': 'Range', 'type': 'float', 'value': 200, 'default': 200, 'readonly': True, 'suffix':'ms [Read Only]'},
            {'title': 'Number of samples :', 'name': 'NumSamples', 'type': 'int', 'value': 40000, 'default': 40000, 'readonly' : True, 'suffix':'S [Read Only]'},
            ]},

        {'title': 'Trigger parameters', 'name': 'trig_params', 'type': 'group', 'children':[
            {'title': 'Trigger:', 'name': 'triggerType', 'type':'list', 'limits': [ "None", "Channel trigger", "Software trigger", "External analog trigger" ], "value":"External analog trigger" },
            {'title': 'Trigger channel:', 'name': 'triggerChannel', 'type':'list', 'limits': ["CH0", "CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"], "value":"CH0", "visible":False },
            {'title': 'Trigger mode', 'name': 'triggerMode', 'type':'list', 'limits': [ "Rising edge", "Falling edge", "Both"], "value":"Rising edge", "visible":True },
            {'title': 'Trigger level:', 'name': 'triggerLevel', 'type': 'slide', 'value': 100, 'default': 100, 'min': -500, 'max': 500, 'subtype': 'linear', 'suffix':'mV', "visible":True},
            {'title': 'Pre-Trig:', 'name': 'preTrig', 'type': 'slide', 'value': 80, 'default': 80, 'min': 0, 'max': 100, 'subtype': 'linear', 'suffix':'%', "visible":True},
            ]},

        {'title': 'External reference clock parameters', 'name': 'clock_param', 'type': 'group', 'children': [
            {'title': 'Clock mode:', 'name': 'clockMode', 'type':'list', 'limits': ["internal PLL", "external", "external reference"], "value":"external reference" },
            # {'title': 'Clock mode:', 'name': 'clockMode', 'type':'list', 'limits': ["internal PLL", "external", "external reference"], "value":"internal PLL" },
            {'title': 'External ref. clock rate:', 'name': 'ExtClock', 'type': 'float', 'value': 80.01, 'default': 80.01, 'suffix':'MHz'},
            {'title': 'Clock threshold', 'name': 'clock_th', 'type': 'float', 'value': 1.5, 'default': 1.5, 'suffix':'V'},
            ], 'expanded': False},
        {'title': 'High freq cutoff', 'name': 'cutoffFreq', 'type': 'slide', 'value': 0, 'suffix': 'kHz', 'visible':True, 'min':0, 'max':1000},

    ]


    def ini_attributes(self):
        """ 
        Called at initialisation of the Daq View
        """

        # --- Choose Wrapper Type based on aquisition mode
        self.wrapper = None
        match self.settings.child("DAQ_mode").value():
            case "Single": 
                self.wrapper = Spectrum_Wrapper_Single
                self.controller : Spectrum_Wrapper_Single = None
            case "Multi":
                self.wrapper = Spectrum_Wrapper_Multi
                self.controller : Spectrum_Wrapper_Multi = None
            case "FIFO":
                self.wrapper = Spectrum_Wrapper_FIFO
                self.controller : Spectrum_Wrapper_FIFO = None
            case _: print("Error, Wrapper Type Not Defined")

        # --- Update parameters based on the card type
        self.update_card_type_parameters()

        # --- Init all readonly values
        self.update_readonly_parameters()

        self.x_axis = None
        self.card = None
        self.manager = None
        self.hit_except = None
        self.trigger = None
        self.clock = None

        # self.fps_counter = 0
        # self.fps_clock=time.time()


    def commit_settings(self, param: Parameter):
        """
        Called when param of ParameterTree is changed
        """

        if param.name() == "channels":
            channel = param.value()
            channel_nbr = int(channel[1])
            self.controller.setChannel(channel_nbr, self.settings.child('Amp').value(), self.settings.child('Offset').value())
        

        elif param.name() == "Num_Pulses" or param.name() == "Sample_per_Pulse":
            self.update_readonly_parameters()


        elif param.name() == "triggerType":
            self.update_trigger_parameter_visibility()
            if param.value()=="Channel trigger": self.settings.child("trig_params", "triggerChannel").show()
            else : self.settings.child("trig_params", "triggerChannel").hide()


    def ini_detector(self, controller=None):
        """
        Detector communication initialization
        """

        if self.is_master:
            # --- Connect to the card
            self.controller = self.wrapper(duration=   self.settings.child("timing", "Range").value(), 
                                                      sample_rate=   self.settings.child("timing", "sampleRate").value())

            # --- Check if the Card corresponds to demanded Card type
            actual_card_type = self.controller.get_device_info()["Product Name"]
            if actual_card_type == self.settings.child("card_type").value():
                # Initiallise with all card parameters
                initialized = self.controller.initialise_device(clock_mode=             self.settings.child("clock_param", "clockMode").value(),
                                                                clock_frequency=        self.settings.child("clock_param", "ExtClock").value(),
                                                                channels_to_activate=   [ self.settings.child("channels", f"c{ii}").value() for ii in range(8)],
                                                                channel_amplitude=      self.settings.child("channels", "Amp").value(),
                                                                channel_offset=         self.settings.child("channels", "Offset").value(),
                                                                trigger_settings=       {"trigger_type":    self.settings.child("trig_params", "triggerType").value(),
                                                                                        "trigger_channel": self.settings.child("trig_params", "triggerChannel").value(),
                                                                                        "trigger_mode":    self.settings.child("trig_params", "triggerMode").value(),
                                                                                        "trigger_level":   self.settings.child("trig_params", "triggerLevel").value()}
                                                                )

                info = f"Initialized card {actual_card_type}"
                initialized = True
            #  --- If not, check if valid card type, update parameters
            else:   
                print(type(self.settings.child("card_type")))
                if actual_card_type not in self.settings.child("card_type").opts['limits'] :
                    info = "Card type is not implemented ! "

                    print(info)
                    self.emit_status(ThreadCommand('Update_Status', [info]))
                else:
                    self.settings.child("card_type").setValue( actual_card_type ) 
                    self.update_card_type_parameters()
                    self.controller.terminate_the_communication(self.manager, self.hit_except)
                    info = f'Card Type Changed to {actual_card_type}'
                    
                    print(info)
                    self.emit_status(ThreadCommand('Update_Status', [info]))

                initialized = False

        else:
            self.controller = controller
            initialized = True


        return info, initialized


    def close(self):
        """Terminate the communication protocol"""
        self.controller.terminate_the_communication(self.manager, self.hit_except) 


    def grab_data(self, Naverage=1, **kwargs):
        """ Start a grab from the detector
        """

        # --- Grab a Trace
        post_trig =  (1-self.settings.child("trig_params", "preTrig").value()/100) * self.settings.child("timing", "Range").value() / self.settings.child("timing", "Num_Pulses").value()
        try:  data_tot = self.controller.grab_trace( post_trig_ms = post_trig )     
        except Exception as e:
            print("Capture Failed !")
            print(e)
            self.emit_status(ThreadCommand('Update_Status', ['Error in card Aquisition ']))
            self.hit_except = True

        # Apply Filter
        for i in range( len(data_tot) ):
            data_tot[i] = self.apply_lowpass_filter(data_tot[i])

        self.x_axis = Axis(data=self.controller.get_the_x_axis(), label='Time', units="s", index=0)

        dwa = DataFromPlugins(name='Pulse train', data=data_tot, dim='Data1D', labels=['D', 'I'], do_plot=True, do_save=True, axes=[self.x_axis])

        data_to_export = [dwa]

        data = DataToExport('Spectrum', data=data_to_export)
        self.dte_signal.emit(data)

        # self.fps_counter += 1
        # if self.fps_counter > 30:
        #     time_elapsed = time.time() - self.fps_clock; 
        #     fps = self.fps_counter / time_elapsed; print("FPS : ", fps)
        #     self.fps_clock = time.time(); self.fps_counter = 0

    def update_readonly_parameters(self):
        self.settings.child('timing', 'sampleRate').setValue(       self.settings.child("timing", "Sample_per_Pulse").value() / (1/ (self.settings.child("timing", "Num_Pulses", "PulseFreq").value() * 1e3) ) * 1e-6      )  # Points per Pulse / PulsePeriod, in MHz
        self.settings.child('timing', 'NumSamples').setValue(       self.settings.child("timing", "Num_Pulses").value() * self.settings.child("timing", "Sample_per_Pulse").value()                          )    # Num of Pulses * Samples per Pulse
        self.settings.child('timing', 'Range').setValue(        self.settings.child('timing', 'NumSamples').value() / (self.settings.child('timing', 'sampleRate').value()*1e6) * 1e3     )  # NumPulse / sampleRate[MHz], in ms



    def update_card_type_parameters(self):
        match self.settings.child("card_type").value():
            case "M2p.5936-x4": # Only has 4 channels
                for chan_setting in self.settings.child("channels").children():
                    if chan_setting.title() in ["CH4", "CH5", "CH6", "CH7"] : chan_setting.hide(); chan_setting.setValue(False)

            case "M2p.5933-x4":
                for chan_setting in self.settings.child("channels").children():
                    if chan_setting.title() in ["CH4", "CH5", "CH6", "CH7"] : chan_setting.show()

            case _: print("ERROR, Card type not recognised")  



    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        return ''


    def update_trigger_parameter_visibility(self):
        trigger_type = self.settings.child("trig_params", "triggerType").value()
        visibility = {
            'None'                      :   {'triggerChannel':False, 'triggerMode':False, 'triggerLevel':False, 'preTrig':False},
            "Channel trigger"           :   {'triggerChannel':True , 'triggerMode':True , 'triggerLevel':True , 'preTrig':True },
            "Software trigger"          :   {'triggerChannel':False, 'triggerMode':True , 'triggerLevel':True , 'preTrig':True },
            "External analog trigger"   :   {'triggerChannel':False, 'triggerMode':True , 'triggerLevel':True , 'preTrig':True },
        }

        for param in visibility['None'].keys():
            self.settings.child("trig_params", param).show(visibility[trigger_type][param])

    def apply_lowpass_filter(self, trace):
            cutoff = self.settings.child('cutoffFreq').value() * 1e3 # kHz to Hz
            if cutoff is None or cutoff <= 0:
                return trace

            fs = self.settings.child('timing', 'sampleRate').value() * 1e6  # MHz -> Hz
            nyquist = fs / 2

            if cutoff >= nyquist:
                # cutoff at/above Nyquist would have no effect (or error out) -- skip filtering
                print("Nyquist")
                return trace

            b, a = signal.butter(N=4, Wn=cutoff / nyquist, btype='low')
            return signal.filtfilt(b, a, trace)






if __name__ == "__main__":
    main(__file__)


