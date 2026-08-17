import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
import os
import sys


from pymodaq_plugins_spectrum_instrumentation.daq_viewer_plugins.plugins_1D.daq_1Dviewer_Spectrum import DAQ_1DViewer_Spectrum
from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_Single import Spectrum_Wrapper_Single


class DAQ_1DViewer_Spectrum_Lockin(DAQ_1DViewer_Spectrum):
    """ Instrument plugin class for a 1D viewer.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

        """

    params = DAQ_1DViewer_Spectrum.params + [

        {'title': 'Lock-in', 'name': 'lock_in', 'type': 'group', 'children': [
            {'title': 'Difference channel', 'name': 'diffChannel', 'type':'list', 'limits': ["CH0", "CH1", "CH2", "CH3", "CH4"], "value":"CH2" },
            {'title': 'Intensity channel:', 'name': 'sumChannel',  'type':'list', 'limits': ["CH0", "CH1", "CH2", "CH3", "CH4"], "value":"CH4" },
            {'title': 'Lock In freq.:', 'name': 'LI_PulseFreq', 'type': 'int', 'value': 500, 'default': 500, 'suffix':'Hz'},
            {'title': 'Subtract background', 'name': 'BG_sub', 'type': 'bool', 'value': True, 'default': True},
            {'title': 'Background Proportion', 'name': 'BG_prop', 'type': 'slide', 'value': 70, 'default': 70, 'min': 0, 'max': 100, 'subtype': 'linear', 'suffix':'%'},
            {'title': 'PD gain :', 'name': 'Gain', 'type': 'float', 'value': 10, 'default': 10, 'readonly': True, 'suffix':' [Read Only]'},
            {'title': 'Conversion factor :', 'name': 'Conversion', 'type': 'float', 'value': 2, 'default': 2, 'readonly': True, 'suffix':' [Read Only]'},

            {'title': 'Plotting & Saving', 'name': 'PlotSave', 'type': 'group', 'children': [
                {'title': 'Raw trace', 'name': 'Trace', 'type': 'led_push', 'value': True, 'default': True, 'children':[
                    {'title': 'Show LockIn Signal', 'name': 'show_LI', 'type': 'led_push', 'value': False, 'default': False},
                ]},
                {'title': 'Pulse train', 'name': 'PulseTrain', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'Pulse average', 'name': 'PulseAverage', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'I_Bd', 'name': 'I_Bd', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'I_Ba', 'name': 'I_Ba', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'D_Bd', 'name': 'D_Bd', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'D_Ba', 'name': 'D_Ba', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'ND_Bd', 'name': 'ND_Bd', 'type': 'led_push', 'value': True, 'default': True},
                {'title': 'ND_Ba', 'name': 'ND_Ba', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'phi_Bd', 'name': 'phi_Bd', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'phi_Ba', 'name': 'phi_Ba', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'phi_Pd', 'name': 'phi_Pd', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'phi_Pa', 'name': 'phi_Pa', 'type': 'led_push', 'value': False, 'default': False},
                {'title': 'Show & save STD', 'name': 'STD', 'type': 'bool', 'value': False, 'default': False}
                ], 'expanded': False}]
        },
    ]


    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

        # --- Calculate some Lock In Parameters
        self.update_lockin_param()

        chan_str = [param.title() for param in self.settings.child("channels").children() if param.type()=="led_push" and param.value()]
        self.settings.child('lock_in', 'diffChannel').setLimits( chan_str )
        self.settings.child('lock_in', 'sumChannel').setLimits( chan_str )


    def commit_settings(self, param):
        super().commit_settings(param)

        if param.name()=="BG_sub":
            if param.value(): self.settings.child("lock_in", "BG_prop").show()
            else: self.settings.child("lock_in", "BG_prop").hide()

        if param.name() in ["LI_PulseFreq", 'Range', "sampleRate"]:     # TODO : is this called if range / sample rate is changed by another commit_setting (ie points_per_pulse)
            self.update_lockin_param()
    

    def grab_data(self, Naverage=1, **kwargs):
        """ Start a grab from the detector
        """

        # --- Grab a Trace
        post_trig =  (1-self.settings.child("trig_params", "preTrig").value()/100) * self.settings.child("timing", "Range").value() / self.settings.child("timing", "Num_Pulses").value()
        try:  data_tot = self.controller.grab_trace( post_trig_ms = post_trig )
        except Exception as e:
            print("Capture Failed !")
            print(e)
            self.emit_status(ThreadCommand('Update_Status', ['Card asked while running ']))
            self.hit_except = True


        # --- Seperate sum and diff
        ii = self.controller.activated_str.index( self.settings.child('lock_in', 'diffChannel').value() )
        index = len(self.controller.activated_str[:ii])
        diff_data = data_tot[index]

        ii = self.controller.activated_str.index( self.settings.child('lock_in', 'sumChannel').value() )
        index = len(self.controller.activated_str[:ii])
        sum_data = data_tot[index]

        # --- Lock In Process
        try: sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd, phi_a, phi_Ba, phi_Bd = self.lock_in(diff_data, sum_data)
        except Exception as e:
            print(" - Problem during lockin Process")
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

            self.emit_status(ThreadCommand('Update_Status', [ 'Problem During the LockIn Process ! ! ']))
            self.hit_except = True

            I_Ba, I_Bd, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd, phi_a, phi_Ba, phi_Bd = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            

        # --- Create Pymodaq export
        self.x_axis = Axis(data=self.controller.get_the_x_axis(), label='Time', units="s", index=0)
        data_to_export = []


        # Integrated Trace, only one to always export
        dwa_int = DataFromPlugins(name='Pulse train', data=[diff_data_int, sum_data_int], dim='Data1D', labels=['D', 'I'], do_plot=self.settings.child('lock_in', 'PlotSave', 'PulseTrain').value(), do_save=True)
        data_to_export.append(dwa_int)

        # Also deal with Trace separately as it is 1D
        if self.settings.child('lock_in', 'PlotSave', 'Trace').value():
            if self.settings.child('lock_in', 'PlotSave','Trace','show_LI').value():
                # --- Add visualisation
                step = self.x_axis.get_data() < self.lockin_step_duration*self.num_lockin_steps
                data_trace = np.sign( np.sin( 2*np.pi*self.settings.child('lock_in', 'LI_PulseFreq').value() * self.x_axis.get_data()) ) * np.max( np.abs(data_tot) ) * step
                dwa_trace = DataFromPlugins(name='Trace', data=data_tot + [data_trace], dim='Data1D', labels=self.controller.activated_str+ ["Lock In Trace"], axes=[self.x_axis])
                data_to_export.append(dwa_trace)
            else:
                dwa_trace = DataFromPlugins(name='Trace', data=data_tot, dim='Data1D', labels=self.controller.activated_str, axes=[self.x_axis])
                data_to_export.append(dwa_trace)


        # Iterate through the calculated data "I_Ba"n "I_Bd"...
        export = {'I_Bd':I_Bd, 'I_Ba':I_Ba, 'D_Bd':D_Bd, 'D_Ba':D_Ba, 'ND_Bd':ND_Bd, 'ND_Ba':ND_Ba, 'phi_Bd':phi_Bd, 'phi_Ba':phi_Ba }
        types = [ param.name() for param in self.settings.child('lock_in', 'PlotSave').children() if (param.value() and param.type()=="led_push" and param.name()!="PulseTrain" and param.name()!="Trace") ]
        for type in types:
            dwa = DataFromPlugins(name=type, data=export[type], dim='Data0D', labels=[type])
            data_to_export.append(dwa)

        data = DataToExport('SPLockIn', data=data_to_export)
        self.dte_signal.emit(data)


    def lock_in(self, diff_data, sum_data):
        """
        From 2 traces, calculate all relevant values
        """

        # --- Reshape to correct size
        diff_data_shortened = diff_data[: int(self.num_lockin_steps*self.points_per_step ) ]
        sum_data_shortened = sum_data[: int(self.num_lockin_steps*self.points_per_step) ]

        # --- Integrate Pulses and remove Background
        diff_chan_reshaped = diff_data_shortened.reshape(self.num_lockin_steps, self.points_per_step)
        sum_chan_reshaped = sum_data_shortened.reshape(self.num_lockin_steps, self.points_per_step)

        if self.settings.child('lock_in', 'BG_sub').value() == True:
            cutoff = int(self.points_per_step * self.settings.child("lock_in", "BG_prop").value()/100)
            diff_data_int = np.sum( diff_chan_reshaped[:,:cutoff], axis=1 ) * (1-self.settings.child('lock_in', 'BG_prop').value()/100) - np.sum(diff_chan_reshaped[:,cutoff:], axis=1) * self.settings.child('lock_in', 'BG_prop').value()/100
            sum_data_int = np.sum( sum_chan_reshaped[:,:cutoff], axis=1 ) * (1-self.settings.child('lock_in', 'BG_prop').value()/100) - np.sum(sum_chan_reshaped[:,cutoff:], axis=1) * self.settings.child('lock_in', 'BG_prop').value()/100
        else:
            diff_data_int = np.sum(diff_chan_reshaped, axis=1)
            sum_data_int = np.sum(sum_chan_reshaped, axis=1)

        # - Compute I_Ba and I_Bd
        I_Bd_list = sum_data_int[::2] - sum_data_int[1::2]
        I_Bd = np.mean(I_Bd_list)
        I_Ba = np.mean(sum_data_int)

        # - Compute D_Ba and D_Bd
        D_Bd_list =   diff_data_int [::2] - diff_data_int [1::2]
        D_Bd = np.mean(D_Bd_list)
        D_Ba = np.mean(diff_data_int)


        # - Compute ND_Ba and ND_Bd
        ND_int = np.divide(diff_data_int, sum_data_int) / self.settings.child('lock_in', 'Gain').value() / 2
        ND_a = np.mean(ND_int)

        ND_Bd_list = ND_int[::2] - ND_int[1::2]
        ND_Bd = np.mean(ND_Bd_list)
        ND_Ba = np.mean(ND_int)

        # - Computing phi_Ba and phi_Bd
        phi_a = ND_a / self.settings.child('lock_in', 'Conversion').value()
        phi_Ba = ND_Ba / self.settings.child('lock_in', 'Conversion').value()
        phi_Bd = ND_Bd / self.settings.child('lock_in', 'Conversion').value()

        return sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd, phi_a, phi_Ba, phi_Bd


    def update_lockin_param(self):
        self.lockin_step_duration = (1/self.settings.child("lock_in", "LI_PulseFreq").value()) / 2                      # Divide by 2 since one step is defined as only up or down
        self.num_lockin_steps = int(self.settings.child("timing", 'Range').value()*1e-3 / self.lockin_step_duration  /2)*2         #
        self.points_per_step = int( self.lockin_step_duration * round(self.settings.child("timing", "sampleRate").value() * 1e6) )

        print("\n--- Lock In Info")
        print("Lockin Step Duration = ", self.lockin_step_duration*1e3, "ms")
        print("Number of Lockin Steps = ", self.num_lockin_steps)
        print("Points Per Step = ", self.points_per_step)




if __name__ == "__main__":
    main(__file__)
