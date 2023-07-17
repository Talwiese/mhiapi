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
        
        self.font4Description = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['smallest'])
        self.font4ValueSmall = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['small'])
        self.font4ChannelNumber = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['medium'])
        self.font4ValueLarge = ImageFont.truetype(self.cfg['display']['fontpaths']['SourceCodeProRegular'], self.cfg['display']['fontsizes']['largest'])
        self.font4Icons = ImageFont.truetype(self.cfg['display']['fontpaths']['FontAwesomeFreeRegular'], self.cfg['display']['fontsizes']['largest'])
        
        # The next block with the tuples on the right side could be somehow moved into mhiacfg, so that the color values are already loaded as tuples here.
        self.back_color1 = tuple(self.cfg['display']['back_color'])
        self.back_color2 = tuple(self.cfg['display']['back_color2'])
        self.text_color = tuple(self.cfg['display']['text_color'])
        self.design_color1 = tuple(self.cfg['display']['design_color1'])
        self.design_color2 = tuple(self.cfg['display']['design_color2'])
        self.text_color_less_visible = tuple(self.cfg['display']['text_color_less_visible'])

        #Creating object and initializing it using the Waveshare module
        SPI_BUS = self.cfg['display']['hw_settings']['spi_bus']
        SPI_DEVICE = self.cfg['display']['hw_settings']['spi_device']
        SPI_FREQ = self.cfg['display']['hw_settings']['spi_freq']
        RST= self.cfg['display']['hw_settings']['reset_pin']
        DC = self.cfg['display']['hw_settings']['command_pin']
        BL = self.cfg['display']['hw_settings']['backlight_pin']
        BL_FREQ = self.cfg['display']['hw_settings']['backlight_freq']
        self.disp = LCD_1inch47.LCD_1inch47(spi=spidev.SpiDev(SPI_BUS, SPI_DEVICE),spi_freq=SPI_FREQ,rst=RST,dc=DC,bl=BL, bl_freq=BL_FREQ, i2c=None)

        #self.disp.bl_DutyCycle(100) # between 0 and 100, flickrs more likely at low values, would need another bcm2835 driver apparently

        #Creating the base images to be shown on the display
        self.portraitAllCh = Image.new("RGB", (172, 320), self.back_color1)
        self.landscapeOneCh = Image.new("RGB", (320,172), self.back_color1)
 
        self.qr_img = Image.new("RGB", (172,320), self.back_color1)
        self.labeltmpimg = Image.new("RGB", (12,172), self.back_color1) # this is for 
        self.labeltmpimg2 = Image.new("RGB", (60,40), self.back_color1)
        self.landscapeGraph = {}
        for channel in self.cfg['active_channels']:
            self.landscapeGraph[channel] = Image.new("RGB", (172,320), self.back_color1) # this is drawn rotated from beginning, so no img.rotate needed later

        self.__mode = 11 # setting the mode of display, 11 means show channel 1 (second digit) in landscape mode (first digit) 

        # this little block prepares lists to hold the points of the diagramm for each channel 
        self.lastx = [40] * 8 # last y and last x are the coordinates of the current value in graph mode, here beginning is set. 40 is vertical zero
        self.lasty = [11] * 8 # 11 is the horizontal zero
        self.xs = range(40,280,1)   # is [40, 42, ..., 276, 278] the indices are [0, 1, ..., 119]
        self.points_flat = [[11] * 480] * 8 # a 2d-array of 8 channels, each contains 240 time the value 11. 
        for j in range(0,8):
            for i in range(0,240):
                self.points_flat[j][i*2+1]=self.xs[i]
            #(self.lasty[j], self.lastx[j]) = (11,40)  
        self.counter_for_graph = 0  

        #self.__connected_wifi_symbol = False

        self.sens_and_calc_text = ["sensor output", "calculated"]
        (self.show_calc_val, self.calc_shown_prev_time)  = (False, True) # this assignment is necessary for the beginning

        # prepare background image for landscape mode
        self.lastShownSingleChannel = 0 # not lastShown channel but it is set to 0 (= no channel) at startup
        ImageDraw.Draw(self.landscapeOneCh).line([(0, 30),(320, 30)], fill = self.design_color1, width = 1) # top margin
        ImageDraw.Draw(self.landscapeOneCh).line([(0, 142),(320, 142)], fill = self.design_color1, width = 1) # bottom margin
        ImageDraw.Draw(self.landscapeOneCh).line([(50, 30),(50, 142)], fill = self.design_color1, width = 1) # left margin
        ImageDraw.Draw(self.landscapeOneCh).text((6, 56), "CH", font = self.font4ChannelNumber, fill = self.design_color1)

        # prepare background for portrait mode
        for j in range(0,9):
            back_color_dyn = self.back_color1 if j%2 == 1 else self.back_color2
            ImageDraw.Draw(self.portraitAllCh).rectangle((0, 0 + j*36 - 4, 172, (j+1)*36 - 4), fill=back_color_dyn)
        for j in range(1,9):
            ImageDraw.Draw(self.portraitAllCh).text((8, (j*36 - 1)), str(j), font = self.font4ValueSmall, fill = self.design_color1)
        ImageDraw.Draw(self.portraitAllCh).line([(0, 32),(172, 32)], fill = self.design_color1, width = 2) # header border
        ImageDraw.Draw(self.portraitAllCh).line([(32, 0),(32, 320)], fill = self.design_color1, width = 1) # channel border

        # prepares background for graph mode
        self.lastChannelShownOnGraph = 0
        for channel in self.cfg['active_channels']:
            ImageDraw.Draw(self.landscapeGraph[channel]).line([(9, 39),(9, 300)], fill = self.design_color1, width = 2) # zero line, time axis
            ImageDraw.Draw(self.landscapeGraph[channel]).line([(9, 39),(161, 39)], fill = self.design_color1, width = 2) # zero line, value axis
            #ImageDraw.Draw(self.landscapeGraph['channel']).text((292, 0), "D", font = self.font4Icons, fill = self.text_color)
        # next the vertical axis of the graph is drawn
            for i in range(0,5): 
                ImageDraw.Draw(self.labeltmpimg).text((0, 152 - i*30), str(i), font = self.font4Description, fill = self.design_color1)
            ImageDraw.Draw(self.labeltmpimg).text((0, 4), "V", font = self.font4Description, fill = self.design_color1)
            self.landscapeGraph[channel].paste(self.labeltmpimg.rotate(angle=270, expand=1), (6,26))

        self.disp.Init()
        self.disp.clear()

        self.img_to_show_next = self.portraitAllCh

        self.active_channels = self.cfg['active_channels']

    # def getwifi_symbol(self):
    #     return self.__connected_wifi_symbol
    
    # def setwifi_symbol(self, enable_now):        
    #     if self.__connected_wifi_symbol and not enable_now:
    #         ImageDraw.Draw(self.landscapeOneCh).rectangle((292, 0, 320, 28 ), fill=self.back_color1)
    #         ImageDraw.Draw(self.landscapeOneCh).text((292, 0), "F", font = self.font4Icons, fill = self.text_color_less_visible) 
    #         self.__connected_wifi_symbol = False      
    #     elif not self.__connected_wifi_symbol and enable_now:
    #         ImageDraw.Draw(self.landscapeOneCh).rectangle((292, 0, 320, 28 ), fill=self.back_color1)
    #         ImageDraw.Draw(self.landscapeOneCh).text((292, 0), "D", font = self.font4Icons, fill = self.text_color)
    #         self.__connected_wifi_symbol = True            
    #     else: pass

    def getmode(self):
        return self.__mode
    
    def setmode(self, mode):
        self.__mode=mode

    def show_all_channels(self, channel, value):
        start_time_of_this_call = time.time()    
        i = channel - 1 + 1 # the first i with index 0 is for the header-info on the display
        text_to_show = "{:.3f}".format(value) + "V"
        back_color_dyn = self.back_color1 if i%2 == 1 else self.back_color2 #to have alternating backgrounds for each line (channel)
        ImageDraw.Draw(self.portraitAllCh).rectangle((33, i*36 - 2, 172, (i+1)*36 - 4), fill=back_color_dyn) #draws an empty rectangle over the value of a channel      
        ImageDraw.Draw(self.portraitAllCh).text((44, i*36 - 1), text_to_show, font = self.font4ValueSmall, fill = self.text_color) #draws the updated value of a channel
        #self.disp.ShowImage(self.portraitAllCh)
        self.__mode = 9 # 9s stand for the mode where all channels are shown in portrait orientation
        self.img_to_show_next = self.portraitAllCh
        return time.time()-start_time_of_this_call
    
    def show_one_channel(self, channel, value):
        start_time_of_this_call = time.time()
        # XOR, if calc wanted but sens shown last time, or if sens wanted and calc shown last time.... to clear field and update field on display
        if (self.show_calc_val ^ self.calc_shown_prev_time):    
            ImageDraw.Draw(self.landscapeOneCh).rectangle((56, 32, 300, 65), fill=self.back_color1)   # clear
            ImageDraw.Draw(self.landscapeOneCh).text((56, 30), self.sens_and_calc_text[int(self.show_calc_val)], font = self.font4ChannelNumber, fill = self.design_color1)
            if self.show_calc_val: self.calc_shown_prev_time = True
            else: self.calc_shown_prev_time=False
        else: pass
        if 10 < self.__mode < 19:
            if channel != self.lastShownSingleChannel: # means whenever changed to this channel (first frame that will be shown after changing to this channel) 
                ImageDraw.Draw(self.landscapeOneCh).rectangle((20,92, 40, 116), fill=self.back_color1) # erase channel number
                ImageDraw.Draw(self.landscapeOneCh).rectangle((9, 3, 320, 22), fill=self.back_color1) # erase description
                ImageDraw.Draw(self.landscapeOneCh).rectangle((9, 145, 320, 171), fill=self.back_color1) # erase ranges info
                self.lastShownSingleChannel = channel
                text2draw = "Descr.: " + self.cfg['channels_config'][self.lastShownSingleChannel]['description']
                ImageDraw.Draw(self.landscapeOneCh).text((9, 3), text2draw, font = self.font4Description, fill = self.text_color)
                fivetimes_inv_gain = "{:.1f}".format(5 / float(self.cfg['adc_gain'])) 
                text2draw = "Sensor:0-" + str(self.cfg['channels_config'][self.lastShownSingleChannel]['max_voltage']) + "V ADC:0-" + str(fivetimes_inv_gain) + "V PGA:" + str(self.cfg['adc_gain']) + "x"
                ImageDraw.Draw(self.landscapeOneCh).text((9, 142), text2draw, font = self.font4Description, fill = self.text_color) 
            else: # whenever show_one_channel is called with same channel as previous call
                ImageDraw.Draw(self.landscapeOneCh).text((21, 84), str(channel), font = self.font4ChannelNumber, fill = self.design_color1)
                ImageDraw.Draw(self.landscapeOneCh).rectangle((56, 66, 320, 118), fill=self.back_color1) # erase (old) value
                if not self.show_calc_val:
                    text_to_show = "{:.3f}".format(value) + "V"
                else: # here value is calculated using the coefficients from config
                    coeffs = self.cfg['channels_config'][channel]['calc']['coefficients']
                    decdigits = str(self.cfg['channels_config'][channel]['calc']['digits_after_decimal_point'])
                    unit = self.cfg['channels_config'][channel]['calc']['unit']
                    inverse_value = 1/value if value !=0 else 0 # "else" something else than 0 would be better, value near zero means inverse is a very big
                    text_to_show = "{:.{decdigits}f}".format(coeffs[-1]*inverse_value + coeffs[0] + coeffs[1]*value, decdigits=decdigits) + unit    # calculation(transformation) of the value happens here
                ImageDraw.Draw(self.landscapeOneCh).text((56, 56), text_to_show, font = self.font4ValueLarge, fill = self.text_color)   # draw new value including Unit 
        else: # the first call of show_one_channel when changing to display mode between 10 and 19
            text_to_show3 = "Description: " + self.cfg.get['channels_config'][channel]['description']
            ImageDraw.Draw(self.landscapeOneCh).text((9, 3), text_to_show3, font = self.Font1, fill = self.text_color)
            text_to_show2 = "Sensing range: 0 to " + str(self.cfg.get('channels_config').get(channel).get('max_value')) + " " + self.cfg.get('channels_config').get(channel).get('unit')
            ImageDraw.Draw(self.landscapeOneCh).text((9, 142), text_to_show2, font = self.Font1, fill = self.text_color)        
        #self.disp.ShowImage(self.landscapeOneCh.rotate(angle=270, expand=1))
        self.__mode = 10 + channel
        self.lastShownSingleChannel = channel
        self.img_to_show_next = self.landscapeOneCh.rotate(angle=270, expand=1)
        return time.time()-start_time_of_this_call
    
    def show_one_graph(self, channel, v):
        #print("call " + str(channel))
        ch_minus_one = channel - 1
        y = int(11 + v * 30) # 11 is the the y pixel coordinate for the graphs zero line, v is the current value, max y about 11+5*30=165 
        ImageDraw.Draw(self.landscapeGraph[channel]).rectangle((11,40, 162, 281), fill=self.back_color1) # erase graph
        if self.lastChannelShownOnGraph == channel:
            for i in range(0,480-2,2):
                self.points_flat[ch_minus_one][i]=self.points_flat[ch_minus_one][i+2]
        else:
            for i in range(0,480-2,2):
                self.points_flat[ch_minus_one][i] = 11  # resets points_flat y values to 11, 
        self.points_flat[ch_minus_one][478] = y                
        
        for c in self.active_channels:
            ImageDraw.Draw(self.landscapeGraph[channel]).line(self.points_flat[c-1], fill=self.text_color, width=2)
            #print("draw")

        ImageDraw.Draw(self.landscapeGraph[channel]).line([(41, 40),(41, 300)], fill = self.design_color2, width = 2)
        ImageDraw.Draw(self.landscapeGraph[channel]).line([(71, 40),(71, 300)], fill = self.design_color2, width = 2)
        ImageDraw.Draw(self.landscapeGraph[channel]).line([(101, 40),(101, 300)], fill = self.design_color2, width = 2)
        ImageDraw.Draw(self.landscapeGraph[channel]).line([(131, 40),(131, 300)], fill = self.design_color2, width = 2)
        ImageDraw.Draw(self.landscapeGraph[channel]).line([(161, 40),(161, 300)], fill = self.design_color2, width = 2)
        ImageDraw.Draw(self.labeltmpimg2).rectangle((0,0,60,40), fill=self.back_color1)
        ImageDraw.Draw(self.labeltmpimg2).multiline_text((0,0), " CH " + str(channel) + "\n" + str(v), fill=self.text_color, font=self.font4Description)
        self.landscapeGraph[channel].paste(self.labeltmpimg2.rotate(angle=270, expand=1), (120,250))
        self.lastChannelShownOnGraph = channel
        self.img_to_show_next=self.landscapeGraph[channel]

    def wifi_symbol(self, enabled):
        symb_to_show = "D" if enabled else "F"
        img = Image.new("RGB", (28,28), self.back_color1)
        ImageDraw.Draw(img).text((0, 0), symb_to_show, font = self.Font5, fill = self.text_color)
        self.landscapeOneCh.paste(img, (290, 0))
        #self.disp.ShowImage(self.landscapeOneCh.rotate(angle=270, expand=1))

    def blink(self, enabled):
        symb_to_show = "•"
        img = Image.new("RGB", (28,28), self.back_color1)
        ImageDraw.Draw(img).text((0, 0), symb_to_show, font = self.Font, fill = self.text_color)
        self.landscapeOneCh.paste(img, (260, 0))
        self.disp.ShowImage(self.landscapeOneCh.rotate(angle=270, expand=1))
        img = Image.new("RGB", (28,28), self.back_color1)
        self.landscapeOneCh.paste(img, (260, 0))

    def display_qr(self, img):
        #self.disp.clear()
        self.qr_img = Image.new("RGB", (172,320), self.back_color1)
        self.qr_img.paste(img, (0,0))
        self.img_to_show_next=self.qr_img
        self.__mode = 40 
        return