#!/usr/bin/env python3

# displayer.py - controls the display on mhia pi, handles user input
# Copyright (C) 2023  Iman Ayatollahi, Talwiese IoT Solutions e.U.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import os, sys, time, struct, socket, logging, logging.config, subprocess, json

from modules.inhouse.mhiabuttons import MhiaButtons 
from modules.inhouse.mhialcd import MhiaDisplay
#from modules.inhouse.mhiaqr import MhiaQR
from modules.inhouse.signalhandler import SignalHandler
from modules.inhouse.mhiacfg import MhiaConfig

CONFIG_PATH = "./config.yaml" if os.path.isfile("./config.yaml") else "./config_default.yaml"
CONFIG = MhiaConfig(CONFIG_PATH).get_config()

logging.config.dictConfig(CONFIG['logging'])
common_logger = logging.getLogger("standard")
error_logger = logging.getLogger("error")

common_logger.info("Starting displayer...")
          
def main():
    """
    Main Function of displayer: UI of the device
    """     
    common_logger.info(f"Config loaded from {CONFIG_PATH}.")
    
    #Preperations for QR and info screen, includes getting some info from host
    ip_json_output = json.loads(subprocess.run(["ip", "-4", "-j", "address"], capture_output=True, text=True).stdout)
    for ip_entry in ip_json_output:
        if ip_entry['ifname']=="wlan0": break # need to put ifname in config
    hostname = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()

    info_pages = {
        '1':{
            'hostname': hostname,
            'ipv4': ip_entry['addr_info'][0]['local']
        },
        '2':{
            'active_cahnnels': CONFIG['active_channels'],
            'resolution': CONFIG['adc_resolution'],
            'requested_sampling_interval': CONFIG['requested_sampling_interval'][CONFIG['adc_resolution']],
        },
        '3':{
            'publisher_enabled': True if CONFIG['enabled_modules']['publisher'] else False,
            'mqtt_broker': CONFIG['publisher']['broker_host'] + ":" + str(CONFIG['publisher']['broker_port']),
            'top_level_topic': CONFIG['publisher']['top_level_topic']
        }
    }
    info_page_nr = 1

    # Preparing a little dictionary of pairs, that will contain 1 to 8 times (timestamp, value), the key is channel number
    # e.g. if channels 1, 4 and 7 where set active the dict will look like this: {1: [...,...], 4: [...,...], 7: [...,...]} 
    current_data = {}
    for i in CONFIG['active_channels']:
        current_data[i] = [None, time.time(), False] # a dict of lists, first in list shall be value, second timestamp, third is a flag telling if value "fresh" or not 
    count_channels = len(CONFIG['active_channels'])
    common_logger.info(f"{count_channels} channels are set active, and these are {CONFIG['active_channels']}." )

    lcd = MhiaDisplay(CONFIG, info_pages)
    signalhandler = SignalHandler()
    bouncetime = int(CONFIG['buttons']['bounce_time'])
    buttons = MhiaButtons(bouncetime)

    # creating a unix domain socket connection to uds_samples that was bound by the sampler process
    # after connection established this sends "disp" over the socket to identify itself as the displayer process
    socket_path = "./uds_samples"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.setblocking(False)    
    temp_counter = 0
    
    while not (signalhandler.interrupt or signalhandler.terminate):
        temp_counter += 1
        try:                            # try max 20 times
            sock.connect(socket_path)
        except Exception as e:
            if temp_counter <= 20: temp_counter += 1
            else:
                error_logger.error(f"Could not connect to sampler after {temp_counter} tries!")
                common_logger.info("Exiting, could not establish uds connection with sampler!")
                print("Error: A needed process not running. Displayer should in general be started by the mhia script!")
                sys.exit(1)
        else:                           # if connected (no exception) send "disp" and break this while-loop
            sock.send("disp".encode(encoding = 'UTF-8'))
            break
    
    common_logger.info("Connected to sampler...")
    req_sampling_interval = float(CONFIG['requested_sampling_interval'][CONFIG['adc_resolution']])/1000  # need this in seconds not ms
    
    # At lower sampling intervals (higher samling rate) updating display is slower than sampling of the ADC chip.
    # display_is_laggy is continuesly set and evaluated in the main loop, and updating display is dropped, if display laggy.
    display_is_laggy = False    

    # CONFIG['activ_channels'] is a list, MhiaConfig already formatted the string in config.yaml
    active_channels = CONFIG['active_channels']     
    display_mode = lcd.setmode(10 + active_channels[0])
    ch2bshown = active_channels[0]

    (channel, timestamp, value) = (1, time.time(), 0)
    sleeptime = 0.01
   
    # here the main loop starts and runs till process is interrupted by signal, this while-block can still be optimized imo!    
    while not (signalhandler.interrupt or signalhandler.terminate):    
        display_mode = lcd.getmode()
        # try to receive and unpack struct
        try:
            channel, timestamp, value = struct.unpack('!idd', sock.recv(20)) # remember socket is set to non-blocking, meaning we will have here very often 'BlockingIOError'
        except Exception as e: # (remember the "try" doesn't block because socket non-blocking) when exception arises the else block will be skipped and finally block executed
            display_is_laggy = False # when exception then the sampler didn't have a new value yet...
            new_sample_ready =  False
        else: # the "try" worked and there is new value from socket connection to sampler
            new_sample_ready = True
            current_data[channel] = [timestamp, value, True] # here latest timestamp, value is saved for each channel. The boolean is flag to say if this channel was last sampled channel 
            # The values shouldn't be displayed if displayer slower than sampler, so display is only refreshed when not lagging 
            display_is_laggy = True if (time.time() - timestamp) > 2*req_sampling_interval else False # this needs maybe fine tuning (2*req_sampling_innterval or add some 0.1ms)
        finally:  # happens in every cycle; 
            # display_mode is a number
            if new_sample_ready and (9 <= display_mode < 40):
                if display_mode == 9:                       # mode 9 means show all channels at once in portrait orientation 
                    lcd.draw_all_channels(channel, round(value,3))  
                elif 10 < display_mode < 19:                        # mode 11 to 18 shows just one channel in landscape orientation, the second digit means which channel is shown
                    ch2bshown = display_mode - 10    
                    lcd.draw_one_channel(ch2bshown,  round(current_data[ch2bshown][1],3))
                elif 20 < display_mode < 29:                        # in mode 21 to 28 the current graph of one channel is shown, the second digit means which channel
                    ch2bshown = display_mode - 20
                    if not current_data[ch2bshown][2]: pass         # means: if value for channel user wants to see is not fresh then pass
                    else: lcd.draw_one_graph(ch2bshown, round(current_data[ch2bshown][1],3))
                else: pass # never
                if not display_is_laggy: 
                    lcd.LCD.ShowImage(lcd.img_to_show_next)
                    print("new")
                current_data[channel][2]=False      # at this point the received data from sampler is not "fresh" anymore
                # lcd.LCD.ShowImage() takes relatively long compared to sampling at high sampling rates (low sampling interval); the SPI speed limits refresh rate: so this shall just happen if display not laggy
            elif 40 <= display_mode < 60:
                if display_mode == 40:                            # mode 40 shows the QR code (text set in config), should be a link to a dashboard feeded with live data using publisher
                    lcd.display_qr()        
                elif 50 < display_mode < 59:
                    page2beshown = display_mode - 50
                    lcd.display_info(page2beshown)
                print("new")
                lcd.LCD.ShowImage(lcd.img_to_show_next)
            
            if (not display_is_laggy): 
                print("new")
                lcd.LCD.ShowImage(lcd.img_to_show_next)  

   
                
        if not buttons.any_button_pushed:
            time.sleep(sleeptime)
        else: # the behaviour directly after pushing a button is defined here, which depends on current display_mode
            buttons.any_button_pushed = False
            but = buttons.get_last_button_pushed()      # don't get confused: get_last_button_pushed means actually the "currently" pushed button, 
            common_logger.info(f"Button pushed: {but}")
            if display_mode == 9: # mode 9 is: all channels shown at once in portrait orientation
                if   but == "down": lcd.setmode(10 + lcd.last_shown_single_channel)
                elif but == "up": lcd.setmode(50 + info_page_nr)
                else: pass  
            elif 10 < display_mode < 19: # mode 1x is: just one channel in landscape orientation   
                if   but == "down": lcd.setmode(20 + channel)
                elif but == "center": 
                    if lcd.show_calc_val: lcd.show_calc_val = False
                    else: lcd.show_calc_val = True
                elif but ==  "up": lcd.setmode(9)
                elif count_channels > 1: 
                    j = active_channels.index(display_mode-10) # j is current index of the array active_channels from config 
                    if but == "right":  
                        if j < count_channels-1: lcd.setmode(10 + active_channels[j+1])
                        else:
                            lcd.setmode(10 + active_channels[0])
                            j = count_channels-1
                    elif but == "left":
                        if j > count_channels-1: lcd.setmode(10 + active_channels[0])
                        else: 
                            lcd.setmode(10 + active_channels[j-1])
                    else:pass
                else: pass
            elif 20 < display_mode < 29: # mode 2x is: just one cahnnel as graph
                if   but == "down": lcd.setmode(40)
                elif but == "up": lcd.setmode(10 + lcd.last_shown_single_channel)
                else: 
                    j = active_channels.index(display_mode-20) # j is current index of the array active_channels from config 
                    if but == "right":  
                        if j < count_channels-1: lcd.setmode(20 + active_channels[j+1])
                        else: lcd.setmode(20 + active_channels[0]) 
                    elif but == "left":
                        if j > 0: lcd.setmode(20 + active_channels[j-1])
                        else: lcd.setmode(20 + active_channels[count_channels-1]) 
                    else:pass  
            elif display_mode == 40:
                if   but == "down": lcd.setmode(50 + info_page_nr)
                elif but == "up": lcd.setmode(20 + channel)
                elif but == "center": # temporarly to allow to make "screenshots", very quick-and-dirty
                    lcd.img_one_channel.save("./screenshots/land_"+str(time.time())+".png")
                    lcd.img_multi_channel.save("./screenshots/port_"+str(time.time())+".png")
                    for i in CONFIG['active_channels']:
                        lcd.imgs_plots[i].save("./screenshots/graph_"+str(time.time())+".png")
            elif 50 < display_mode < 59:
                if   but == "down": lcd.setmode(9)
                elif but == "up": lcd.setmode(40)
                else: 
                    if   but == "left": 
                        if info_page_nr < 3:
                            info_page_nr = info_page_nr + 1
                        else:
                            info_page_nr = 1
                    elif but == "right": 
                        if info_page_nr > 1:
                            info_page_nr = info_page_nr - 1
                        else:
                            info_page_nr = 3
                    lcd.setmode(50 + info_page_nr)
                common_logger.info(f"info page nr: {info_page_nr}")
            else: pass
            if but == "reset": os.system("sudo shutdown now") # more gracefully planned, message or signal to mhia.py?

    # we are now out of the while block
    common_logger.info("Exiting because of SIGINT or SIGTERM!")
    lcd.LCD.clear()  
    lcd.LCD.module_exit()
    common_logger.info("Display cleared, SPI closed, GPIOs reset.")
    common_logger.info("Exiting.")
    sys.exit(0)

if __name__=="__main__":
    main()
