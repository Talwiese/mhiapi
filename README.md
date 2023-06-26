# MHiAplusLCD
## HW list:
- RPi Zero + RPi OS
- adcpi
  - https://www.abelectronics.co.uk/p/69/adc-pi-raspberry-pi-analogue-to-digital-converter
  - https://www.abelectronics.co.uk/kb/article/23/python-library-and-demos
  - repo python lib: https://github.com/abelectronicsuk/ABElectronics_Python_Libraries
- 0.96inch LCD Module (ST7735S)
  - https://www.waveshare.com/product/displays/lcd-oled/lcd-oled-3/0.96inch-lcd-module.htm
  - https://www.waveshare.com/wiki/0.96inch_LCD_Module

- Installation steps
  - configure zero:
    - in /boot/config.txt:
      - uncomment dtparam=i2c_arm=on
      - uncomment dtparam=spi=on
      - add dtparam=i2c_baudrate=1000000
      - core_freq=250
    - in /etc/modules add i2c-dev
  - follow instruction from https://www.waveshare.com/wiki/0.96inch_LCD_Module
   