import time
import board
import neopixel

# Configuration
PIXEL_PIN = board.D13  # Pin D13 (GPIO13 on Feather RP2040)
NUM_PIXELS = 3         # Number of RGBW NeoPixels
BRIGHTNESS = 0.5       # Adjust brightness (0.0 to 1.0)

# Initialize the NeoPixel chain
pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.RGBW
)

# Set the colors: red, green, blue (RGBW format)
pixels[0] = (255, 0, 0, 0)  # Red
pixels[1] = (0, 255, 0, 0)  # Green
pixels[2] = (0, 0, 255, 0)  # Blue

pixels.show()

while True:
    time.sleep(1)  # Keep running
