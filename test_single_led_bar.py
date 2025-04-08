import time
import board
import neopixel

# --- Configuration ---
PIXEL_PIN = board.D9
NUM_PIXELS = 8
BRIGHTNESS = 0.4

# Create the NeoPixel object
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS, auto_write=False)

# --- Basic Test Loop ---
def color_chase(color, delay=0.1):
    for i in range(NUM_PIXELS):
        pixels[i] = color
        pixels.show()
        time.sleep(delay)
    time.sleep(0.5)
    pixels.fill((0, 0, 0))
    pixels.show()

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(NUM_PIXELS):
            rc_index = (i * 256 // NUM_PIXELS + j) & 255
            pixels[i] = wheel(rc_index)
        pixels.show()
        time.sleep(wait)

def wheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

# --- Run Tests ---
while True:
    color_chase((255, 0, 0))   # Red
    color_chase((0, 255, 0))   # Green
    color_chase((0, 0, 255))   # Blue
    rainbow_cycle(0.01)
