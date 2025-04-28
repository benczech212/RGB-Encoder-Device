import board
import neopixel

# Configure the NeoPixel
pixel_pin = board.D18  # Pin where the NeoPixel is connected
num_pixels = 3         # Number of NeoPixels
brightness = 0.1       # Brightness level (0.0 to 1.0)

# Initialize the NeoPixel
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=brightness, auto_write=False, pixel_order=neopixel.GRBW)

# Set the NeoPixels to colors
pixels[0] = (255, 0, 0, 0)  # Red
pixels[1] = (0, 255, 0, 0)  # Green
pixels[2] = (0, 0, 255, 0)  # Blue
pixels.show()