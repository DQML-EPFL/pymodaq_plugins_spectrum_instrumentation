import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from Spectrum_Instrumentation_Digitizer_Wrapper_better import Digitizer_Wrapper


import spcm
from spcm import units # spcm uses the pint library for unit handling (units is a UnitRegistry object)
import sys


#class PythonWrapperOfYourInstrument:
    #  TODO Replace this fake class with the import of the real python wrapper of your instrument
    #pass

# TODO:
# (1) change the name of the following class to DAQ_1DViewer_TheNameOfYourChoice
# (2) change the name of this file to daq_1Dviewer_TheNameOfYourChoice ("TheNameOfYourChoice" should be the SAME
#     for the class name and the file name.)
# (3) this file should then be put into the right folder, namely IN THE FOLDER OF THE PLUGIN YOU ARE DEVELOPING:
#     pymodaq_plugins_my_plugin/daq_viewer_plugins/plugins_1D
class DAQ_1DViewer_SIDigitizer(DAQ_Viewer_base):
    """ Instrument plugin class for a 1D viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of instruments that should be compatible with this instrument plugin.
        * With which instrument it has actually been tested.
        * The version of PyMoDAQ during the test.
        * The version of the operating system.
        * Installation instructions: what manufacturer’s drivers should be installed to make it run?

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    # TODO add your particular attributes here if any

    """
    
   
    params = comon_parameters + [

            {'title': 'Channels:',
             'name': 'channels',
             'type': 'itemselect',
             'value': dict(all_items=[
                 "C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7"], selected=["C0"])},
            
            {'title': 'Clock mode:',
             'name': 'clockMode',
             'type': 'itemselect',
             'value': dict(all_items=[
                 "internal PLL", "external", "external reference" ], selected=["internal PLL"])},
            
            {'title': 'Trigger type:',
             'name': 'triggerType',
             'type': 'itemselect',
             'value': dict(all_items=[
                 "None", "Rising edge", "Falling edge"], selected=["None"])},
            
            {'title': 'Sample rate (MHz):',
             'name': 'sampleRate',
             'type': 'float',
             'value': 20, 'default': 20},
            
            {'title': 'Amplitude (mV):',
             'name': 'Amp',
             'type': 'float',
             'value': 200, 'default': 200},
            
            {'title': 'Offset (mV):',
             'name': 'Offset',
             'type': 'float',
             'value': 0, 'default': 0},
            
            {'title': 'Time range (µs):',
             'name': 'Range',
             'type': 'float',
             'value': 200, 'default': 200},
            
            {'title': 'Post trigger duration (µs):',
             'name': 'PostTrigDur',
             'type': 'float',
             'value': 80, 'default': 80},
            
            
        ]

    def ini_attributes(self):
        #  TODO declare the type of the wrapper (and assign it to self.controller) you're going to use for easy
        #  autocompletion
        self.controller = Digitizer_Wrapper()

        # TODO declare here attributes you want/need to init with a default value

        self.x_axis = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        ## TODO for your custom plugin
        if param.name() == "channels":
            
           channel = self.settings.child('channels').value()['selected']
           
           channel_nbr = int(channel[1])
           self.controller.setChannel(self, channel_nbr, self.settings.child('Amp').value(), self.settings.child('Offset').value() )
           
        if param.name() == "clockMode":
              
            self.controller.clock = spcm.Clock(self.controller.card)
            
            if self.settings.child('clockMode').value() == 'internal PLL':
                self.controller.clock.mode(spcm.SPC_CM_INTPLL)      
                # clock mode internal PLL
        
        if param.name() == "sampleRate":  
            self.controller.clock.sample_rate(self.settings.child('sampleRate').value() * units.MHz, return_unit=units.MHz)
            
            
        if param.name() == "Amp":    
            self.controller.channels.amp(self.settings.child('Amp').value() * units.mV)
        
        
        if param.name() == "Offset": 
           self.controller.channels.offset(self.settings.child('Offset').value() * units.mV, return_unit=units.mV)
           
        if param.name() == "Range": 
           self.controller.data_transfer.duration(self.settings.child('Range').value()*units.us, post_trigger_duration=self.settings.child('PostTrigDur').value()*units.us)
           
        if param.name() == "PostTrigDur": 
           self.controller.data_transfer.duration(self.settings.child('Range').value()*units.us, post_trigger_duration=self.settings.child('PostTrigDur').value()*units.us)
#        elif ...
        ##
        
        
        

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        
        ####################################################################
        self.manager = (spcm.Card('/dev/spcm0'))
        enter = type(self.manager).__enter__
        exit = type(self.manager).__exit__
        value = enter(self.manager)
        hit_except = False

        try:
            self.controller.card = value 
        except:
            hit_except = True
            if not exit(self.manager, *sys.exc_info()):
                raise    
                

        try:
            # do a simple standard setup
            self.controller.card.card_mode(spcm.SPC_REC_STD_SINGLE)     # single trigger standard mode
            self.controller.card.timeout(5 * units.s)                     # timeout 5 s
            
            self.controller.trigger = spcm.Trigger(self.controller.card)
            self.controller.trigger.or_mask(spcm.SPC_TMASK_NONE)       # trigger set to none #software
            self.controller.trigger.and_mask(spcm.SPC_TMASK_NONE)      # no AND mask
            
            self.controller.clock = spcm.Clock(self.controller.card)
            self.controller.clock.mode(spcm.SPC_CM_INTPLL)            # clock mode internal PLL
            self.controller.clock.sample_rate(self.settings.child('sampleRate').value() * units.MHz, return_unit=units.MHz)
        
        
        
                    
                    
            channel = self.settings.child('channels').value()['selected']
           
            channel_nbr = int(channel[1])
            
            self.controller.setChannel(self, channel_nbr, self.settings.child('Amp').value(), self.settings.child('Offset').value())
        
            
            #self.channels = spcm.Channels(self.controller.card, card_enable=spcm.CHANNEL0) # enable channel 0
            #self.channels.amp(200 * units.mV)
            #self.channels[0].offset(0 * units.mV, return_unit=units.mV)
            #self.channels.termination(1)                
                    
                
        except:
            hit_except = True
            if not exit(self.manager, *sys.exc_info()):
                raise                
                
                
                
        ####################################################################        
                

        #raise NotImplemented  # TODO when writing your own plugin remove this line and modify the one below
        self.ini_detector_init(old_controller=controller,
                               new_controller=Digitizer_Wrapper())  #M: here I will put the wrapper class I just wrote

        ## TODO for your custom plugin
        # get the x_axis (you may want to to this also in the commit settings if x_axis may have changed
        data_x_axis = self.controller.get_the_x_axis()  # if possible
        self.x_axis = Axis(data=data_x_axis, label='', units='', index=0)

        # TODO for your custom plugin. Initialize viewers pannel with the future type of data
        self.dte_signal_temp.emit(DataToExport(name='SI_plugin',
                                               data=[DataFromPlugins(name='SI_DAQ',
                                                                     data=[np.array([0., 0., ...])],
                                                                     dim='Data1D', labels=['SI_DAQ'],
                                                                     axes=[self.x_axis])]))

        info = "Whatever info you want to log"
        initialized = True
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        ## TODO for your custom plugin
        #raise NotImplemented  # when writing your own plugin remove this line
        #self.controller.terminate_the_communication()  # when writing your own plugin replace this line
        try:
            print('Communication terminated')

        except:
            hit_except = True
            if not exit(self.manager, *sys.exc_info()):
                raise
        finally:
            if not hit_except:
                exit(self.manager, None, None, None)

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        ## TODO for your custom plugin: you should choose EITHER the synchrone or the asynchrone version following

        ##synchrone version (blocking function)
        Range = self.settings.child('Range').value()
        postTrigDur = self.settings.child('PostTrigDur').value()
        
        data_tot = self.controller.start_a_grab_snap(Range, postTrigDur)
        self.dte_signal.emit(DataToExport('data',
                                          data=[DataFromPlugins(name='SI_DAQ', data=data_tot,
                                                                dim='Data1D', labels=['data'],
                                                                axes=[self.x_axis])]))

        ##asynchrone version (non-blocking function with callback)
        #self.controller.your_method_to_start_a_grab_snap(self.callback)
        #########################################################


    def callback(self):
        """optional asynchrone method called when the detector has finished its acquisition of data"""
        data_tot = self.controller.your_method_to_get_data_from_buffer()
        self.dte_signal.emit(DataToExport('myplugin',
                                          data=[DataFromPlugins(name='Mock1', data=data_tot,
                                                                dim='Data1D', labels=['dat0', 'data1'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        ## TODO for your custom plugin
        raise NotImplementedError  # when writing your own plugin remove this line
        self.controller.your_method_to_stop_acquisition()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################
        return ''


if __name__ == '__main__':
    main(__file__)
