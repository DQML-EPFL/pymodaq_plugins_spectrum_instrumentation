# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 11:46:01 2024

@author: dqml-lab
"""


import spcm
from spcm import units # spcm uses the pint library for unit handling (units is a UnitRegistry object)    
import sys



class Digitizer_Wrapper:
    


############## PMD mandatory methods       
        
    def get_the_x_axis(self):

        return self.data_transfer.time_data().magnitude
    
    
    def setTriggerType(self):
        # Channel triggering
        self.trigger.ch_or_mask0(self.channels[0].ch_mask())
        self.trigger.ch_mode(self.channels[0], spcm.SPC_TM_POS)
        self.trigger.ch_level0(self.channels[0], 0 * units.mV, return_unit=units.mV)        
    
    def start_a_grab_snap(self, card, channel, Range, postTrigDur):
        # define the data buffer
        self.data_transfer = spcm.DataTransfer(card)
        self.data_transfer.duration(Range*units.us, post_trigger_duration=postTrigDur*units.us)
        # Start DMA transfer
        self.data_transfer.start_buffer_transfer(spcm.M2CMD_DATA_STARTDMA)
        
        # start card
        card.start(spcm.M2CMD_CARD_ENABLETRIGGER, spcm.M2CMD_DATA_WAITDMA)
        
        data_V = []
        for chan in channel:
            data_V.append(chan.convert_data(self.data_transfer.buffer[chan.index, :], units.V).magnitude)
        
        return data_V 
    #def get_data_from_buffer():
        
      
    def terminate_the_communication(self, manager, hit_except):
        try:
            print('Communication terminated')

        except:
            hit_except = True
            if not exit(manager, *sys.exc_info()):
                raise
        finally:
            if not hit_except:
                
                exit(manager)
                manager.close()
  