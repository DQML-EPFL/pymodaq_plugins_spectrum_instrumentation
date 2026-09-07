# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 11:46:01 2024

@author: dqml-lab
"""

import spcm
from spcm import units  # spcm uses the pint library for unit handling (units is a UnitRegistry object)
import sys
import numpy as np

class Spectrum_Wrapper_FIFO:

    def __init__(self, duration : int, sample_rate : float):
        """
        Initialise class
        Input : 
            - Duration : int [ms]
            - sample_rate : float [MHz]
        """
        self.card = None
        self.channels = None
        self.duration = duration
        self.sample_rate = sample_rate
        self.activated_str = []
    

    def initialise_device(self, clock_mode : str = "external reference", clock_frequency : float = 80, channels_to_activate : list[bool] = [0,0,1,0,1,0,0,0], channel_amplitude : int = 5000, channel_offset : int = 0, trigger_settings : dict = {"trigger_type":"None", "trigger_channel":"CH0", "trigger_mode":"Rising edge", "trigger_level":5000}) -> bool:
        """
        Initializes the spectrum device in Single Mode
        Input :
            - clock_mode : str ["internal PLL", "external reference", "external"]
            - clock_frequency : float [MHz]
            - channels_to_activate : list[bool] list of lenght 8 of 0 and 1 depending on the channels to activate
            - channel_amplitude : int [mV]
            - channel_offset : int [mV]
            - trigger_settings : dict with : {"trigger_type", "trigger_channel", "trigger_mode", "trigger_level"}. 
                - trigger_type = 'None', 'Software trigger', 'External analog trigger'
                - trigger_channel = 'CH0', 'CH1' ...
                - trigger_mode = 'Rising Edge', 'Falling Edge', 'Both'
                - trigger_level [mV]
        """

        
        # --- Determine Some Properties
        Num_Samples = int( (self.duration*1e-3) * (self.sample_rate*1e6) )                 # Total Number of Samples
        print("\n--- Initializing SPCM Card --- Mode : Single")
        print("Duration = ", round(self.duration,5), "ms")
        print("Number of Samples = ", Num_Samples)
        print("Sampling Frequency = ", round(self.sample_rate,5), "MHz")

        manager = spcm.Card('/dev/spcm0')
        enter = type(manager).__enter__
        exit = type(manager).__exit__
        value = enter(manager)
        hit_except = False


        try:
            self.card = value

            # --- Choose Mode
            self.card.card_mode(spcm.SPC_REC_FIFO_SINGLE)  # single trigger standard mode
            self.card.timeout(50 * units.s)  # timeout 50 s

            # --- Setup External Clock
            clock = spcm.Clock(self.card)
            if clock_mode == "internal PLL":
                clock.mode(spcm.SPC_CM_INTPLL)  # clock mode internal PLL

            elif clock_mode == "external reference":
                clock.mode(spcm.SPC_CM_EXTREFCLOCK)  # external reference clock
                clock.reference_clock(clock_frequency * units.MHz)

            else : print("ERROR : Unknown Clock type")

            clock.sample_rate(self.sample_rate * units.MHz, return_unit=units.MHz)

            # - DO THIS IN DAQ VIEWER
            # # - Check if Given Parameters Work    
            # if int(Num_B_Pulse) != Num_B_Pulse : print("Duration is not an integer amount of Lock-In Pulses !"); exit()
            # if Num_B_Pulse%2 != 0 : print("Not an even amount ou Lock-In Pulses ! Will not be able to calculate Bd"); exit()

            # --- Activate Channels
            activated_channels = []

            for ii in range(8):
                if channels_to_activate[ii] == True:
                    self.activated_str.append('CH'+str(ii))
                    match ii:
                        case 0: activated_channels.append(spcm.CHANNEL0)
                        case 1: activated_channels.append(spcm.CHANNEL1)
                        case 2: activated_channels.append(spcm.CHANNEL2)
                        case 3: activated_channels.append(spcm.CHANNEL3)
                        case 4: activated_channels.append(spcm.CHANNEL4)
                        case 5: activated_channels.append(spcm.CHANNEL5)
                        case 6: activated_channels.append(spcm.CHANNEL6)
                        case 7: activated_channels.append(spcm.CHANNEL7)

            # Can only activate certain number of channels ...
            if len(activated_channels) == 1:
                self.channels = spcm.Channels(self.card, card_enable=activated_channels[0])
            elif len(activated_channels) == 2:
                self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1])
            elif len(activated_channels) == 3:
                self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1] | activated_channels[2] | spcm.CHANNEL7)
            elif len(activated_channels) == 4:
                self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1] | activated_channels[2] | activated_channels[3])
            elif len(activated_channels) == 5:
                self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1] | activated_channels[2] | activated_channels[3] | activated_channels[4] | activated_channels[5])

            # Set Amplitude and Offset
            self.channels.amp(channel_amplitude * units.mV)
            self.channels[0].offset(channel_offset * units.mV, return_unit=units.mV)
            self.channels.termination(0)     # Set termination to 500MOhm ?

            # --- Activate Triggering Channel Triggering
            trigger = spcm.Trigger(self.card)

            if trigger_settings["trigger_type"] == 'None':          # trigger set to none
                trigger.or_mask(spcm.SPC_TMASK_NONE)  
                trigger.ch_or_mask0(self.channels[0].ch_mask())
            elif trigger_settings["trigger_type"] == 'Software trigger':        # trigger set to software
                trigger.or_mask(spcm.SPC_TMASK_SOFTWARE)  
            elif trigger_settings["trigger_type"] == 'External analog trigger':     # trigger set to external analog
                trigger.or_mask(spcm.SPC_TMASK_EXT0)  
            elif trigger_settings['trigger_type'] == 'Channel trigger':  # trigger set channel
                trigger.or_mask(spcm.SPC_TMASK_NONE)
                if trigger_settings['trigger_channel'] == 'CH0':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH0)
                elif trigger_settings['trigger_channel'] == 'CH1':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH1)
                elif trigger_settings['trigger_channel'] == 'CH2':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH2)
                elif trigger_settings['trigger_channel'] == 'CH3':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH3)
                elif trigger_settings['trigger_channel'] == 'CH4':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH4)
                elif trigger_settings['trigger_channel'] == 'CH5':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH5)
                elif trigger_settings['trigger_channel'] == 'CH6':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH6)
                elif trigger_settings['trigger_channel'] == 'CH7':
                    trigger.ch_or_mask0(spcm.SPC_TMASK0_CH7)
                else: print("ERROR : unknown trigger Channel")
            else : print("ERROR : unknown trigger type")

            trigger.and_mask(spcm.SPC_TMASK_NONE)  # no AND mask

            if trigger_settings['trigger_type'] == 'Channel trigger':
                if trigger_settings['trigger_mode'] == 'Rising edge':
                    trigger.ch_mode(self.channels[0], spcm.SPC_TM_POS)
                elif trigger_settings['trigger_mode'] == 'Falling edge':
                    trigger.ch_mode(self.channels[0], spcm.SPC_TM_NEG)
                elif trigger_settings['trigger_mode'] == 'Both':
                    trigger.ch_mode(self.channels[0], spcm.SPC_TM_BOTH)
                else: print("ERROR : unknown triggering mode")

                trigger.ch_level0(self.channels[0], trigger_settings['trigger_level'] * units.mV, return_unit=units.mV)
            
            elif trigger_settings['trigger_type'] == 'External analog trigger':
                if trigger_settings['trigger_mode'] == 'Rising edge':
                    trigger.ext0_mode(spcm.SPC_TM_POS)
                elif trigger_settings['trigger_mode'] == 'Falling edge':
                    trigger.ext0_mode(spcm.SPC_TM_NEG)
                elif trigger_settings['trigger_mode'] == 'Both':
                    trigger.ext0_mode(spcm.SPC_TM_BOTH)
                else: print("ERROR : unknown triggering mode")

                trigger.ext0_level0(trigger_settings['trigger_level'] * units.mV, return_unit=units.mV)


            # define the data buffer
            num_samples = 40000 * units.KiS
            notify_samples = 128 * units.KiS
            self.data_transfer = spcm.DataTransfer(self.card)
            self.data_transfer.allocate_buffer(num_samples)
            self.data_transfer.pre_trigger(spcm.KIBI(1))
            self.data_transfer.notify_samples(notify_samples)
            self.data_transfer.start_buffer_transfer()
            self.data_transfer.verbose(True)



            initialized = True

        except Exception as e:
            hit_except = True
            print("EXIT WITH ERROR : ")
            print(e)
            initialized = False

 

        return initialized




    def get_the_x_axis(self):
        return self.data_transfer.time_data().magnitude

    def grab_trace(self, post_trig_ms : float = 0):
        self.card.start(spcm.M2CMD_DATA_STARTDMA | spcm.M2CMD_CARD_ENABLETRIGGER)

        data_array = np.array([])
        try:
            print("Press Ctrl+C to stop the recording and show the results...")
            # Get a block of data
            for data_block in self.data_transfer:
                if data_array.size == 0:
                    data_array = data_block
                else:
                    data_array = np.append(data_array, data_block, axis=1)
                
        except KeyboardInterrupt as e:
            pass



    def terminate_the_communication(self, manager, hit_except):
        try:
            print('Communication terminated')
            self.card.close()

        except:
            hit_except = True
            if not exit(manager, *sys.exc_info()):
                raise







def main():
    controller = Spectrum_Wrapper_FIFO(duration = 50,
                                         sample_rate= 0.2)
    
    init = controller.initialise_device(trigger_settings= {"trigger_type":"External analog trigger", "trigger_channel":"CH0", "trigger_mode":"Rising edge", "trigger_level":5000})
    data = controller.grab_trace()

    # import matplotlib.pyplot as plt
    # plt.plot(data)
    # plt.show()

if __name__=="__main__":
    main()