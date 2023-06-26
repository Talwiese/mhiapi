import sys, time, spidev as SPI
from PIL import Image,ImageDraw,ImageFont
sys.path.append("../")
from modules.thirdparty.waveshare.LCD_1inch47 import LCD_1inch47

#sys.path.append("../modules/3rdparty/waveshare")
#sys.path.append("../modules/inhouse/")

#import LCD_1inch47

#from mhialcd import MhiaDisplay

# lcd = MhiaDisplay()
# lcd.disp.bl_DutyCycle(20)
# lcd.disp.bl_Frequency(100)
bus = 0
device = 0
RST = 19
DC = 6
BL = 13

lcd = LCD_1inch47(spi=SPI.SpiDev(bus, device),spi_freq=100000000,rst=RST,dc=DC,bl=BL, bl_freq = 1)

i = [None] * 8

for j in range(len(i)):
    i[j] = Image.open("./pics/" + str(j) + ".png")

l=0
m=0
backwards = False
backwards2 = False
lcd.Init()
stoppedtime = time.time()
while 1:
    j = l % len(i)
    k = m % 100
    if j == 0:
        backwards = not backwards
    if backwards: l = l + 1
    else: l = l - 1
    if k == 0:
        backwards2 = not backwards2
        print (time.time()-stoppedtime)
        stoppedtime = time.time()
    if backwards2: m = m + 1
    else: m = m - 1
    #lcd.bl_DutyCycle(m)
    lcd.ShowImage(i[j])

