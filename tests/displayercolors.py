import sys, time, os
from PIL import Image,ImageDraw,ImageFont
sys.path.append("../")
from modules.inhouse.mhiabuttons import MhiaButtons
from modules.inhouse.mhiacfg import MhiaConfig
from modules.inhouse.mhialcd import MhiaDisplay

#sys.path.append("../modules/3rdparty/waveshare")
#sys.path.append("../modules/inhouse/")

#import LCD_1inch47

#from mhialcd import MhiaDisplay

# lcd = MhiaDisplay()
# lcd.disp.bl_DutyCycle(20)
# lcd.disp.bl_Frequency(100)
CONFIG_PATH = "../config.yaml" if os.path.isfile("../config.yaml") else "../config_default.yaml"
CONFIG = MhiaConfig(CONFIG_PATH).get_config()

but = MhiaButtons(200)
lcd = MhiaDisplay(CONFIG)


r = 0
g = 0
b = 0

img = Image.new("RGB", (172,320), (r,g,b))
#color_assign_names = ['back_color','back_color2','text_color','design_color1','design_color2','text_color_less_visible']
color = [r,g,b]
color_assign = {
    'back_color': lcd.back_color1,
    'back_color2': lcd.back_color2,
    'text_color': lcd.text_color,
    'design_color1': lcd.design_color1,
    'design_color2':lcd.design_color2,
    'text_color_less_visible':lcd.text_color_less_visible
}
color_assign_names = list(color_assign.keys())
print(color_assign_names)
i = 0
j = 0

#color_assignement = color_assign_names[0]
while 1:
    lcd.show_calc_val = False
    lcd.setmode(12)
    lcd.lastShownSingleChannel = 1
    if not but.any_button_pushed:
        pass
    else:
        last_but = but.get_last_button_pushed()
        but.any_button_pushed = False
        if last_but != "reset":
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
                #color_assignement = color_assign_names[j%5]
                #colortext="R"+str(color[0])+"G"+str(color[1])+"B"+str(color[2])
                #img.save(colortext + ".png")
                color_assign[color_assign_names[j%5]] = tuple(color)
                print(color_assign_names[j%5] + " set to " + str(color))
                lcd.show_one_channel(2, 1.258)
            lcd.disp.ShowImage(lcd.img_to_show_next)
            print(color)                 
        else:
            j=j+1
            print(color_assign_names[j%5])
            color = list(color_assign[color_assign_names[j%5]])
            print(color)

        #print(i)
        #print(str(color) + " " + str(color_assignement))
        #ImageDraw.Draw(img).rectangle((1,1,172,320), fill=tuple(color))
 