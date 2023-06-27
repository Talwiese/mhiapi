# mhia pi
This repository is meant to be used with a Raspberry Pi singel board computer or other compatible computers. Raspberry Pi is a trademark of Raspberry Pi Ltd. The authors of this repository are not related in any kind to Raspberry Pi Ltd.
Beside of a SBC, you will also need specific hardware on i2c (2x MCP3424 ADCs) and on spi (a ST7735S controlled 172x320 pixel color LCD) to be able to run the mhia pi application.
The mhia pi HAT produced by Talwiese IoT Solutions is the device for which this application was initially developed for, updates are also tested on mhia pi HATs.
There is also a wiki here: www.mhia.at
- HW description available at mhia.at

- Installation steps: TBD, please checkout mhia.at

- Fast instructions: setup your Raspberry Pi, so it is connected to the internet, activate i2c and spi. make sure you have python3 and theses packages: pil, numpy, RPi.GPIO, spidev, smbus2, pyyaml, qrcode and paho-mqtt. clone this repo. change and save config-default.yaml as you wish under filename config.yaml. start the app by running the mhia.py script or by enabling and starting the systemd service: mhia.service
   
