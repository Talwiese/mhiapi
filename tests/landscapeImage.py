import os, sys, time, struct, socket, logging, logging.config
sys.path.append("../")
import spidev
from modules.inhouse.mhiabuttons import MhiaButtons 
from modules.inhouse.mhialcd import MhiaDisplay
from modules.inhouse.mhiacfg import MhiaConfig
from modules.thirdparty.waveshare import LCD_1inch47
from PIL import Image,ImageDraw,ImageFont

but = MhiaButtons(200)

CONFIG_PATH = "../config.yaml" if os.path.isfile("../config.yaml") else "../config_default.yaml"
cfg = MhiaConfig(CONFIG_PATH).get_config()

SPI_BUS = cfg['display']['hw_settings']['spi_bus']
SPI_DEVICE = cfg['display']['hw_settings']['spi_device']
SPI_FREQ = cfg['display']['hw_settings']['spi_freq']
RST= cfg['display']['hw_settings']['reset_pin']
DC = cfg['display']['hw_settings']['command_pin']
BL = cfg['display']['hw_settings']['backlight_pin']
BL_FREQ = cfg['display']['hw_settings']['backlight_freq']
disp = LCD_1inch47.LCD_1inch47(spi=spidev.SpiDev(SPI_BUS, SPI_DEVICE),spi_freq=SPI_FREQ,rst=RST,dc=DC,bl=BL, bl_freq=BL_FREQ, i2c=None)

font4Description = ImageFont.truetype(cfg['display']['fontpaths']['SourceCodeProRegular'], cfg['display']['fontsizes']['smallest'])
font4ValueSmall = ImageFont.truetype(cfg['display']['fontpaths']['SourceCodeProRegular'], cfg['display']['fontsizes']['small'])
font4ChannelNumber = ImageFont.truetype(cfg['display']['fontpaths']['SourceCodeProRegular'], cfg['display']['fontsizes']['medium'])
font4ValueLarge = ImageFont.truetype(cfg['display']['fontpaths']['SourceCodeProRegular'], cfg['display']['fontsizes']['largest'])
font4Icons = ImageFont.truetype(cfg['display']['fontpaths']['FontAwesomeFreeRegular'], cfg['display']['fontsizes']['largest'])
    
    # The next block with the tuples on the right side could be somehow moved into mhiacfg, so that the color values are already loaded as tuples here.
back_color1 = tuple(cfg['display']['back_color'])
back_color2 = tuple(cfg['display']['back_color2'])
text_color = tuple(cfg['display']['text_color'])
design_color1 = tuple(cfg['display']['design_color1'])
design_color2 = tuple(cfg['display']['design_color2'])
text_color_less_visible = tuple(cfg['display']['text_color_less_visible'])



disp.Init()
disp.clear()

color = []
color_assign = {
    'back_color': back_color1,
    'back_color2': back_color2,
    'text_color': text_color,
    'design_color1': design_color1,
    'design_color2':design_color2,
    'text_color_less_visible':text_color_less_visible
}
color_assign_names = list(color_assign.keys())


def show():
    landscapeOneCh = Image.new("RGB", (320,172), color_assign['back_color'])
    # prepare background image for landscape mode
    lastShownSingleChannel = 1 
    ImageDraw.Draw(landscapeOneCh).line([(0, 30),(320, 30)], fill = color_assign['design_color1'], width = 1) # top margin
    ImageDraw.Draw(landscapeOneCh).line([(0, 142),(320, 142)], fill = color_assign['design_color1'], width = 1) # bottom margin
    ImageDraw.Draw(landscapeOneCh).line([(50, 30),(50, 142)], fill = color_assign['design_color1'], width = 1) # left margin
    ImageDraw.Draw(landscapeOneCh).text((6, 56), "CH", font = font4ChannelNumber, fill = color_assign['design_color1'])
    
    # Description part
    text2draw = "Descr.: " + cfg['channels_config'][lastShownSingleChannel]['description']
    ImageDraw.Draw(landscapeOneCh).text((9, 3), text2draw, font = font4Description, fill = color_assign['text_color'])

    # Sensing Range Part
    fivetimes_inv_gain = "{:.1f}".format(5 / float(cfg['adc_gain'])) 
    text2draw = "Sensor:0-" + str(cfg['channels_config'][lastShownSingleChannel]['max_voltage']) + "V ADC:0-" + str(fivetimes_inv_gain) + "V PGA:" + str(cfg['adc_gain']) + "x"
    ImageDraw.Draw(landscapeOneCh).text((9, 144), text2draw, font = font4Description, fill = color_assign['text_color']) 

    # Value Part
    ImageDraw.Draw(landscapeOneCh).text((62, 56), "1.234V", font = font4ValueLarge, fill = color_assign['text_color'])   # draw new value including Unit 

    # sensed or calculated
    ImageDraw.Draw(landscapeOneCh).text((220, 30), "calc", font = font4ChannelNumber, fill = color_assign['design_color2'])

    # channel number
    ImageDraw.Draw(landscapeOneCh).text((21, 84), "2", font = font4ChannelNumber, fill = color_assign['design_color1'])
    img_to_show_next = landscapeOneCh.rotate(angle=270, expand=1)
    disp.ShowImage(img_to_show_next)



i=0
j=0

while 1:
    show_calc_val = False
    lastShownSingleChannel = 1
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
                show()
            print(color)                 
        else:
            j=j+1
            print(color_assign_names[j%5])
            color = list(color_assign[color_assign_names[j%5]])
            print(color)
