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


import os, sys, time, struct, socket, logging, logging.config

from modules.inhouse.mhiabuttons import MhiaButtons 
from modules.inhouse.mhialcd import MhiaDisplay
from modules.inhouse.mhiaqr import MhiaQR
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
    
    lcd = MhiaDisplay(CONFIG)
    qr = MhiaQR()
    
    signalhandler = SignalHandler()
    
    bouncetime = int(CONFIG['buttons']['bounce_time'])
    buttons = MhiaButtons(bouncetime)
    
    # Preparing a little dictionary of pairs, that will contain 1 to 8 times (timestamp, value), the key is channel number
    # e.g. if channels 1, 4 and 7 where set active the dict will look like this: {1: [...,...], 4: [...,...], 7: [...,...]} 
    current_data = {}
    for i in CONFIG['active_channels']:
        current_data[i] = [None, time.time(), False] # a dict of lists, first in list shall be value, second is scorr. timestamp, third is a flag telling if value "fresh" or not 
    count_channels = len(CONFIG['active_channels'])
    common_logger.info(f"{count_channels} channels are set active, and these are {CONFIG['active_channels']}." )

    # creating a unix domain socket connection to uds_samples that was bound by the sampler process
    # after connection established this sends "disp" over the socket to identify itself as the displayer process
    socket_path = "./uds_samples"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.setblocking(False)    
    temp_counter = 0
    while not (signalhandler.interrupt or signalhandler.terminate):
        temp_counter += 1
        try:                            # try max 20 times
            sock.connect(socket_path)   # timeout is set few lines before
        except Exception as e:
            if temp_counter <= 20: temp_counter += 1
            else:
                error_logger.error(f"Could not connect to sampler after {temp_counter} tries!")
                common_logger.info("Exiting, could not establish uds connection with sampler!")
                sys.exit(1)
        else:                           # if connected (no exception) send "disp" and break this while-loop
            sock.send("disp".encode(encoding = 'UTF-8'))
            break
    
    common_logger.info("Connected to sampler...")

    qr_img=qr.generate(lcd.text_color, lcd.back_color1, CONFIG['display']['qr_text'])

    req_sampling_interval = float(CONFIG['requested_sampling_interval'][CONFIG['adc_resolution']])/1000  # need this in seconds not ms
    
    # At lower sampling intervals (higher samling rate) updating display is slower than sampling of the ADC chip.
    # display_is_laggy is continuesly set and evaluated in the main loop, and updating display is dropped, if display laggy.
    display_is_laggy = False    

    # CONFIG['activ_channels'] is a list, MhiaConfig already formatted the string in config.yaml
    active_channels = CONFIG['active_channels']     
    display_mode = lcd.setmode(10 + active_channels[0])
    # now the main loop starts and runs till process is interrupted by signal, this while-block can still be optimized!
    timestamp = time.time()
    while not (signalhandler.interrupt or signalhandler.terminate):    
        display_mode = lcd.getmode()        
        # try to receive and unpack struct
        try:
            channel, timestamp, value = struct.unpack('!idd', sock.recv(20)) # remember socket is set to non-blocking, meaning we will have here very often 'BockingIOError'
        except Exception as e: 
            display_is_laggy = False # this is necessary here to ensure that display is "refreshed" in case no data available on pipe
        else:
            current_data[channel] = [timestamp, value, True]
            # The values shouldn't be displayed if displayer slower than sampler, so display is only updated when not lagging 
            display_is_laggy = True if (time.time() - timestamp) > req_sampling_interval else False # this needs maybe fine tuning (2*req_sampling_innterval or add some 0.1ms)
            
            # display_mode is a number
            if display_mode == 9:                               # mode 9 means show all channels at once in portrait orientation 
                lcd.show_all_channels(channel, round(value,3))  
            elif 10 < display_mode < 19:                        # mode 11 to 18 shows just one channel in landscape orientation, the second digit means which channel is shown
                ch2bshown = display_mode - 10    
                lcd.show_one_channel(ch2bshown,  round(current_data[ch2bshown][1],3))
            elif 20 < display_mode < 29:                        # in mode 21 to 28 the current graph of one channel is shown, the second digit means which channel
                ch2bshown = display_mode - 20
                lcd.show_one_graph(ch2bshown, round(current_data[ch2bshown][1],3))
            elif display_mode == 40:                            # mode 40 shows the QR code (text set in config), should be a link to a dashboard feeded with live data using publisher
                lcd.display_qr(qr_img)            
            else: pass # i can be 9, 11 to 18, 21 to 28 or 40, if its something else (= never) nothing shall happens     
            if not display_is_laggy: lcd.disp.ShowImage(lcd.img_to_show_next)

        finally:
         
            # in this block the behaviour after pushing a button is defined, that depends on current display_mode
            if buttons.any_button_pushed:
                buttons.any_button_pushed = False
                but = buttons.get_last_button_pushed()      # don't get confused: get_last_button_pushed means actually the "currently" pushed button, 
                common_logger.info(f"Button pushed: {but}")
                if display_mode == 9: # mode 9 is: all channels shown as number on display in portrait orientation
                    if   but ==  "left": lcd.setmode(10 + lcd.lastShownSingleChannel)
                    elif but == "right": lcd.setmode(40)
                    else: pass  
                elif 10 < display_mode < 19: # mode 1x is: just one channel in landscape orientation   
                    if   but ==   "left": lcd.setmode(20 + channel)
                    elif but == "center": 
                        if lcd.show_calc_val: lcd.show_calc_val = False
                        else: lcd.show_calc_val = True
                    elif but ==  "right": lcd.setmode(9)
                    elif count_channels > 1: 
                        j = active_channels.index(display_mode-10) # j is index, that is currently beeing displayed, of the array active_channels from config 
                        if but ==  "down":  
                            if j < count_channels-1: lcd.setmode(10 + active_channels[j+1])
                            else:
                                lcd.setmode(10 + active_channels[0])
                                j = count_channels-1
                        elif but == "up":
                            if j > count_channels-1: lcd.setmode(10 + active_channels[0])
                            else: 
                                lcd.setmode(10 + active_channels[j-1])
                        else:pass
                    else: pass
                elif 20 < display_mode < 29: # mode 2x is: just one cahnnel as graph
                    if   but ==  "left": lcd.setmode(40)
                    elif but == "right": lcd.setmode(10 + lcd.lastShownSingleChannel)
                    else: #count_channels > 1:
                        j = active_channels.index(display_mode-20) # j is current index of the array active_channels from config 
                        if but ==  "down":  
                            if j < count_channels-1: lcd.setmode(20 + active_channels[j+1])
                            else: lcd.setmode(20 + active_channels[0]) 
                        elif but == "up":
                            if j > 0: lcd.setmode(20 + active_channels[j-1])
                            else: lcd.setmode(20 + active_channels[count_channels-1]) 
                        else:pass  
                elif display_mode == 40:
                    if   but ==  "left": lcd.setmode(9)
                    elif but == "right": lcd.setmode(20 + channel)
                    elif but == "center": # temporarly to allow to make "screenshots"
                        lcd.landscapeOneCh.save("land_"+str(time.time())+".png")
                        lcd.portraitAllCh.save("port_"+str(time.time())+".png") 
                else: pass
                if but == "reset": os.system("sudo shutdown now") # more gracefully planned, message to mhia.py?
            else: pass #if no button pushed

    # we are now out of the while block
    common_logger.info("Exiting because of SIGINT or SIGTERM!")
    lcd.disp.clear()  
    lcd.disp.module_exit()
    common_logger.info("Display cleared, SPI closed, GPIOs reset.")
    common_logger.info("Exiting.")
    sys.exit(0)

if __name__=="__main__":
    main()
