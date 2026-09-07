from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_Single import Spectrum_Wrapper_Single
from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_FIFO import Spectrum_Wrapper_FIFO
import numpy as np
import matplotlib.pyplot as plt

liFreq = 500
liPhase = .2
liTime = 100
refWave = 'Sine'
SamplingRate = 0.2
ShowTraces = False

EnvShape = None
EnvWidth = 1

X = True
Y = False
R = False
Theta = False

balance = False
diff_chan = 'D'
int_chan = 'I'

cutoffFreq = 0

live = True


def main():
    
    controller = Spectrum_Wrapper_FIFO(duration=     20, 
                                        sample_rate=   SamplingRate)

    initialized = controller.initialise_device(clock_mode=             ["internal PLL", "external", "external reference"][2],
                                                    clock_frequency=        80.01,
                                                    channels_to_activate=   [0,0,1,0,1,0,0,0],
                                                    channel_amplitude=      5000,
                                                    trigger_settings=       {"trigger_type":        [ "None", "Channel trigger", "Software trigger", "External analog trigger" ][3],
                                                                                "trigger_channel":  ["CH0", "CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"][0],
                                                                                "trigger_mode":     [ "Rising edge", "Falling edge", "Both"][0],
                                                                                "trigger_level":    100}
                                                    )


    # Single Aquisition
    import matplotlib.pyplot as plt
    data = controller.grab_trace()
    D = data[0]
    I = data[1]

    I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd = lockin(D, I)

    if live: 
        import time
        max_len = 50

        plt.ion()
        fig, [ax, ax1, ax2] = plt.subplots(1,3, figsize=(6*3.5,6))

        x= []
        Nd_Bd_list, I_Bd_list, D_Bd_list, I_Ba_list, D_Ba_list = [], [], [], [], []
        i = 0
        while True:
            
            i += 1 

            data = controller.grab_trace()
            D = data[0]
            I = data[1]
            I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd = lockin(D, I)

            x.append(i); 
            Nd_Bd_list.append(Nd_Bd); I_Bd_list.append(I_Bd); D_Bd_list.append(D_Bd)
            I_Ba_list.append(I_Ba); D_Ba_list.append(D_Ba)
            if len(x) > max_len: x.pop(0); Nd_Bd_list.pop(0); I_Bd_list.pop(0);  D_Bd_list.pop(0); I_Ba_list.pop(0); D_Ba_list.pop(0)


            ax.clear()
            ax.plot(x, Nd_Bd_list, label=f"Nd_Bd = {Nd_Bd:.1e}")
            ax.plot(x, I_Bd_list, label=f"I_Bd = {I_Bd:.1e}")
            ax.plot(x, D_Bd_list, label=f"D_Bd = {D_Bd:.1e}")
            ax.set_xlabel("Aquisition []"); ax.set_ylabel("Lockin Signal [a.u.]"); ax.legend(loc="upper left")

            ax1.clear()
            ax1.plot(x, I_Ba_list, label=f"I_Ba = {I_Ba:.1e}")
            ax1.plot(x, D_Ba_list, label=f"D_Ba = {D_Ba:.1e}")
            ax1.set_xlabel("Aquisition []"); ax1.set_ylabel("Lockin Signal [a.u.]"); ax1.legend(loc="upper left")

            ax2.clear()
            ax2.plot(I_train, label="I")
            ax2.plot(D_train, label="D")
            ax2.set_xlabel("Time [s]"); ax2.set_ylabel("Integrated Signal [a.u.]"); ax2.legend(loc="upper left")

            fig.canvas.draw()
            fig.canvas.flush_events()
            if not plt.fignum_exists(fig.number): break

def lockin(D, I):


    # D = apply_lowpass_filter(D)
    # I = apply_lowpass_filter(I)


    # Get X
    I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd = multiply_with_ref_wave_and_balance_integrate(D, I, liFreq, liPhase*np.pi, plot_debug=False)

    Nd_Bd /= 2

    return I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd


def multiply_with_ref_wave_and_balance_integrate_old(D, I, freq, phase):  

    N = D.shape[0]
    match refWave:
        case 'Sine' :   ref_wave = sine_wave(D, freq, phase)
        case 'Square':  ref_wave = square_wave(D, freq, phase)

    D_Bd = np.sum(np.multiply(D, ref_wave)) / N
    I_Bd = np.sum(np.multiply(D, ref_wave)) / N

    I_Ba = np.sum(np.multiply(I, np.abs(ref_wave))) / N
    D_Ba = np.sum(np.multiply(I, np.abs(ref_wave))) / N

    ND_Bd = D_Bd / I_Ba

    x = np.arange( N ) * SamplingRate * 1e-6
    plt.plot(x, D)
    plt.plot(x, I)
    plt.plot(x, ref_wave)
    plt.show()

    return ND_Bd


def multiply_with_ref_wave_and_balance_integrate(D, I, freq, phase, plot_debug=False):  

    N = D.shape[0]
    # - Uncomment To get signal
    # freq *= 2       
    # phase = -1/4

    match refWave:
        case 'Sine' :   ref_wave = sine_wave(D, freq, phase)
        case 'Square':  ref_wave = square_wave(D, freq, phase)

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

    return I_train, I_Ba, I_Bd, D_train, D_Ba, D_Bd, Nd_Bd


def multiply_with_ref_wave_and_integrate_ND(D, I, freq, phase, index_max=0):

    match refWave:
        case 'Sine' :   ref_wave = sine_wave(D, freq, phase)
        case 'Square':  ref_wave = square_wave(D, freq, phase)

    N = D.shape[0]
    period = 1 / freq
    points_per_period = int( period * SamplingRate*1e6 )

    D_bulk = D[: int(N/points_per_period)*points_per_period ].reshape(int(N/points_per_period), points_per_period)
    I_bulk = I[: int(N/points_per_period)*points_per_period ].reshape(int(N/points_per_period), points_per_period)
    ref_bulk = ref_wave[: int(N/points_per_period)*points_per_period ].reshape(int(N/points_per_period), points_per_period)

    ND_bulk = (np.sum(D_bulk*ref_bulk, axis=1)/points_per_period) / (np.sum(I_bulk*ref_bulk, axis=1)/points_per_period)
    ND_bulk = np.sum(  ND_bulk  ) / D_bulk.shape[0]


    if  int(N/points_per_period)*points_per_period == N: return ND_bulk

    D_end = D[int(N/points_per_period)*points_per_period:]
    I_end = I[int(N/points_per_period)*points_per_period:]
    ref_end = ref_wave[int(N/points_per_period)*points_per_period:]

    ND_end = (np.sum(D_end*ref_end, axis=1)/points_per_period) / (np.sum(I_end*ref_end, axis=1)/points_per_period)
    ND_end = np.sum(  ND_end  ) / D_end.shape[0]

    x = np.arange( N ) * SamplingRate * 1e-6
    plt.plot(x, D)
    plt.show()


    return np.mean([ND_bulk, ND_end])


def sine_wave(data, freq, phase):
    axis = np.linspace(0, np.shape(data)[0] * 1 / (SamplingRate*1e6), np.shape(data)[0])

    wave = np.sin(2*np.pi*axis*freq + phase)

    if EnvShape == 'Sine':

        width = int(EnvWidth/100 * np.shape(data)[0])
        wave[:width] = np.multiply(wave[:width], sine_envelope_start(data[:width]))

        wave[-width:] = np.multiply(wave[-width:], sine_envelope_stop(data[-width:]))

    if EnvShape == 'Linear':
        print('here')

        width = int(EnvWidth/100 * np.shape(data)[0])
        wave[:width] = np.multiply(wave[:width], linear_envelope_start(data[:width]))

        wave[-width:] = np.multiply(wave[-width:], linear_envelope_stop(data[-width:]))

    return wave

def square_wave(data, freq, phase):
    import signal
    axis = np.linspace(0, np.shape(data)[0] * 1 / (SamplingRate*1e6), np.shape(data)[0])
    wave = signal.square(t=2*np.pi*axis*freq + phase, duty=0.5)

    if EnvShape == 'Sine':

        width = int(EnvWidth/100 * np.shape(data)[0])
        wave[:width] = np.multiply(wave[:width], sine_envelope_start(data[:width]))

        wave[-width:] = np.multiply(wave[-width:], sine_envelope_stop(data[-width:]))

    if EnvShape == 'Linear':
        print('here')

        width = int(EnvWidth/100 * np.shape(data)[0])
        wave[:width] = np.multiply(wave[:width], linear_envelope_start(data[:width]))

        wave[-width:] = np.multiply(wave[-width:], linear_envelope_stop(data[-width:]))

    return wave

def sine_envelope_start(data):
    length = np.shape(data)[0]
    axis = np.linspace(0, length -1, length)
    return np.sin(2*np.pi*axis/(4* length))

def sine_envelope_stop(data):
    length = np.shape(data)[0]
    axis = np.linspace(0, length -1, length)
    return np.cos(2*np.pi*axis/(4* length))

def linear_envelope_start(data):
    length = np.shape(data)[0]
    axis = np.linspace(0, length -1, length)
    return axis/(length-1)

def linear_envelope_stop(data):
    length = np.shape(data)[0]
    axis = np.linspace(0, length -1, length)
    return 1 - axis/(length-1)


if __name__=="__main__": main()