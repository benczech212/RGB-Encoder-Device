import time
import board
import neopixel

PIXEL_PIN = board.D13
NUM_PIXELS = 3
BRIGHTNESS = 0.5

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.RGBW
)

def wheel(pos):
    # Return (R, G, B) for a given position on the color wheel
    # if pos < 0 or pos > 255:
    pos %= 256
    while pos < 0:
        pos += 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)
tick_count = 0
while True:
    
    r, g, b = wheel(tick_count)
    
    pixels[0] = (r, 0, 0, 0)  # Only red component
    pixels[1] = (0, g, 0, 0)  # Only green component
    pixels[2] = (0, 0, b, 0)  # Only blue component
    
    pixels.show()
    
