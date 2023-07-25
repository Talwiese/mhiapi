import sys, time, spidev as SPI
from PIL import Image,ImageDraw,ImageFont
sys.path.append("../")
from modules.thirdparty.waveshare.LCD_1inch47 import LCD_1inch47
from modules.inhouse.mhiabuttons import MhiaButtons 

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

lcd = LCD_1inch47(spi=SPI.SpiDev(bus, device),spi_freq=5000000,rst=RST,dc=DC,bl=BL, bl_freq = 1)

but = MhiaButtons(200)

r = 0
g = 0
b = 0

img = Image.new("RGB", (172,320), (r,g,b))

color = [r,g,b]
i = 0

while 1:
    if not but.any_button_pushed:
        time.sleep(0.1)
    else:
        last_but = but.get_last_button_pushed()
        but.any_button_pushed = False
        if last_but == "left":
            if i != 0: i = i - 1 
        elif last_but == "right":
            if i != 3: i = i + 1
        elif last_but == "up":
            color[i] = color[i] + 4
            print(color[i])
        elif last_but == "down":
            color[i] = color[i] - 4
        elif last_but == "center":
            colortext="R"+str(color[0])+"G"+str(color[1])+"B"+str(color[2])
            img.save(colortext + ".png")
        print(i)
        print(color)
        ImageDraw.Draw(img).rectangle((1,1,172,320), fill=tuple(color))
        lcd.ShowImage(img)

