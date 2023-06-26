import yaml

class MhiaConfig:
    def __init__(self, cfg_path):
        self.cfg_path = cfg_path
        
    def get_config(self):
        try:
            with open(self.cfg_path, "r") as f: cfg_temp=yaml.safe_load(f)       #get yaml
            #cfg_temp['sampling_interval_request'] = cfg_temp['sampling_interval_request'] / 1000 #converts milliseconds (user input) to seconds
            act_ch = str(cfg_temp.get('active_channels')).split(',')        #split active_channels from yaml, write in list act_ch
            for i in range(len(act_ch)): act_ch[i] = int(act_ch[i])         #make act_ch a list of int instead of strings
            cfg_temp['active_channels'] = act_ch
        except (RuntimeError, TypeError, NameError, OSError) as err:
            print(f"Could not load configuration! Error: {err}")
            print("Subprocesses could not start, please check syntax of config file!")
            return err
        else: return cfg_temp