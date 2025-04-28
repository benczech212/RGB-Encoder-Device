import time
import board
import displayio
import terminalio
import neopixel
from adafruit_display_text import label
from fourwire import FourWire
from adafruit_st7789 import ST7789

from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import rotaryio, digitalio
from adafruit_seesaw.neopixel import NeoPixel as SeesawNeoPixel

# --- Encoder Setup ---
ENCODER_I2C_ADDRESS = 0x37  # Red encoder
ENCODER_NEOPIXEL_PIN = 6
BUTTON_PIN = 24
MAX_ENCODER_VALUE = 50

# --- NeoPixel Strip Setup ---
pixel_pin = board.A3
num_pixels = 3
ORDER = neopixel.GRBW
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=1.0, auto_write=False, pixel_order=ORDER)

def update_led_strip(r, g, b):
    pixels[0] = (r, 0, 0, 0)
    pixels[1] = (0, g, 0, 0)
    pixels[2] = (0, 0, b, 0)
    pixels.show()

# --- I2C, Encoder, Display Setup ---
i2c = board.I2C()
ss = Seesaw(i2c, addr=ENCODER_I2C_ADDRESS)
encoder = rotaryio.IncrementalEncoder(ss)
ss.pin_mode(BUTTON_PIN, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, BUTTON_PIN)
encoder_pixel = SeesawNeoPixel(ss, ENCODER_NEOPIXEL_PIN, 1)
encoder_pixel.brightness = 0.4

displayio.release_displays()
spi = board.SPI()
tft_cs = board.D5
tft_dc = board.D6
tft_rst = board.D9

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)
display = ST7789(display_bus, width=320, height=172, colstart=34, rotation=270)
screen_width = 320
screen_height = 172

class Menu:
    def __init__(self, display_group):
        self.group = display_group

    def update(self):
        pass

class RawRGBMenu(Menu):
    def __init__(self, display_group):
        super().__init__(display_group)
        self.last_r_pos = encoder.position
        self.r_value = 0
        self.g_value = 127
        self.b_value = 255
        self.last_heights = [0, 0, 0]

        self.bar_width = screen_width // 3
        self.bar_area_height = int(screen_height * 0.75)

        self.palettes = []
        self.bar_bitmaps = []
        self.bar_tilegrids = []

        colors = [0xFF0000, 0x00FF00, 0x0000FF]
        for i in range(3):
            palette = displayio.Palette(2)
            palette[0] = 0x000000
            palette[1] = colors[i]
            self.palettes.append(palette)

            bitmap = displayio.Bitmap(self.bar_width, self.bar_area_height, 2)
            self.bar_bitmaps.append(bitmap)

            tilegrid = displayio.TileGrid(
                bitmap,
                pixel_shader=palette,
                x=i * self.bar_width,
                y=screen_height - self.bar_area_height
            )
            self.bar_tilegrids.append(tilegrid)
            self.group.append(tilegrid)

        self.preview_palette = displayio.Palette(1)
        self.preview_palette[0] = 0x000000
        self.preview_bitmap = displayio.Bitmap(screen_width, 20, 1)
        self.preview_tile = displayio.TileGrid(self.preview_bitmap, pixel_shader=self.preview_palette, x=0, y=0)
        self.group.append(self.preview_tile)

        self.labels = []
        for i, val in enumerate([self.r_value, self.g_value, self.b_value]):
            lbl_bg = displayio.Bitmap(self.bar_width, 20, 1)
            bg_palette = displayio.Palette(1)
            bg_palette[0] = 0x000000
            bg_tile = displayio.TileGrid(
                lbl_bg,
                pixel_shader=bg_palette,
                x=i * self.bar_width,
                y=screen_height - 22
            )
            self.group.append(bg_tile)

            lbl = label.Label(
                terminalio.FONT,
                text="000",
                color=0xFFFFFF,
                scale=2,
                anchor_point=(0.5, 0.5),
                anchored_position=(
                    int((i + 0.5) * self.bar_width),
                    screen_height - 12
                ),
            )
            self.labels.append(lbl)
            self.group.append(lbl)

        self.update_bars()

    def update_bars(self):
        values = [self.r_value, self.g_value, self.b_value]
        for i in range(3):
            height = int((values[i] / 255) * self.bar_area_height)
            bitmap = self.bar_bitmaps[i]
            old_height = self.last_heights[i]

            if height > old_height:
                for y in range(self.bar_area_height - height, self.bar_area_height - old_height):
                    for x in range(self.bar_width):
                        bitmap[x, y] = 1
            elif height < old_height:
                for y in range(self.bar_area_height - old_height, self.bar_area_height - height):
                    for x in range(self.bar_width):
                        bitmap[x, y] = 0

            self.last_heights[i] = height
            self.labels[i].text = f"{values[i]:03}"

        rgb = (self.r_value << 16) | (self.g_value << 8) | self.b_value
        self.preview_palette[0] = rgb
        update_led_strip(self.r_value, self.g_value, self.b_value)

    def update(self):
        raw_pos = -encoder.position
        delta = abs(raw_pos - self.last_r_pos)

        if delta > 10:
            raw_pos = self.last_r_pos

        pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))
        if pos != self.last_r_pos:
            self.r_value = int((pos / MAX_ENCODER_VALUE) * 255)
            encoder_pixel.fill((self.r_value, 0, 0))
            self.update_bars()
            self.last_r_pos = pos

main_group = displayio.Group()
display.root_group = main_group
current_menu = RawRGBMenu(main_group)

while True:
    current_menu.update()

    if not button.value:
        print("Encoder button pressed!")

    time.sleep(0.05)