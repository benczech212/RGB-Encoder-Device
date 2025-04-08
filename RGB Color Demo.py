# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import neopixel

pixel_pin = board.D9
num_pixels = 3
ORDER = neopixel.GRBW

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=1.0, auto_write=False, pixel_order=ORDER
)

def wheel(pos):
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

def split_color_to_pixels(color, pixel_ids, scale=1.0):
    r = int(color[0] * scale)
    g = int(color[1] * scale)
    b = int(color[2] * scale)
    for i in range(num_pixels):
        if i == 0:
            pixels[pixel_ids[i]] = (r, 0, 0, 0)
        elif i == 1:
            pixels[pixel_ids[i]] = (0, g, 0, 0)
        elif i == 2:
            pixels[pixel_ids[i]] = (0, 0, b, 0)
        else:
            pixels[pixel_ids[i]] = (0, 0, 0, 0)

def fade_color(color, pixel_ids, steps=50, delay=0.01):
    # Fade in
    for i in range(steps + 1):
        brightness = i / steps
        split_color_to_pixels(color, pixel_ids, brightness)
        pixels.show()
        time.sleep(delay)
    # Fade out
    for i in range(steps, -1, -1):
        brightness = i / steps
        split_color_to_pixels(color, pixel_ids, brightness)
        pixels.show()
        time.sleep(delay)

colors = [
    (255, 0, 0),    # red
    (0, 255, 0),    # green
    (0, 0, 255),    # blue
    (255, 255, 0),  # yellow
    (255, 0, 255),  # magenta
    (0, 255, 255),  # cyan
    (255, 255, 255) # white
]

pixel_ids = [0, 1, 2]

while True:
    for color in colors:
        fade_color(color, pixel_ids, steps=80, delay=0.05)
