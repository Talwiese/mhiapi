# mhialcd.py - a module of the mhia pi application
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

import time
import spidev
from modules.thirdparty.waveshare import LCD_1inch47
from PIL import Image,ImageDraw,ImageFont

class MhiaDisplay:
    def __init__(self, config) -> None:
        '''
        Class of the Display including the images beeing shown on it.
        '''
        #loading config
        self.cfg = config

        #Creating the display object and initializing it using the Waveshare module
        SPI_BUS = self.cfg['display']['hw_settings']['spi_bus']
        SPI_DEVICE = self.cfg['display']['hw_settings']['spi_device']
        SPI_FREQ = self.cfg['display']['hw_settings']['spi_freq']
        RST= self.cfg['display']['hw_settings']['reset_pin']
        DC = self.cfg['display']['hw_settings']['command_pin']
        BL = self.cfg['display']['hw_settings']['backlight_pin']
        BL_FREQ = self.cfg['display']['hw_settings']['backlight_freq']
        self.LCD = LCD_1inch47.LCD_1inch47(spi=spidev.SpiDev(SPI_BUS, SPI_DEVICE),spi_freq=SPI_FREQ,rst=RST,dc=DC,bl=BL, bl_freq=BL_FREQ, i2c=None)

        #Creating the ImageFont objects
        self.font_regular_smallest = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['smallest'])
        self.font_regular_small = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['small'])
        self.font_regular_medium = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['medium'])
        self.font_bold_medium = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProBold'], self.cfg['display']['fontsizes']['medium'])
        self.font_regular_largest = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['largest'])
        
        #self.font4Icons = ImageFont.truetype(self.cfg['display']['fontpaths']['FontAwesomeFreeRegular'], self.cfg['display']['fontsizes']['largest'])
        
        self.em_dash_width_largest = int(self.cfg['display']['fontsizes']['largest'] * 0.6)

        #PIL needs RGB values as tuples not lists, so here we build tuples out of lists 
        self.back_color1 = tuple(self.cfg['display']['back_color1'])
        self.back_color2 = tuple(self.cfg['display']['back_color2'])
        self.text_color1 = tuple(self.cfg['display']['text_color1'])
        self.text_color2 = tuple(self.cfg['display']['text_color2'])
        self.design_color1 = tuple(self.cfg['display']['design_color1'])
        self.design_color2 = tuple(self.cfg['display']['design_color2'])

        #Creating the base images to be shown on the display
        self.img_multi_channel = Image.new("RGB", (172, 320), self.back_color1)
        self.img_one_channel = Image.new("RGB", (320,172), self.back_color1)
 
        self.qr_img = Image.new("RGB", (172,320), self.back_color1)
        self.labeltmpimg = Image.new("RGB", (42,172), self.back_color1) # this is a temp img for pasting vertical axis label on plots
        self.labeltmpimg2 = Image.new("RGB", (60,40), self.back_color1) # this is a temp img for pasting little box on right top of the plot
        self.imgs_plots = {}
        for channel in self.cfg['active_channels']:
            self.imgs_plots[channel] = Image.new("RGB", (172,320), self.back_color1) # this is drawn rotated from beginning, so no img.rotate needed later

        self.__mode = 11 # setting the mode of display, 11 means draw channel 1 (second digit) in landscape mode (first digit) 

        # this little block prepares lists to hold the points of the diagramm for each channel 
        self.lastx = [40] * 8 # last y and last x are the coordinates of the current value in graph mode, here beginning is set. 40 is vertical zero
        self.lasty = [11] * 8 # 11 is the horizontal zero
        self.xs = range(40,280,1)   # is [40, 42, ..., 276, 278] the indices are [0, 1, ..., 119]
        self.points_flat = [[11] * 480] * 8 # a 2d-array of 8 channels, each contains 240 time the value 11. 
        for j in range(0,8):
            for i in range(0,240):
                self.points_flat[j][i*2+1]=self.xs[i]
        self.counter_for_graph = 0  

        #self.__connected_wifi_symbol = False

        self.sens_and_calc_text = ["SENS", "CALC"]
        (self.show_calc_val, self.calc_shown_prev_time)  = (False, True) # this assignment is necessary for the beginning

        # prepare background image for single channel mode
        self.last_shown_single_channel = 0 # not lastShown channel but it is set to 0 (= no channel) at startup
        ImageDraw.Draw(self.img_one_channel).line([(0, 52),(320, 52)], fill = self.design_color1, width = 1) # second top margin
        ImageDraw.Draw(self.img_one_channel).line([(0, 142),(320, 142)], fill = self.design_color1, width = 1) # bottom margin
        ImageDraw.Draw(self.img_one_channel).text((2, 56), "CH", font = self.font_regular_medium, fill = self.design_color1)

        # prepare background for all channels mode
        for j in range(0,9):
            back_color_dyn = self.back_color1 if j%2 == 1 else self.back_color2
            ImageDraw.Draw(self.img_multi_channel).rectangle((0, 0 + j*36 - 4, 172, (j+1)*36 - 4), fill=back_color_dyn)
        for j in range(1,9):
            ImageDraw.Draw(self.img_multi_channel).text((8, (j*36 - 1)), str(j), font = self.font_regular_small, fill = self.design_color1)
        ImageDraw.Draw(self.img_multi_channel).line([(0, 32),(172, 32)], fill = self.design_color1, width = 2) # header border
        ImageDraw.Draw(self.img_multi_channel).line([(32, 0),(32, 320)], fill = self.design_color1, width = 1) # channel border

        # prepares background for plot mode
        self.last_drawn_plot_channel = 0
        for channel in self.cfg['active_channels']:
            #ImageDraw.Draw(self.imgs_plots[channel]).line([(9, 39),(9, 300)], fill = self.design_color1, width = 2) # zero line, time axis
            ImageDraw.Draw(self.labeltmpimg).text((22, 8), "V", font = self.font_regular_smallest, fill = self.text_color2)
            self.imgs_plots[channel].paste(self.labeltmpimg.rotate(angle=270, expand=1), (6,-1))

        self.LCD.Init()
        self.LCD.clear()

        self.img_to_show_next = self.img_multi_channel

        self.active_channels = self.cfg['active_channels']
        
        self.pga = [int] * 9
        self.pga_inv = [float] * 9
        self.pga[0] = self.cfg['adc_gain']
        self.pga_inv[0] = 1/self.pga[0]
        for i in self.active_channels:
            try:
                self.pga[i] = self.cfg['channels_config'][i]['wanted_pga']
                self.pga_inv[i] = 1/self.pga[i]
            except KeyError: #happens when pga for channel i not defined in config, or wrong... fallback to default (global pga 'adc_gain' in config)
                self.pga[i] = self.pga[0]
                self.pga_inv[i] = 1/self.pga[0]
        print(self.pga, 5*self.pga_inv[8])

    def getmode(self):
        return self.__mode
    
    def setmode(self, mode):
        self.__mode=mode

    def draw_all_channels(self, channel, value):
        start_time_of_this_call = time.time()    
        i = channel - 1 + 1 # the first i with index 0 is for the header-info on the display
        text_to_draw = "{:.3f}".format(value) + "V"
        back_color_dyn = self.back_color1 if i%2 == 1 else self.back_color2 #to have alternating backgrounds for each line (channel)
        ImageDraw.Draw(self.img_multi_channel).rectangle((33, i*36 - 2, 172, (i+1)*36 - 6), fill=back_color_dyn) #draws an empty rectangle over the value of a channel      
        ImageDraw.Draw(self.img_multi_channel).text((44, i*36 - 1), text_to_draw, font = self.font_regular_small, fill = self.text_color1) #draws the updated value of a channel
        #self.LCD.ShowImage(self.img_multi_channel)
        self.__mode = 9 # 9s stand for the mode where all channels are shown in portrait orientation
        self.img_to_show_next = self.img_multi_channel
        return time.time()-start_time_of_this_call
    
    def draw_one_channel(self, channel, value):
        start_time_of_this_call = time.time()
        # XOR, if calc wanted but sens shown last time, or if sens wanted and calc shown last time.... to clear field and update field on display
        if (self.show_calc_val ^ self.calc_shown_prev_time):    
            ImageDraw.Draw(self.img_one_channel).rectangle((2, 106, 67, 136), fill=self.back_color1)   # erase sens/calc
            ImageDraw.Draw(self.img_one_channel).text((2, 106), self.sens_and_calc_text[int(self.show_calc_val)], font = self.font_regular_medium, fill = self.text_color2) # draw sens/calc
            if self.show_calc_val: self.calc_shown_prev_time = True
            else: self.calc_shown_prev_time=False
        else: pass

        if channel != self.last_shown_single_channel: # means whenever changed to this channel (first frame that will be shown after changing to this channel) 
            ImageDraw.Draw(self.img_one_channel).rectangle((36, 56, 52, 86), fill=self.back_color1)       # erase channel number
            ImageDraw.Draw(self.img_one_channel).rectangle((9, 3, 320, 22), fill=self.back_color1)       # erase description
            ImageDraw.Draw(self.img_one_channel).rectangle((9, 145, 320, 171), fill=self.back_color1)    # erase ranges info
            ImageDraw.Draw(self.img_one_channel).rectangle((9, 18, 320, 51), fill=self.back_color1)      # erase label
            self.last_shown_single_channel = channel
            text_to_draw = "" + self.cfg['channels_config'][self.last_shown_single_channel]['description']
            ImageDraw.Draw(self.img_one_channel).text((9, 3), text_to_draw, font = self.font_regular_smallest, fill = self.text_color1)          # draw description
            fivetimes_inv_gain = "{:.1f}".format(5*self.pga_inv[channel]) 
            text_to_draw = "Sensor:" + str(self.cfg['channels_config'][self.last_shown_single_channel]['min_voltage']) + "-" + str(self.cfg['channels_config'][self.last_shown_single_channel]['max_voltage']) + "V ADC:0-" + fivetimes_inv_gain + "V PGA:" + str(self.pga[channel]) + "x"
            ImageDraw.Draw(self.img_one_channel).text((9, 146), text_to_draw, font = self.font_regular_smallest, fill = self.text_color1)        # draw ranges info
            text_to_draw = str(self.cfg['channels_config'][self.last_shown_single_channel]['label'])
            ImageDraw.Draw(self.img_one_channel).text((9, 18), text_to_draw, font = self.font_regular_medium, fill = self.text_color1)       # draw label
            ImageDraw.Draw(self.img_one_channel).text((36, 56), str(channel), font = self.font_bold_medium, fill = self.design_color1) # draw channel number
        
        else: # whenever last call was with same channel (just value needs to be updated)    
            ImageDraw.Draw(self.img_one_channel).rectangle((74, 54, 320, 130), fill=self.back_color1) # erase (old) value
            if not self.show_calc_val:
                text_to_draw = "{:.3f}".format(value)
                valueAsText_parts = text_to_draw.split('.')
                ImageDraw.Draw(self.img_one_channel).text((76, 52), valueAsText_parts[0], font = self.font_regular_largest, fill = self.text_color1)              # draw digit before decimal point 
                ImageDraw.Draw(self.img_one_channel).text((76 + self.em_dash_width_largest - 12, 52), ".", font = self.font_regular_largest, fill = self.text_color1)                          # draw decimal point
                ImageDraw.Draw(self.img_one_channel).text((76 + 2*(self.em_dash_width_largest - 12), 52), valueAsText_parts[1] + "V", font = self.font_regular_largest, fill = self.text_color1)    # draw digits after decimal point and also unit

                # #next lines are commented, can help alignment of the decimal dot when you change the font and want to adjust the code
                # ImageDraw.Draw(self.img_one_channel).line([(0, 52),(320, 52)], fill = self.design_color1, width = 1) 
                # ImageDraw.Draw(self.img_one_channel).line([(0, 52+68),(320, 52+68)], fill = self.design_color1, width = 1) 
                # for i in range(0,7):
                #     if i>1: i = i-0.55
                #     ImageDraw.Draw(self.img_one_channel).line([(76 + (i*self.em_dash_width_largest), 52),(76+ (i*self.em_dash_width_largest), 52+68)], fill = self.design_color1, width = 1)
            
            else: # here value is calculated using the coefficients from config
                coeffs = self.cfg['channels_config'][channel]['calc']['coefficients']
                decdigits = self.cfg['channels_config'][channel]['calc']['digits_after_decimal_point']
                unit = str(self.cfg['channels_config'][channel]['calc']['unit'])
                inverse_value = 1/value if value !=0 else 1000000 # "else" a relatively big number, value near zero means inverse is very large number. Smallest sampled value can be 4.77*10^(-6)V after 8x gain. Inverse of it is around 200k: a million is here a big number
                text_to_draw = "{:.{decdigits}f}".format(coeffs[-1]*inverse_value + coeffs[0] + coeffs[1]*value, decdigits=str(decdigits))    # calculation(transformation) of the value happens here
                if "." in text_to_draw:
                    valueAsText_parts = text_to_draw.split('.')
                    digits_before_decimal = len(valueAsText_parts[0])
                    pixels_before_decimal =  digits_before_decimal*self.em_dash_width_largest              
                    ImageDraw.Draw(self.img_one_channel).text((76, 52), valueAsText_parts[0], font = self.font_regular_largest, fill = self.text_color1)              # draw digits before decimal point 
                    ImageDraw.Draw(self.img_one_channel).text((76 + pixels_before_decimal - 12, 52), ".", font = self.font_regular_largest, fill = self.text_color1)                          # draw decimal point
                    ImageDraw.Draw(self.img_one_channel).text((76 + pixels_before_decimal - 12 + self.em_dash_width_largest - 12, 52), valueAsText_parts[1], font = self.font_regular_largest, fill = self.text_color1)    # draw digits after decimal point 
                    ImageDraw.Draw(self.img_one_channel).text((76 + pixels_before_decimal - 12 + (decdigits + 1)*self.em_dash_width_largest - 12, 52), unit, font = self.font_regular_largest, fill = self.text_color1)               # draw unit

                    #next lines are commented, can help alignment of the decimal dot when you change the font and want to adjust the code
                    # ImageDraw.Draw(self.img_one_channel).line([(0, 52),(320, 52)], fill = self.design_color1, width = 1) 
                    # ImageDraw.Draw(self.img_one_channel).line([(0, 52+68),(320, 52+68)], fill = self.design_color1, width = 1)          
                    # for i in range(0,7):
                    #     if i>digits_before_decimal: i = i-0.55
                    #     ImageDraw.Draw(self.img_one_channel).line([(76 + (i*self.em_dash_width_largest), 52),(76+ (i*self.em_dash_width_largest), 52+68)], fill = self.design_color1, width = 1)

                else:
                    ImageDraw.Draw(self.img_one_channel).text((76, 52), text_to_draw, font = self.font_regular_largest, fill = self.text_color1)
                    ImageDraw.Draw(self.img_one_channel).text((76 + len(text_to_draw)*self.em_dash_width_largest, 52), unit, font = self.font_regular_largest, fill = self.text_color1)


        self.__mode = 10 + channel
        self.last_shown_single_channel = channel
        self.img_to_show_next = self.img_one_channel.rotate(angle=270, expand=1)
        return time.time()-start_time_of_this_call
    
    def draw_one_graph(self, channel, value):
        ch_minus_one = channel - 1
        y = int(11 + value * self.pga[channel] * 30) # 11 is the the y pixel coordinate for the graphs zero line, v is the current value, max y about 11+5*30=165 
        ImageDraw.Draw(self.imgs_plots[channel]).rectangle((6,39, 164, 281), fill=self.back_color1) # erase plot
        
        if self.last_drawn_plot_channel == channel:
            for i in range(0,480-2,2):
                self.points_flat[ch_minus_one][i]=self.points_flat[ch_minus_one][i+2]
        else:
            for i in range(0,480-2,2):
                self.points_flat[ch_minus_one][i] = 11  # resets points_flat y values to 11
            ImageDraw.Draw(self.labeltmpimg).rectangle((0, 32, 42, 172), fill=self.back_color1)
            for i in range(0,5): 
                ImageDraw.Draw(self.labeltmpimg).text((0, 152 - i*30), "{:.2f}".format(i*self.pga_inv[channel]), font = self.font_regular_smallest, fill = self.text_color2)
            self.imgs_plots[channel].paste(self.labeltmpimg.rotate(angle=270, expand=1), (6, 0))

        self.points_flat[ch_minus_one][478] = y                
        
        #draw the plot for channel
        for c in self.active_channels:
            ImageDraw.Draw(self.imgs_plots[channel]).line(self.points_flat[c-1], fill=self.text_color1, width=2)

        #horizontal lines and pga adjusted labels for vertical axis (5 horizontal lines will also be drawn)
        for i in range(0,6): 
            ImageDraw.Draw(self.imgs_plots[channel]).line([(11 + i*30, 40),(11 + i*30, 300)], fill = self.design_color2, width = 1)
        
        #draw and paste little box on top right corner with channel and current numeric value
        ImageDraw.Draw(self.labeltmpimg2).rectangle((0,0,60,40), fill=self.back_color1)
        ImageDraw.Draw(self.labeltmpimg2).multiline_text((0,0), " CH " + str(channel) + "\n" + str(value), fill = self.text_color1, font=self.font_regular_smallest)
        self.imgs_plots[channel].paste(self.labeltmpimg2.rotate(angle=270, expand=1), (120,260))
        
        self.last_drawn_plot_channel = channel
        self.img_to_show_next=self.imgs_plots[channel]

    def display_qr(self, img):
        #self.LCD.clear()
        self.qr_img = Image.new("RGB", (172,320), self.back_color1)
        self.qr_img.paste(img, (0,0))
        self.img_to_show_next=self.qr_img
        self.__mode = 40 
        return