from pymodaq_plugins_thorlabs.daq_move_plugins.daq_move_KinesisIntegratedStepper import DAQ_Move_KinesisIntegratedStepper
import time
TIME_LIMIT = 10 # in seconds

def customPID(modules_manager, angle):
    print(f"Moving to angle {angle}, and balancing.")

    # LockIn = [det for det in modules_manager.detectors if det.detector == "Spectrum_Lockin"][0]
    Ello = [act for act in modules_manager.actuators_all if act.actuator == "ELLO"][0] 
    print(modules_manager.actuators_all)
    Waveplate= [act for act in modules_manager.actuators_all if act.actuator == "CageRotator"][0]

    Ello.controller.move_absolute(angle)
    
    dir = +1
    step_size = 5

    iteration = 0
    
    previous_value = get_D_Ba( modules_manager )
    start = time.time()
    while abs(previous_value) > 1:
        iteration +=1
        Waveplate.move_abs(Waveplate.controller.get_position() + dir*step_size)
        time.sleep(1)
        new_value = get_D_Ba( modules_manager )

        print(f"{iteration} : Went from {previous_value} to {new_value}. Waveplat Position is {Waveplate.controller.get_position()}")

        if abs(new_value) > abs(previous_value) :
            dir *= -1
            step_size /= 2
            print(f"Flipping Direction. Step Size is now {step_size}")

        # if time.time() - start > TIME_LIMIT:
        #     print("Went over time limit, exiting PID")
        #     print(start, time.time(), TIME_LIMIT)
        #     break
        
        previous_value = new_value

    print("Done. Balancing Angle is ", Waveplate.controller.get_position(), ", obtained after ", iteration, " iterations") 


from pymodaq_data.data import DataToExport
from pymodaq.utils.managers.modules_manager import ModulesManager

def get_D_Ba(modules_manager : ModulesManager):
    modules_manager.connect_detectors()
    dte = modules_manager.grab_data()
    modules_manager.connect_detectors(False)
    # sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd, phi_a, phi_Ba, phi_Bd = LockIn.grab_data()
    D_Ba = [data for data in dte if data._name =="D_Ba"][0].data[0][0]
    return D_Ba



# def grab_Lockin(LockIn):
#     preTrig = LockIn.settings.child("detector_settings", "trig_params", "preTrig").value()
#     Range = LockIn.settings.child("detector_settings", "timing", "Range").value()
#     Num_Pulses = LockIn.settings.child("detector_settings", "timing", "Num_Pulses").value()

    


#     # --- Grab a Trace
#     post_trig =  (1-preTrig/100) * Range / Num_Pulses
#     data_tot = LockIn.controller.grab_trace( post_trig_ms = post_trig )

#     # --- Seperate sum and diff
#     ii = LockIn.controller.activated_str.index( LockIn.settings.child("detector_settings", 'lock_in', 'diffChannel').value() )
#     index = len(LockIn.controller.activated_str[:ii])
#     diff_data = data_tot[index]

#     ii = LockIn.controller.activated_str.index( LockIn.settings.child("detector_settings", 'lock_in', 'sumChannel').value() )
#     index = len(LockIn.controller.activated_str[:ii])
#     sum_data = data_tot[index]

#     # --- Lock In Process
#     sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd, phi_a, phi_Ba, phi_Bd = lockin(LockIn, diff_data, sum_data)

#     return D_Ba



# def lockin(LockIn, diff, sum):

#     # --- Reshape to correct size
#     diff_data_shortened = diff[: int(LockIn.num_lockin_steps*LockIn.points_per_step ) ]
#     sum_data_shortened = sum[: int(LockIn.num_lockin_steps*LockIn.points_per_step) ]

#     # --- Integrate Pulses and remove Background
#     diff_chan_reshaped = diff_data_shortened.reshape(LockIn.num_lockin_steps, LockIn.points_per_step)
#     sum_chan_reshaped = sum_data_shortened.reshape(LockIn.num_lockin_steps, LockIn.points_per_step)

#     if LockIn.settings.child( "detector_settings", 'lock_in', 'BG_sub').value() == True:
#         cutoff = int(LockIn.points_per_step * LockIn.settings.child( "detector_settings", "lock_in", "BG_prop").value()/100)
#         diff_data_int = np.sum( diff_chan_reshaped[:,:cutoff], axis=1 ) * (1-LockIn.settings.child( "detector_settings", 'lock_in', 'BG_sub').value()/100) - np.sum(diff_chan_reshaped[:,cutoff:], axis=1) * LockIn.settings.child( "detector_settings", 'lock_in', 'BG_sub').value()/100
#         sum_data_int = np.sum( sum_chan_reshaped[:,:cutoff], axis=1 ) * (1-LockIn.settings.child( "detector_settings", 'lock_in', 'BG_sub').value()/100) - np.sum(sum_chan_reshaped[:,cutoff:], axis=1) * LockIn.settings.child( "detector_settings", 'lock_in', 'BG_sub').value()/100
#     else:
#         diff_data_int = np.sum(diff_chan_reshaped, axis=1)
#         sum_data_int = np.sum(sum_chan_reshaped, axis=1)

#     # - Compute I_Ba and I_Bd
#     I_Bd_list = sum_data_int[::2] - sum_data_int[1::2]
#     I_Bd = np.mean(I_Bd_list)
#     I_Ba = np.mean(sum_data_int)

#     # - Compute D_Ba and D_Bd
#     D_Bd_list =   diff_data_int [::2] - diff_data_int [1::2]
#     D_Bd = np.mean(D_Bd_list)
#     D_Ba = np.mean(diff_data_int)


#     # - Compute ND_Ba and ND_Bd
#     ND_int = np.divide(diff_data_int, sum_data_int) / LockIn.settings.child( "detector_settings", 'lock_in', 'Gain').value() / 2
#     ND_a = np.mean(ND_int)

#     ND_Bd_list = ND_int[::2] - ND_int[1::2]
#     ND_Bd = np.mean(ND_Bd_list)
#     ND_Ba = np.mean(ND_int)

#     # - Computing phi_Ba and phi_Bd
#     phi_a = ND_a / LockIn.settings.child( "detector_settings", 'lock_in', 'Conversion').value()
#     phi_Ba = ND_Ba / LockIn.settings.child( "detector_settings", 'lock_in', 'Conversion').value()
#     phi_Bd = ND_Bd / LockIn.settings.child( "detector_settings", 'lock_in', 'Conversion').value()

#     return sum_data_int, I_Ba, I_Bd, diff_data_int, D_Ba, D_Bd, ND_a, ND_Ba, ND_Bd, phi_a, phi_Ba, phi_Bd