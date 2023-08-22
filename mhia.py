#!/usr/bin/env python3

# mhia.py - main process of the mhia pi aplication
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


import os, subprocess, time, sys, logging, logging.config
from modules.inhouse.signalhandler import SignalHandler
from modules.inhouse.mhiacfg import MhiaConfig


CONFIG_PATH = "./config.yaml" if os.path.isfile("./config.yaml") else "./config_default.yaml"
CONFIG = MhiaConfig(CONFIG_PATH).get_config()

logging.config.dictConfig(CONFIG['logging'])
common_logger = logging.getLogger("standard")
error_logger = logging.getLogger("error")

common_logger.info(f"Starting mhia application using configuration form {CONFIG_PATH}")


signalhandler = SignalHandler() 

# the next function can be used to discover update of config-file. Intended to be used later for configuration update during runtime.
def config_file_modified(memorized_mtime):
    """
    Little function delivers true, when mtim of config file is not a "memorized" value! update of memorized_time is still TBD ! 
    """
    if os.stat(CONFIG_PATH).st_mtime != memorized_mtime: return True
    else: return False

def main():
    
    process_labels = {
        'samp': "Sampler", 
        'disp': "Displayer", 
        'publ': "Publisher", 
        'stor': "Storer"
    }
    process_paths = {
        'samp': "./sampler.py",
        'disp': "./displayer.py",
        'publ': "./publisher.py",
        'stor': "./storer.py"
    }
    process_pids = {}

    processes_wanted = ['samp'] # 'samp' is wanted every time as the first process
    memorized_mtime = os.stat(CONFIG_PATH).st_mtime    
    signalhandler = SignalHandler()
    #the order in the list MUST be: 'samp', 'stor', 'publ', 'disp'  
    if CONFIG['enabled_modules']['storer']: processes_wanted.append("stor") 
    if CONFIG['enabled_modules']['publisher']: processes_wanted.append("publ")
    if CONFIG['enabled_modules']['displayer']: processes_wanted.append("disp")
    
    processes_started = []
    subpro = {}

    common_logger.info(f"Will try to start these processes: {processes_wanted} ")
    #TBD: the sockets (unix domain sockets) are for now opened in the sampler process, i think it makes more sense that mhia.py, as the management process does it
    for i in processes_wanted:
        #TBD: put this (parts of it) in a try and implement error handling
        subpro[i] = subprocess.Popen([process_paths[i]], shell=False, encoding='UTF-8', bufsize=-1, text=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        processes_started.append(i)
        process_pids[i] = subpro[i].pid
        common_logger.info(process_labels[i] + " started with PID: " + str(process_pids[i]))
    #print(processes_started)
    # THIS NEEDS REWORK, WHAT DOES THE LOOP DO AFTER ALL PROCESSES STARTED?
    
    break_the_loop = False
    while not (signalhandler.interrupt or signalhandler.terminate):
        for i in processes_started:
            ret_code = subpro[i].poll()
            if not (ret_code==None):
                print(f"{process_labels[i]} not running anymore, will terminate all other processes. Check the logs!")
                processes_started.remove(i)
                common_logger.info(f"{process_labels[i]} not running, will terminate all other processes.")
                break_the_loop = True
        if break_the_loop: break
        time.sleep(0.2)
    
    text_to_log = "SIGINT or SIGTERM received! Trying to terminate subprocesses ..." if not break_the_loop else "A needed subprocess is not running, trying to terminate application ..."
    common_logger.info(text_to_log)
    exception_during_termination = False
    for i in processes_started:
        str_popped=processes_started.pop()     
        try: 
            subpro[str_popped].terminate()
            if not subpro[str_popped].poll():
                common_logger.info(f"{str_popped} terminated!")
            else:
                subpro[str_popped].kill()
                if not subpro[str_popped].poll():
                    common_logger.info(f"{str_popped} killed!")           
        except Exception as e: 
            common_logger.info(f"Trying to kill {str_popped} resulted in exception: {e}")
            exception_during_termination = True
    if exception_during_termination or break_the_loop:
        error_logger.error("Exiting due to error!")
        print("Exiting due to error! Check the logs!") 
        sys.exit(1)
    else:
        print("Exiting.") 
        common_logger.info("Exiting.") 
        sys.exit(0)

if __name__=="__main__":
    main()   
