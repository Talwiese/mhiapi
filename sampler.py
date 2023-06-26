#!/usr/bin/env python3
import os, sys, time, struct, socket, logging, logging.config

from modules.inhouse.signalhandler import SignalHandler
from modules.thirdparty.abelectronics.ADCPi import ADCPi
from modules.inhouse.mhiacfg import MhiaConfig

CONFIG_PATH = "./config.yaml" if os.path.isfile("./config.yaml") else "./config_default.yaml"
CONFIG = MhiaConfig(CONFIG_PATH).get_config()
logging.config.dictConfig(CONFIG['logging'])

common_logger = logging.getLogger("standard")
error_logger = logging.getLogger("error")

common_logger.info("Starting sampler...")

def capture(adc, channel):
    timestamp = time.time()
    value = adc.read_voltage(channel)      # for raw binary value = adc.read_raw(channel) for voltage (calculated by ADCPi lib) adc.read_voltage(channel)
    duration = time.time() - timestamp
    return duration, timestamp, value

def main():
    """
    Main function of sampler: drives the ADC chips and sends sampled values over uds
    """
    common_logger.info(f"config loaded from {CONFIG_PATH}.") 
    
    socket_path = "./uds_samples"
    # remove possibly still exisiting uds from last execution
    if os.path.exists(socket_path): 
        try:
            os.remove(socket_path)
        except OSError as error:
            error_logger.exception(f"{error}, could not remove old socket.")
            common_logger.info("Exiting.")
            sys.exit(1)
        else: pass
         
    #setting up the ADCPi module from ABelectronics (todo: use new selfmade lib?)
    (chip1addr, chip2addr, bitrate, pga) = (CONFIG['chip1_address'], CONFIG['chip2_address'], CONFIG['adc_bitrate'], CONFIG['adc_gain'])
    common_logger.info(f"ADC parameters read from config: chip1 at 0x{chip1addr:02x}, chip2 at 0x{chip2addr:02x}, bit rate = {bitrate}, gain = {pga}")
    adc = ADCPi(chip1addr, chip2addr, bitrate)
    common_logger.info("ADC object created, usind ABElectronics module.")
    adc.set_conversion_mode(0)
    adc.set_pga(pga)
    common_logger.info("ADC set and ready for sampling.")

    # the requested sample rate for different bitrates is read from config
    # the goal is to have almost constant time intervalls between samples, see the loop wherein capture is called
    requested_sampling_interval = float(CONFIG['requested_sampling_interval'][bitrate]/1000)
    common_logger.info(f"Requested sampling interval for {bitrate} bit conversion is {requested_sampling_interval*1000} ms")    

    # initialising lists with current values, timestamps; the indices represent the channel number - 1
    sample_values = [int] * 8
    sample_timestamps = [float] * 8
    actual_sampling_duration = [float] * 8

    # this running process is named "sampler", other mhia processes (modules) have also self explanatory names
    # in config file these modules can be activated or deactivated depending on customers' use case   
    displayer_wanted = True if CONFIG['enabled_modules']['displayer'] else False
    common_logger.info("Config wants displayer.") if displayer_wanted else None
    publisher_wanted = True if CONFIG['enabled_modules']['publisher'] else False
    common_logger.info("Config wants publisher.") if publisher_wanted else None
    storer_wanted = True if CONFIG['enabled_modules']['storer'] else False
    common_logger.info("Config wants storer.") if storer_wanted else None
    (displayer_connected, publisher_connected, storer_connected) = (False, False, False)
    
    tempstr = ""

    # binding a unix domain socket for inter-process communication
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path)
    sock.settimeout(0.2)
    sock.listen()
    common_logger.info("Unix domain socket created and listening...")

    #this while loop lets the required modules get connected to the uds 
    wanted = displayer_wanted + publisher_wanted + storer_wanted
    connected = displayer_connected + publisher_connected + storer_connected    

    signalhandler = SignalHandler() 
    temp_counter = 0
    common_logger.info("socket is listening ...")
    
    while (wanted > connected) and not (signalhandler.interrupt or signalhandler.terminate):
        # this loop contains a try block, that is repeated max 30 times. Process exits if the wanted processes didn't connect during this time.
        try:
            temp_sock, client_address = sock.accept()
        except Exception as e:
            if temp_counter <= 30: temp_counter += 1    # tries 30 times   
            else: 
                error_logger.error(f"waited {temp_counter * sock.gettimeout()} seconds for requested processes, at least one of them did not connect!")
                common_logger.info("Exiting, at least one needed process didn't connect in time!")
                sys.exit(1)
        else:
            tempstr = temp_sock.recv(4).decode(encoding = 'UTF-8')
            if tempstr == "publ":
                publisher_connected = True
                publisher_socket = temp_sock.dup()
                common_logger.info("Publisher connected!")
                del temp_sock 
            elif tempstr == "disp":
                displayer_connected = True
                displayer_socket = temp_sock.dup() 
                common_logger.info("Displayer connected!")
                del temp_sock 
            elif tempstr == "stor":
                storer_connected = True
                storer_socket = temp_sock.dup()
                common_logger.info("Storer connected!")
                del temp_sock 
        finally: 
            connected = displayer_connected + publisher_connected + storer_connected            
    # "temp_sock" (socket object) is to find out what process got connected 
    
    common_logger.info("All requested processes connected!")
    
    sock.setblocking(False)

    # this loop calls capture continuesly, calculates the variable sleep time till next capture call and sends data to connected processes (modules)
    active_channels = CONFIG['active_channels']
    
    common_logger.info(f"Starting capturing and sampling these channels: {active_channels}, quantizing in {bitrate} bit, will try to sample every {requested_sampling_interval * 1000} ms! ")
    
    period_of_time_for_moving_average = 60 # seconds, used for debug or info level logging. 
    average_sampling_duration = requested_sampling_interval / 2 # just a starting value, will get more precise in every iteration of the main loop
    count_for_eval = int(period_of_time_for_moving_average / requested_sampling_interval)   
    
    struct_def = '!idd'     # over the uds connection a struct is passed that is packed, !idd stands for one int and two doubles, that is 4+8+8=20 bytes
    
    while not (signalhandler.interrupt or signalhandler.terminate):        

        for i in active_channels:
            last_time = time.time()
            j=i-1 # active_channels is between 1 and 8, j as index for the lists between 0 and 7, be carefull here what is i and what is j
            actual_sampling_duration[j], sample_timestamps[j], sample_values[j] = capture(adc, i)
            data2send = bytearray(struct.pack(struct_def, i, sample_timestamps[j],sample_values[j]))

            try:
                if displayer_connected: displayer_socket.send(data2send)
                if publisher_connected: publisher_socket.send(data2send)
            except Exception as e:
                error_logger.error(f"Could not send data over socket, because: {e} !")
                common_logger.info("Exiting due to error!")
                sys.exit(1)       

            average_sampling_duration = (average_sampling_duration + actual_sampling_duration[j])/2
            count_for_eval = count_for_eval - 1
            if count_for_eval > 1: pass
            else: 
                #print((req_sample_interval - mean_sampling_duration) * 1000)
                if average_sampling_duration > requested_sampling_interval:
                    common_logger.warn(f"mean sampling duration {average_sampling_duration*1000:.1f} ms, higher than {requested_sampling_interval*1000:.1f}.")
                common_logger.info(f"mean sampling duration {average_sampling_duration*1000:.1f} ms, lower than {requested_sampling_interval*1000:.1f}.")
                count_for_eval = int(period_of_time_for_moving_average / requested_sampling_interval)
            
            sleepval = requested_sampling_interval - actual_sampling_duration[j]
            time.sleep(sleepval)

    common_logger.info("Exiting because of SIGINT or SIGTERM!")
    sys.exit(0)

if __name__=="__main__":
    main()