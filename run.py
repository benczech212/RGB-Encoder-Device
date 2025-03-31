import board
import busio
import time
import neopixel
from adafruit_seesaw import seesaw, neopixel as seesaw_neopixel

# ----- CONFIG -----

I2C_ADDRESS = 0x36  # Only the R encoder for now
COLOR_ORDER = ('R', 'G', 'B')  # Adjust if needed (ex: ('G', 'R', 'B'))

# NeoPixel Strip Config
NUM_STRIP_PIXELS = 3
STRIP_PIN = board.D18  # Must be a PWM pin like GPIO18 (Pin 12 on header)

# ------------------

class ColorEncoder:
    def __init__(self, i2c, addr, color_channel, strip, strip_index):
        self.color_channel = color_channel  # 'R'
        self.strip = strip
        self.strip_index = strip_index

        # Setup Seesaw encoder
        self.encoder = seesaw.Seesaw(i2c, addr=addr)
        self.encoder.pin_mode(24, self.encoder.INPUT_PULLUP)

        # Track rotation
        self.last_position = self.encoder.encoder_position
        self.value = 128
        self.enabled = True

        # Encoder NeoPixel (on Seesaw)
        self.neo = seesaw_neopixel.NeoPixel(self.encoder, 6, 1)
        self.neo.brightness = 0.3

    def update(self):
        # Handle rotation
        position = self.encoder.encoder_position
        delta = position - self.last_position

        if delta != 0:
            self.value = max(0, min(255, self.value + delta))
            print(f"{self.color_channel} = {self.value}")
            self.last_position = position
            self.update_pixels()

        # Handle pushbutton
        if not self.encoder.digital_read(24):  # Active LOW
            self.enabled = not self.enabled
            print(f"{self.color_channel} toggle -> {'ON' if self.enabled else 'OFF'}")
            self.update_pixels()
            while not self.encoder.digital_read(24):
                time.sleep(0.01)

    def get_color(self):
        return self.value if self.enabled else 0

    def update_pixels(self):
        # Encoder Pixel Color
        rgb = [0, 0, 0]
        rgb[COLOR_ORDER.index(self.color_channel)] = self.get_color()
        self.neo[0] = tuple(rgb)

        # NeoPixel Strip Color
        self.strip[self.strip_index] = tuple(rgb)

# ----- INIT -----

# Setup I2C on Pi Zero
i2c = busio.I2C(board.SCL, board.SDA)

# NeoPixel Strip
strip = neopixel.NeoPixel(STRIP_PIN, NUM_STRIP_PIXELS, auto_write=False, pixel_order=neopixel.RGB)
strip.brightness = 0.5

# Encoder instance
r_encoder = ColorEncoder(i2c, I2C_ADDRESS, 'R', strip, 0)

# ----- LOOP -----

print("Running on Pi Zero... CTRL+C to exit.")
while True:
    r_encoder.update()
    strip.show()
    time.sleep(0.01)
