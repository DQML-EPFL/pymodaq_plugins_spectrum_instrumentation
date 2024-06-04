# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 11:46:01 2024

@author: dqml-lab
"""


import spcm
from spcm import units # spcm uses the pint library for unit handling (units is a UnitRegistry object)




class Digitizer_Wrapper:
    

        
        
        
    def setChannel(self, channel_nbr, Amp, Offset, ):
        if channel_nbr == 0:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL0) # enable channel 0
        if channel_nbr == 1:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL1)             
        if channel_nbr == 2:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL2)            
        if channel_nbr == 3:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL3)           
        if channel_nbr == 4:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL4)        
        if channel_nbr == 5:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL5)             
        if channel_nbr == 6:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL6)            
        if channel_nbr == 7:
            self.channels = spcm.Channels(self.card, card_enable=spcm.CHANNEL7)           

            
        self.channels.amp(Amp * units.mV)
        self.channels[0].offset(Offset * units.mV, return_unit=units.mV)
        self.channels.termination(1)       
        
        
 
        
############## PMD mandatory methods       
        
    def get_the_x_axis(self):

        return self.data_transfer.time_data()
    
    
    def setTriggerType(self):
        # Channel triggering
        self.trigger.ch_or_mask0(self.channels[0].ch_mask())
        self.trigger.ch_mode(self.channels[0], spcm.SPC_TM_POS)
        self.trigger.ch_level0(self.channels[0], 0 * units.mV, return_unit=units.mV)        
    
    def start_a_grab_snap(self, Range, postTrigDur):
        # define the data buffer
        self.data_transfer = spcm.DataTransfer(self.card)
        self.data_transfer.duration(Range*units.us, post_trigger_duration=postTrigDur*units.us)
        # Start DMA transfer
        self.data_transfer.start_buffer_transfer(spcm.M2CMD_DATA_STARTDMA)
        
        # start card
        self.card.start(spcm.M2CMD_CARD_ENABLETRIGGER, spcm.M2CMD_DATA_WAITDMA)
        
        
        data_V = self.channels.convert_data(self.data_transfer.buffer[self.channels.index, :], units.V)
        
        return data_V
    #def get_data_from_buffer():
        
'''        
    def terminate_the_communication(self):
        try:
            print('Communication terminated')

        except:
            hit_except = True
            if not exit(manager, *sys.exc_info()):
                raise
        finally:
            if not hit_except:
                exit(manager, None, None, None)
'''   