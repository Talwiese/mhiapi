import time, os, sys, spidev as SPI
from PIL import Image,ImageDraw,ImageFont
sys.path.append("../")
from modules.thirdparty.waveshare.LCD_1inch47 import LCD_1inch47

from mhialcd import MHiA_LCD

bus = 0
device = 0
RST = 19
DC = 6
BL = 13

lcd = LCD_1inch47(spi=SPI.SpiDev(bus, device),spi_freq=100000000,rst=RST,dc=DC,bl=BL, bl_freq = 1)

# lcd = MHiA_LCD()
# lcd.disp.bl_DutyCycle(20)
# lcd.disp.bl_Frequency(100)

i = [None] * 8
for j in range(len(i)):
    i[j] = Image.open(str(j) + ".jpg")

l=0
m=0
backwards = False
backwards2 = False
while 1:
    j = l % len(i)
    k = m % 100
    if j == 0:
        backwards = not backwards
    if backwards: l = l + 1
    else: l = l - 1
    if k == 0:
        backwards2 = not backwards2
    if backwards2: m = m + 1
    else: m = m - 1
    lcd.disp.bl_DutyCycle(m)
    lcd.disp.ShowImage(i[j])

