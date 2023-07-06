# mhiacfg.py - a module of the mhia pi application
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

import yaml

class MhiaConfig:
    def __init__(self, cfg_path):
        self.cfg_path = cfg_path
        
    def get_config(self):
        try:
            with open(self.cfg_path, "r") as f: cfg_temp=yaml.safe_load(f)       #get yaml
        # messages shall be logged, not printed out! TBD soon.
        except (RuntimeError, TypeError, NameError, OSError) as err:
            print(f"Could not load configuration! Error: {err}")
            print("Subprocesses could not start, please check syntax of config file!")
            return err
        else: return cfg_temp