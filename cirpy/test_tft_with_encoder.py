# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import displayio
import terminalio
from adafruit_display_text import label
from fourwire import FourWire
from adafruit_st7789 import ST7789

from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import rotaryio, digitalio
from adafruit_seesaw.neopixel import NeoPixel as SeesawNeoPixel

# --- Encoder Configuration ---
ENCODER_I2C_ADDRESS = 0x37  # Red encoder
ENCODER_NEOPIXEL_PIN = 6
BUTTON_PIN = 24
MAX_ENCODER_VALUE = 50

# --- I2C Setup for Encoder ---
i2c = board.I2C()  # SDA=D0, SCL=D1 (Feather RP2040 default)
ss = Seesaw(i2c, addr=ENCODER_I2C_ADDRESS)

encoder = rotaryio.IncrementalEncoder(ss)
ss.pin_mode(BUTTON_PIN, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, BUTTON_PIN)
encoder_pixel = SeesawNeoPixel(ss, ENCODER_NEOPIXEL_PIN, 1)
encoder_pixel.brightness = 0.4

# --- Display Setup (from working reference code) ---
displayio.release_displays()
spi = board.SPI()
tft_cs = board.D5
tft_dc = board.D6
tft_rst = board.D9

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)
display = ST7789(display_bus, width=320, height=172, colstart=34, rotation=270)

# --- Display Drawing ---
splash = displayio.Group()
display.root_group = splash

# Color fill square
color_box = displayio.Bitmap(100, 100, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x000000  # Start with black
color_tile = displayio.TileGrid(color_box, pixel_shader=color_palette, x=110, y=30)
splash.append(color_tile)

# Label for Red value
text_label = label.Label(
    terminalio.FONT,
    text="R: 0",
    color=0xFFFFFF,
    scale=3,
    anchor_point=(0, 0),
    anchored_position=(10, 10),
)
splash.append(text_label)

# --- Encoder Reading Loop ---
last_position = encoder.position

while True:
    raw_pos = -encoder.position  # CW = positive
    delta = abs(raw_pos - last_position)

    # Glitch filter
    if delta > 10:
        print(f"Ignored glitch: Δ={delta}")
        raw_pos = last_position

    pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))

    if pos != last_position:
        red = int((pos / MAX_ENCODER_VALUE) * 255)
        encoder_pixel.fill((red, 0, 0))

        # Update TFT
        text_label.text = f"R: {red}"
        color_palette[0] = (red << 16)  # RGB 0xRRGGBB

        print(f"Encoder pos: {pos} → red={red}")
        last_position = pos

    if not button.value:
        print("Encoder button pressed!")

    time.sleep(0.05)
