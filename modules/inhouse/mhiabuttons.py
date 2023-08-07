#!/usr/bin/env python3

# mhiabuttons.py - a module of the mhia pi application, can run as script
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


import RPi.GPIO as GPIO
import time

class MhiaButtons: 
    
    # Why not put this assignment in config? This should not be changed for the mhia pi (v1.0) board. Change only if the baord design changes, or you enhance the board somehow. 
    # The keys of the dict should not be changed, since the displayer process accesses exactely these keys: "up", "down", ...
    # Orientation: assume the display is used (mainly) in landscape orientation. The long side of the display is horizontal, so the buttons direction correspond to this orientation.
    _button_gpio_assignments = {
        "left" : 16,    
        "right" : 21,
        "down" : 12,
        "up" : 20,
        "center" : 26,
        "reset" : 4
    }

    def __init__(self, bouncetime):
        """
        Setup up the GPIO pins. Bouncetime is for reducing risk of detecting button signal bounces in ms. 300 is a reasonable value for mhia pi.
        """
        self.any_button_pushed = False
        GPIO.setmode(GPIO.BCM) # BCM because external LCD lib also sets GPIO.BCM
        self.ButtonGPIOAssignmentKeys = list(self._button_gpio_assignments.keys())              # We need a seperate list of keys ...
        self.ButtonGPIOAssignmentValues = list(self._button_gpio_assignments.values())          # ... and a seperate list of values,
        self._which_button_pushed = "nothing"
        for x in self.ButtonGPIOAssignmentValues:                                               # ... to set up each pin.
            GPIO.setup(x, GPIO.IN, pull_up_down=GPIO.PUD_UP)                                                        # pull-up resistors are activated, 
            GPIO.add_event_detect(x, GPIO.RISING, callback=self.set_which_button_pushed, bouncetime=bouncetime)     # the GPIO.RISING event is set to be detected, and the callback function that will be called is set.
    
    def set_which_button_pushed(self, pin):
        """
        This is called whenever any of the GPIO.RISING event is detected on the setup (in __init__) GPIOs.
        """ 
        position_in_dict = self.ButtonGPIOAssignmentValues.index(pin)
        self._which_button_pushed = self.ButtonGPIOAssignmentKeys[position_in_dict]
        self.any_button_pushed = True
        print(self._which_button_pushed)
        return None

    def get_last_button_pushed(self):
        return self._which_button_pushed

# You can run this module on its own to test the buttons. The key of pushed button will be shown on standard output.
def main():
    but = MhiaButtons(300)
    while 1:
      print(but.get_last_button_pushed())
      time.sleep(0.5)

if __name__=="__main__":
    main() 
