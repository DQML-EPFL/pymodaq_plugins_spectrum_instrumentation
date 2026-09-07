import numpy as np

import matplotlib.pyplot as plt




from pymodaq_plugins_spectrum_instrumentation.hardware.SpectrumCard_wrapper_Single import Spectrum_Wrapper_Single



def main():

    Spectrum = Spectrum_Wrapper_Single(duration=200, sample_rate=0.2)
    Spectrum.initialise_device()
    data = Spectrum.grab_trace()

    sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd = lock_in(data[0], data[1])

    # print()

    plt.plot(sum_data_int, '.')
    plt.plot(diff_data_int, '.')
    plt.show()



def lock_in(diff_data, sum_data):
    """
    From 2 traces, calculate all relevant values
    """

    LI_PulseFreq = 500  
    Range = 200
    sampleRate = 0.2
    lockin_step_duration = (1/LI_PulseFreq) / 2                      # Divide by 2 since one step is defined as only up or down
    num_lockin_steps = int(Range*1e-3 / lockin_step_duration  /2)*2         #
    points_per_step = int( lockin_step_duration * round(sampleRate * 1e6) )
    BG_sub = True
    BG_prop = 70
    Gain = 10

    # --- Reshape to correct size
    diff_data_shortened = diff_data[: int(num_lockin_steps*points_per_step ) ]
    sum_data_shortened = sum_data[: int(num_lockin_steps*points_per_step) ]

    # --- Integrate Pulses and remove Background
    diff_chan_reshaped = diff_data_shortened.reshape(num_lockin_steps, points_per_step)
    sum_chan_reshaped = sum_data_shortened.reshape(num_lockin_steps, points_per_step)

    if BG_sub:
        cutoff = int(points_per_step * BG_prop/100)
        diff_data_int = np.sum( diff_chan_reshaped[:,:cutoff], axis=1 ) * (1-BG_prop/100) - np.sum(diff_chan_reshaped[:,cutoff:], axis=1) * BG_prop/100
        sum_data_int = np.sum( sum_chan_reshaped[:,:cutoff], axis=1 ) * (1-BG_prop/100) - np.sum(sum_chan_reshaped[:,cutoff:], axis=1) * BG_prop/100
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
    ND_int = np.divide(diff_data_int, sum_data_int) / Gain / 2
    ND_a = np.mean(ND_int)

    ND_Bd_list = ND_int[::2] - ND_int[1::2]
    ND_Bd = np.mean(ND_Bd_list)
    ND_Ba = np.mean(ND_int)


    return sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd







if __name__=="__main__": main()