import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter



#import spcm
#from spcm import units # spcm uses the pint library for unit handling (units is a UnitRegistry object)
import PyQt5.QtCore as Qtc
import PyQt5.QtWidgets as Qtw
import sys
import spcm
from spcm import units
#from pymodaq_plugins_template2.hardware.SpectrumCard_wrapper import Digitizer_Wrapper
from ...hardware.SpectrumCard_wrapper import Digitizer_Wrapper

#class PythonWrapperOfYourInstrument:
    #  TODO Replace this fake class with the import of the real python wrapper of your instrument
#   pass



# TODO:
# (1) change the name of the following class to DAQ_1DViewer_TheNameOfYourChoice
# (2) change the name of this file to daq_1Dviewer_TheNameOfYourChoice ("TheNameOfYourChoice" should be the SAME
#     for the class name and the file name.)
# (3) this file should then be put into the right folder, namely IN THE FOLDER OF THE PLUGIN YOU ARE DEVELOPING:
#     pymodaq_plugins_my_plugin/daq_viewer_plugins/plugins_1D
class DAQ_1DViewer_SpectrumCard(DAQ_Viewer_base):
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
                 "1 channel", "2 channels", "4 channels", "8 channels"], selected=["1 channel"])},
            
            {'title': 'Clock mode:',
             'name': 'clockMode',
             'type': 'itemselect',
             'value': dict(all_items=[
                 "internal PLL", "external", "external reference" ], selected=["internal PLL"])},
            
            {'title': 'Trigger:',
             'name': 'triggerType',
             'type': 'itemselect',
             'value': dict(all_items=[
                 "None", "Software trigger", "External analog trigger"], selected=["None"])},
            
            {'title': 'Trigger mode',
             'name': 'triggerMode',
             'type': 'itemselect',
             'value': dict(all_items=[
                 "Rising edge", "Falling edge", "Both"], selected=["Rising edge"])},
            
            {'title': 'Trigger level (mV):',
             'name': 'trigLevel',
             'type': 'float',
             'value': 0, 'default': 0},
            
            {'title': 'Sample rate (MHz):',
             'name': 'sampleRate',
             'type': 'float',
             'value': 30, 'default': 30},
            
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
             'value': 10, 'default': 10},
            
            {'title': 'Post trigger duration (µs):',
             'name': 'postTrigDur',
             'type': 'float',
             'value': 0, 'default': 0},
            
            
        ]


    def ini_attributes(self):
        #  TODO declare the type of the wrapper (and assign it to self.controller) you're going to use for easy
        #  autocompletion
        
        self.controller : Digitizer_Wrapper = None
        #self.controller = Digitizer_Wrapper()
        # TODO declare here attributes you want/need to init with a default value

        self.x_axis = None
        
        self.card = None
        
        self.manager = None
        
        self.hit_except = None
        
        self.trigger = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        ## TODO for your custom plugin
        if param.name() == "channels":
            channel = param.value()
            
            channel_nbr = int(channel[1])
      
            self.controller.setChannel(channel_nbr, self.settings.child('Amp').value(), self.settings.child('Offset').value())
            
        if param.name() == "sampleRate":
            clock = spcm.Clock(self.card)
            clock.mode(spcm.SPC_CM_INTPLL)            # clock mode internal PLL
            clock.sample_rate(self.settings.child('sampleRate').value() * units.MHz, return_unit=units.MHz)
            
        if param.name() == "Offset":
            self.channels[0].offset(self.settings.child('Offset').value() * units.mV, return_unit=units.mV)
            
        if param.name() == "Amp":
            self.channels.amp(self.settings.child('Amp').value() * units.mV)

        if param.name() == "trigLevel":
            self.trigger.ch_level0(self.channels[0], param.value() * units.mV, return_unit=units.mV)         
        
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
       
        
        self.manager = (spcm.Card('/dev/spcm0'))
        enter = type(self.manager).__enter__
        exit = type(self.manager).__exit__
        value = enter(self.manager)
        self.hit_except = False

        try:
            self.card = value 
        except:
            hit_except = True
            if not exit(self.manager, *sys.exc_info()):
                raise    
                
                
                
        ###### try standard setup
        
        try:
                 
                
        
        #card : spcm.Card
        #with spcm.Card('/dev/spcm0') as card:                       # if you want to open a specific card
        # with spcm.Card('TCPIP::192.168.1.10::inst0::INSTR') as card:  # if you want to open a remote card
        # with spcm.Card(serial_number=12345) as card:                  # if you want to open a card by its serial number
        #card = spcm.Card(card_type=spcm.SPCM_TYPE_AI)         # if you want to open the first card of a specific type
            
            # do a simple standard setup
            self.card.card_mode(spcm.SPC_REC_STD_SINGLE)     # single trigger standard mode
            self.card.timeout(5 * units.s)                     # timeout 5 s
            
            self.trigger = spcm.Trigger(self.card)
            
            if self.settings.child('triggerType').value()['selected'] == ['None']:
                self.trigger.or_mask(spcm.SPC_TMASK_NONE)       # trigger set to none 
            if self.settings.child('triggerType').value()['selected'] == ['Software trigger']:
                print('bla')
                self.trigger.or_mask(spcm.SPC_TMASK_SOFTWARE)       # trigger set to software          
            if self.settings.child('triggerType').value()['selected'] == ['External analog trigger']:
                self.trigger.or_mask(spcm.SPC_TMASK_EXT0)       # trigger set to external analog                    
            
            
            
            self.trigger.and_mask(spcm.SPC_TMASK_NONE)      # no AND mask
            
            clock = spcm.Clock(self.card)
            clock.mode(spcm.SPC_CM_INTPLL)            # clock mode internal PLL
            clock.sample_rate(self.settings.child('sampleRate').value() * units.MHz, return_unit=units.MHz)
            
            # setup the channels
 
            if self.settings.child('channels').value()['selected'] == ['1 channel']:
                self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL0)
            if self.settings.child('channels').value()['selected'] == ['2 channels']:
                self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL0 | spcm.CHANNEL1)
            if self.settings.child('channels').value()['selected'] == ['4 channels']:
                self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL0 | spcm.CHANNEL1 | spcm.CHANNEL2 | spcm.CHANNEL3)
            if self.settings.child('channels').value()['selected'] == ['8 channels']:
                self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL0 | spcm.CHANNEL1 | spcm.CHANNEL2 | spcm.CHANNEL3 | spcm.CHANNEL4 | spcm.CHANNEL5 | spcm.CHANNEL6 | spcm.CHANNEL7)
            
            #self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL0 | spcm.CHANNEL1| spcm.CHANNEL2| spcm.CHANNEL3)#|spcm.CHANNEL1) # enable channel 0
            self.channels.amp(self.settings.child('Amp').value() * units.mV)
            self.channels[0].offset(self.settings.child('Offset').value() * units.mV, return_unit=units.mV)
            


            self.channels.termination(1)
            
            #channels.coupling(spcm.COUPLING_DC)
            
            # Channel triggering
            self.trigger.ch_or_mask0(self.channels[0].ch_mask())
            
            
            if self.settings.child('triggerMode').value()['selected'] == ['Rising edge']:
                self.trigger.ch_mode(self.channels[0], spcm.SPC_TM_POS)
            if self.settings.child('triggerMode').value()['selected'] == ['Falling edge']:
                self.trigger.ch_mode(self.channels[0], spcm.SPC_TM_NEG)                
            if self.settings.child('triggerMode').value()['selected'] == ['Both']:
                self.trigger.ch_mode(self.channels[0], spcm.SPC_TM_BOTH)            
                
                
                
            self.trigger.ch_level0(self.channels[0], self.settings.child('trigLevel').value() * units.mV, return_unit=units.mV)
            

            
            # define the data buffer
            #data_transfer = spcm.DataTransfer(self.card)
            #data_transfer.duration(self.settings.child('Range').value()*units.us, post_trigger_duration=self.settings.child('postTrigDur').value()*units.us)
            #self.card.start(spcm.M2CMD_CARD_ENABLETRIGGER, spcm.M2CMD_DATA_WAITDMA)
        
        except:
            self.hit_except = True
            if not exit(self.manager, *sys.exc_info()):
                raise


        #self.emit_status(ThreadCommand('show_splash', 'Starting initialization ...'))
        #Qtc.QThread.msleep(500)
        self.ini_detector_init(old_controller=controller,
                             new_controller=Digitizer_Wrapper())
        self.emit_status(ThreadCommand('show_splash', 'Connecting to card ...'))
        Qtc.QThread.msleep(500)

        self.emit_status(ThreadCommand('show_splash', 'Enjoy taking data :)'))
        Qtc.QThread.msleep(1000)
        #QtCore.QThread.msleep(500)
        # initialize viewers with the future type of data
        self.dte_signal_temp.emit(DataToExport('Card', data=[DataFromPlugins(name='Trace1', data=[np.zeros((100))],
                                                                             dim='Data1D',
                                                                             labels=[])]))
        self.emit_status(ThreadCommand('close_splash'))
                

        info = "Initialized"
        initialized = True
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        ## TODO for your custom plugin
        #raise NotImplemented  # when writing your own plugin remove this line
        self.controller.terminate_the_communication(self.manager, self.hit_except)  # when writing your own plugin replace this line
        
        
    def grab_data(self, Naverage=1, **kwargs):
        #self.emit_status(ThreadCommand('show_splash', 'Bla ...'))
        #Qtc.QThread.msleep(1000)
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
        
        postTrigDur = self.settings.child('postTrigDur').value()
        
        data_tot = self.controller.start_a_grab_snap(self.card, self.channels, Range, postTrigDur)
        #self.emit_status(ThreadCommand('show_splash', 'Bla 2 ...'))
        
        data_x = self.controller.get_the_x_axis()
        
        
        self.x_axis = Axis('Time', units='µs', data=data_x, index=0)
        self.dte_signal.emit(DataToExport('SpectrumCard',
                                          data=[DataFromPlugins(name='trace', data=data_tot,
                                                                dim='Data1D', labels=[], axes=[self.x_axis]
                                                                )]))
        

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
        #raise NotImplemented  # when writing your own plugin remove this line
        self.controller.your_method_to_stop_acquisition()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################
        return ''





