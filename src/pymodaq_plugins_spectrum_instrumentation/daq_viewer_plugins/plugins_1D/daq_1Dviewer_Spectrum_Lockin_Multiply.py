import numpy as np
from scipy import signal
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
import os
import sys


from pymodaq_plugins_spectrum_instrumentation.daq_viewer_plugins.plugins_1D.daq_1Dviewer_Spectrum import DAQ_1DViewer_Spectrum
from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_Single import Spectrum_Wrapper_Single

class DAQ_1DViewer_Spectrum_Lockin_Multiply(DAQ_1DViewer_Spectrum):
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
            {'title': 'Reference wave', 'name': 'refWave', 'type': 'list', 'limits': ['Sine', 'Square'], 'value': 'Square'},
            {'title': 'Lock In freq.:', 'name': 'LI_PulseFreq', 'type': 'int', 'value': 500, 'default': 500, 'suffix':'Hz'},
            {'title': 'Lock In Phase :', 'name': 'LI_Phase', 'type': 'slide', 'value': 0.4, 'suffix': r'pi rad', 'visible': True, 'min':0, 'max':2},

            {'title': 'Envelope', 'name': 'Env', 'type': 'group', 'expanded': False, 'children': [
                {'title': 'Type', 'name': 'EnvShape', 'type': 'list', 'limits': ['Sine', 'Linear', 'None'], 'value': 'None'},
                {'title': 'Width', 'name': 'EnvWidth', 'type': 'slide', 'value': 1, 'suffix': '%', 'visible': True, 'min': 0.01, 'max': 50},
            ]},

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
        try: I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, ND_Bd, ref_wave = self.lock_in(diff_data, sum_data)
        except Exception as e:
            print(" - Problem during lockin Process")
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

            self.emit_status(ThreadCommand('Update_Status', [ 'Problem During the LockIn Process ! ! ']))
            self.hit_except = True

            I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, ND_Bd = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            

        # --- Create Pymodaq export
        self.x_axis = Axis(data=self.controller.get_the_x_axis(), label='Time', units="s", index=0)
        data_to_export = []


        # Integrated Trace, only one to always export
        dwa_int = DataFromPlugins(name='Pulse train', data=[D_train, I_train], dim='Data1D', labels=['D', 'I'], do_plot=self.settings.child('lock_in', 'PlotSave', 'PulseTrain').value(), do_save=True)
        data_to_export.append(dwa_int)

        # Also deal with Trace separately as it is 1D
        if self.settings.child('lock_in', 'PlotSave', 'Trace').value():
            if self.settings.child('lock_in', 'PlotSave','Trace','show_LI').value():
                # --- Add visualisation

                dwa_trace = DataFromPlugins(name='Trace', data=data_tot + [ref_wave * np.max(data_tot)], dim='Data1D', labels=self.controller.activated_str+ ["Lock In Trace"], axes=[self.x_axis])
                data_to_export.append(dwa_trace)
            else:
                dwa_trace = DataFromPlugins(name='Trace', data=data_tot, dim='Data1D', labels=self.controller.activated_str, axes=[self.x_axis])
                data_to_export.append(dwa_trace)


        # Iterate through the calculated data "I_Ba"n "I_Bd"...
        export = {'I_Bd':I_Bd, 'I_Ba':I_Ba, 'D_Bd':D_Bd, 'D_Ba':D_Ba, 'ND_Bd':ND_Bd}
        types = [ param.name() for param in self.settings.child('lock_in', 'PlotSave').children() if (param.value() and param.type()=="led_push" and param.name()!="PulseTrain" and param.name()!="Trace") ]
        for type in types:
            dwa = DataFromPlugins(name=type, data=export[type], dim='Data0D', labels=[type])
            data_to_export.append(dwa)

        data = DataToExport('SPLockIn', data=data_to_export)
        self.dte_signal.emit(data)


    def lock_in(self, D, I):

        lockin_freq = self.settings.child("lock_in", "LI_PulseFreq").value()
        lockin_phase = self.settings.child("lock_in", "LI_Phase").value() * np.pi
        pd_gain = self.settings.child('lock_in', 'Gain').value()

        I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd, ref_wave = self.multiply_with_ref_wave_and_balance_integrate(D, I, lockin_freq, lockin_phase, plot_debug=False)

        Nd_Bd = Nd_Bd / 2 / pd_gain

        return I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd, ref_wave


    def multiply_with_ref_wave_and_balance_integrate(self, D, I, freq, phase, plot_debug=False):  

        N = D.shape[0]
        # - Uncomment To get signal
        # freq *= 2       
        # phase = -1/4
        ref_wave_type = self.settings.child('lock_in', 'refWave').value()
        SamplingRate = self.settings.child('timing', 'sampleRate').value()

        match ref_wave_type:
            case 'Sine' :   ref_wave = self.sine_wave(D, freq, phase)
            case 'Square':  ref_wave = self.square_wave(D, freq, phase)
            case _: raise Exception(f"Error : Unrecognised Reference Wave : {ref_wave_type}")

        number_of_periods = round( (N / (SamplingRate * 1e6)) / (1/freq) )
        points_per_period = round( N / number_of_periods )

        # print(number_of_periods)
        D_matrix = np.reshape(D, ( number_of_periods, points_per_period))
        I_matrix = np.reshape(I, ( number_of_periods, points_per_period))
        ref_matrix = np.reshape(ref_wave, ( number_of_periods, points_per_period))

        D_multiply = np.multiply(D_matrix, ref_matrix)
        I_multiply = np.multiply(I_matrix, ref_matrix)

        D_train = np.sum(D_multiply, axis=1) / points_per_period
        I_train = np.sum(I_multiply, axis=1) / points_per_period

        D_Bd = D_train.sum() / number_of_periods
        I_Bd = I_train.sum() / number_of_periods

        I_Ba = np.sum(I) / N
        D_Ba = np.sum(D) / N

        Nd_Bd = D_Bd / I_Ba

        if plot_debug:
            import matplotlib.pyplot as plt
            fig, [ax0, ax1, ax2] = plt.subplots(1,3, figsize=(18,6))


            x = np.arange( N ) / (SamplingRate * 1e6) * 1e3
            ax0.plot(x, I, label="I")
            ax0.plot(x, D, label="D")
            ax0.plot(x, ref_wave * max(I.max(), D.max()), label="Ref Wave")
            ax0.set_xlabel("Time [ms]"); ax0.set_ylabel("Card Signal [V]"); ax0.legend()

            offset = max(I.max(), D.max()) * 2.1
            for i in range(number_of_periods):
                ax1.plot(I_matrix[i, :] + i*offset, 'darkred')
                ax1.plot(ref_matrix[i, :] * max(I_matrix[i, :]) + i*offset, 'k')
                ax1.plot(I_multiply[i, :] + i*offset, '--', color='darkgreen')
            ax1.set_xlabel("N"); ax1.set_ylabel("Card Signal [V]")


            ax2.plot(I_train, label=f"I_Bd = {I_Bd:.1e}")
            ax2.plot(D_train, label=f"D_Bd = {D_Bd:.1e}")
            ax2.set_xlabel("Pulse Number []"); ax2.set_ylabel("Lockin Signal [a.u.]"); ax2.legend(); ax2.set_title(f"Nd_Bd = {Nd_Bd:.1e}")
            
            plt.tight_layout(); plt.show()

        return I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd, ref_wave


    def update_lockin_param(self):
        self.lockin_step_duration = (1/self.settings.child("lock_in", "LI_PulseFreq").value()) / 2                      # Divide by 2 since one step is defined as only up or down
        self.num_lockin_steps = int(self.settings.child("timing", 'Range').value()*1e-3 / self.lockin_step_duration  /2)*2         #
        self.points_per_step = int( self.lockin_step_duration * round(self.settings.child("timing", "sampleRate").value() * 1e6) )

        print("\n--- Lock In Info")
        print("Lockin Step Duration = ", self.lockin_step_duration*1e3, "ms")
        print("Number of Lockin Steps = ", self.num_lockin_steps)
        print("Points Per Step = ", self.points_per_step)


    def sine_wave(self, data, freq, phase):
        axis = np.linspace(0, np.shape(data)[0] * 1 / (self.settings.child('timing', 'sampleRate').value()*1e6), np.shape(data)[0])

        wave = np.sin(2*np.pi*axis*freq + phase)

        if self.settings.child('lock_in', 'Env', 'EnvShape').value() == 'Sine':

            width = int(self.settings.child('lock_in', 'Env', 'EnvWidth').value()/100 * np.shape(data)[0])
            wave[:width] = np.multiply(wave[:width], self.sine_envelope_start(data[:width]))

            wave[-width:] = np.multiply(wave[-width:], self.sine_envelope_stop(data[-width:]))

        if self.settings.child('lock_in', 'Env', 'EnvShape').value() == 'Linear':

            width = int(self.settings.child('lock_in', 'Env', 'EnvWidth').value()/100 * np.shape(data)[0])
            wave[:width] = np.multiply(wave[:width], self.linear_envelope_start(data[:width]))

            wave[-width:] = np.multiply(wave[-width:], self.linear_envelope_stop(data[-width:]))

        return wave

    def square_wave(self, data, freq, phase):
        axis = np.linspace(0, np.shape(data)[0] * 1 / (self.settings.child('timing', 'sampleRate').value()*1e6), np.shape(data)[0])
        wave = signal.square(t=2*np.pi*axis*freq + phase, duty=0.5)

        if self.settings.child('lock_in', 'Env', 'EnvShape').value() == 'Sine':

            width = int(self.settings.child('lock_in', 'Env', 'EnvWidth').value()/100 * np.shape(data)[0])
            wave[:width] = np.multiply(wave[:width], self.sine_envelope_start(data[:width]))

            wave[-width:] = np.multiply(wave[-width:], self.sine_envelope_stop(data[-width:]))

        if self.settings.child('lock_in', 'Env', 'EnvShape').value() == 'Linear':

            width = int(self.settings.child('lock_in', 'Env', 'EnvWidth').value()/100 * np.shape(data)[0])
            wave[:width] = np.multiply(wave[:width], self.linear_envelope_start(data[:width]))

            wave[-width:] = np.multiply(wave[-width:], self.linear_envelope_stop(data[-width:]))

        return wave

    def sine_envelope_start(self, data):
        length = np.shape(data)[0]
        axis = np.linspace(0, length -1, length)
        return np.sin(2*np.pi*axis/(4* length))

    def sine_envelope_stop(self, data):
        length = np.shape(data)[0]
        axis = np.linspace(0, length -1, length)
        return np.cos(2*np.pi*axis/(4* length))

    def linear_envelope_start(self, data):
        length = np.shape(data)[0]
        axis = np.linspace(0, length -1, length)
        return axis/(length-1)

    def linear_envelope_stop(self, data):
        length = np.shape(data)[0]
        axis = np.linspace(0, length -1, length)
        return 1 - axis/(length-1)



if __name__ == "__main__":
    main(__file__)
