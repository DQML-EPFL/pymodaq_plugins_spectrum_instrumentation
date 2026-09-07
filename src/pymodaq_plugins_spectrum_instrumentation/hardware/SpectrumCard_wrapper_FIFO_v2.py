# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 11:46:01 2024

@author: dqml-lab
"""


# TODO: 

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
        self.duration = round(duration,5)
        self.sample_rate = round(sample_rate,5)
        self.activated_str = []
        self.data_transfer=None

        try:
            manager = spcm.Card('/dev/spcm0')
            enter = type(manager).__enter__
            exit = type(manager).__exit__
            value = enter(manager)
            hit_except = False
            self.card = value
            # self.card = spcm.Card(card_type=spcm.SPCM_TYPE_AI)
        except:
            print(" -- ERROR IN OPENING CARD : ")
 
    # TODO: (card_type=spcm.SPCM_TYPE_AI)

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

        try:

            # --- Choose Mode
            self.card.card_mode(spcm.SPC_REC_FIFO_SINGLE)  # single trigger standard mode
            self.card.timeout(5 * units.s)  # timeout 50 s

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

            for ii in range( len(channels_to_activate) ):
                if channels_to_activate[ii]:
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
            match len(activated_channels):
                case 1: self.channels = spcm.Channels(self.card, card_enable=activated_channels[0])
                case 2: self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1])
                case 3: self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1] | activated_channels[2] | spcm.CHANNEL0)
                case 4: self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1] | activated_channels[2] | activated_channels[3])                
                case 5: self.channels = spcm.Channels(self.card, card_enable=activated_channels[0] | activated_channels[1] | activated_channels[2] | activated_channels[3] | activated_channels[4] | activated_channels[5])
                case _: print("INITIALIZATION ERROR : Cannot activate", len(activated_channels), "channels.")


            # Set Amplitude and Offset
            self.channels.amp(channel_amplitude * units.mV)
            for chan in self.channels:
                chan.offset(channel_offset * units.mV, return_unit=units.mV)
                chan.termination(0)

            # --- Activate Triggering Triggering
            trigger = spcm.Trigger(self.card)
            trigger.and_mask(spcm.SPC_TMASK_NONE)
            trigger.ext0_level0(1.5 * units.V)         # trigger threshold - ADJUST to match your external trigger signal
            trigger.ext0_coupling(spcm.COUPLING_DC)    # DC-coupled trigger input - change to COUPLING_AC if needed

            match trigger_settings["trigger_type"]:
                case 'None': trigger.or_mask(spcm.SPC_TMASK_SOFTWARE)
                case 'Software trigger': trigger.or_mask(spcm.SPC_TMASK_SOFTWARE)
                case 'External analog trigger': 
                    trigger.or_mask(spcm.SPC_TMASK_EXT0)
                    match trigger_settings['trigger_mode']:
                        case 'Rising edge': trigger.ext0_mode(spcm.SPC_TM_POS)  
                        case 'Falling edge': trigger.ext0_mode(spcm.SPC_TM_NEG)
                        case 'Both': trigger.ext0_mode(spcm.SPC_TM_BOTH) 
                        case _: print("INITIALIZATION ERROR : unknown triggering mode")
                case 'Channel trigger':
                    trigger.or_mask(spcm.SPC_TMASK_NONE)
                    dic = {'CH0':spcm.SPC_TMASK0_CH0, 'CH1':spcm.SPC_TMASK0_CH1, 'CH2':spcm.SPC_TMASK0_CH2, 'CH3':spcm.SPC_TMASK0_CH3, 'CH4':spcm.SPC_TMASK0_CH4, 'CH5':spcm.SPC_TMASK0_CH5, 'CH6':spcm.SPC_TMASK0_CH6, 'CH7':spcm.SPC_TMASK0_CH7 }
                    trigger.ch_or_mask0( dic[trigger_settings['trigger_channel']] )
                    # TODO: Right now only sets mode of first channel
                    trigger.ext0_level0(trigger_settings['trigger_level'] * units.mV, return_unit=units.mV)
                    match trigger_settings['trigger_mode']:
                        case 'Rising edge': trigger.ch_mode(self.channels[0], spcm.SPC_TM_POS)  
                        case 'Falling edge': trigger.ch_mode(self.channels[0], spcm.SPC_TM_NEG)
                        case 'Both': trigger.ch_mode(self.channels[0], spcm.SPC_TM_BOTH) 
                        case _: print("INITIALIZATION ERROR : unknown triggering mode")
                case _: print("ERROR : unknown trigger type")


            # --- Initialize Buffer for Data Transfer in FIFO Mode
            self.total_samples = int(round( (self.sample_rate*1e6) * (self.duration*1e-3) ) )
            self.total_samples_q = self.total_samples * units.S

            print(self.total_samples)
            print(self.total_samples_q)


            buffer_samples = 20 * units.KiS
            notify_samples = 1 * units.KiS

            self.data_transfer = spcm.DataTransfer(self.card)
            self.data_transfer.allocate_buffer(buffer_samples)
            self.data_transfer.pre_trigger(spcm.KIBI(1))
            self.data_transfer.notify_samples(notify_samples)
            self.data_transfer.start_buffer_transfer()
            self.data_transfer.verbose(False)


            initialized = True

        except Exception as e:
            import os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" -- ERROR IN INITIALIZATION : ")
            print("Error Type : ", e)
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, "in", fname, "at line", exc_tb.tb_lineno)
            print("--")

            hit_except = True
            initialized = False


        # Communicate Properties
        print("\n========== Initializing SPCM Card ========== " )
        print(" ----- Mode : FIFO")
        print("Duration = ", self.duration, "ms")
        print("Sampling Frequency = ", self.sample_rate, "MHz")
        print("Total Number of Samples = ", Num_Samples)
        print(f"Clock Frequency = {clock.reference_clock()*1e-6:.3f} MHz")
        print(  "============================================" )


        self.card.start(spcm.M2CMD_DATA_STARTDMA | spcm.M2CMD_CARD_ENABLETRIGGER)

        return initialized




    def get_the_x_axis(self): 
        return self.data_transfer.time_data(total_num_samples=self.total_samples_q).magnitude - self.data_transfer.time_data(total_num_samples=self.total_samples_q).magnitude[0]   # Add offset otherwise trigger makes trace start in the negatives


    def grab_trace(self, post_trig_ms : float = 0):

        blocks = []
        collected_samples = 0
        for data_block in self.data_transfer:
            blocks.append(data_block)
            collected_samples += data_block.shape[1]
            if collected_samples >= self.total_samples:
                break
        data_array = np.concatenate(blocks, axis=1)

        # stop the card and the DMA transfer now that we have enough data
        

        all_data = []
        for i, channel in enumerate(self.channels):
            all_data.append( np.array(channel.convert_data(data_array[i, :self.total_samples], units.V).magnitude) )

        return all_data


        # data_array = np.array([])
        # collected_samples = 0
        # # Get a block of data
        # for data_block in self.data_transfer:
        #     if data_array.size == 0:
        #         data_array = data_block
        #     else:
        #         data_array = np.append(data_array, data_block, axis=1)
        #         # print(data_block.shape[1])
        #     collected_samples = data_array.shape[1]
        #     if collected_samples >= self.total_samples: 
        #         # print("Collected ", collected_samples, " Samples, stopping")
        #         break

        
        # # stop the card and the DMA transfer now that we have enough data
        # self.card.stop(spcm.M2CMD_DATA_STOPDMA)

        
        # all_data = []
        # # print(data_array.shape)
        # for i, channel in enumerate(self.channels):
        #     all_data.append( np.array(channel.convert_data(data_array[i, :self.total_samples], units.V).magnitude ) )  # TODO : Way to do without trimming ? [i, :total_samples]

        # return all_data

        



    def terminate_the_communication(self, manager, hit_except):
        try:
            print('Communication terminated')
            self.card.stop(spcm.M2CMD_DATA_STOPDMA)
            self.card.close()

        except:
            hit_except = True
            if not exit(manager, *sys.exc_info()):
                raise


    def get_device_info(self, print_info=False):
        info = { 
                "Product Name" : self.card.product_name(),
                "Serial Number": self.card.sn()
                }
        if print_info:
            for prop in info.keys():
                print(prop, " - ", info[prop])
        return info





def main():

    controller = Spectrum_Wrapper_FIFO(duration=     5, 
                                        sample_rate=   1)

    initialized = controller.initialise_device(clock_mode=             ["internal PLL", "external", "external reference"][2],
                                                    clock_frequency=        80.01,
                                                    # channels_to_activate=   [1,1,1,1],
                                                    channels_to_activate=   [0,0,1,0,1,0,0,0],
                                                    channel_amplitude=      5000,
                                                    trigger_settings=       {"trigger_type":        [ "None", "Channel trigger", "Software trigger", "External analog trigger" ][3],
                                                                                "trigger_channel":  ["CH0", "CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"][0],
                                                                                "trigger_mode":     [ "Rising edge", "Falling edge", "Both"][0],
                                                                                "trigger_level":    100}
                                                    )

    controller.get_device_info(True)


    # # === Single Aquisition
    # import matplotlib.pyplot as plt
    # data = controller.grab_trace()
    # for i, data_ in enumerate(data):
    #     plt.plot(controller.get_the_x_axis(), data_, label=f"Channel {i}")
    # plt.xlabel("Time [s]"); plt.ylabel("Signal [a.u.]")
    # plt.legend(); plt.show()


    # ==== Save
    # file_to_save = "//sti-nas1.rcp.epfl.ch//dqml//dqml-commun//Data//PumpProbeData//2026//20260901/with_cables_not_twisted.pkl"
    # import pickle as pkl
    # with open(file_to_save, "wb") as file:
    #     pkl.dump(data, file)

    # # Live mode
    import time
    import matplotlib.pyplot as plt

    plt.ion()
    fig, ax = plt.subplots()
    fps_counter = 0
    fps_clock = time.time()

    while True:

        data = controller.grab_trace()
        y, y2 = data
        x = controller.get_the_x_axis()

        # fps_counter += 1
        # if fps_counter > 30:
        #     time_elapsed = time.time() - fps_clock; 
        #     fps = fps_counter / time_elapsed; print("FPS : ", fps)
        #     fps_clock = time.time(); fps_counter = 0

        ax.clear()
        ax.plot(x, y)
        ax.plot(x, y2)
        plt.xlabel("Time [s]"); plt.ylabel("Signal [a.u.]")
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.1)

        if not plt.fignum_exists(fig.number): break




    # # === FPS Calculator ===
    # import time
    # start = time.time()
    # counter = 0

    # while True:
    #     try:
    #         data = controller.grab_trace()
    #         print( counter)
    #         counter +=1

    #         if counter>=30:
    #             fps = counter / (time.time() - start)
    #             counter =0; start = time.time()
    #             print(fps)
    #     except KeyboardInterrupt:
    #         break




if __name__=="__main__":
    main()