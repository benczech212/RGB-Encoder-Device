import time
import board
import neopixel
import busio
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import rotaryio, digitalio
from adafruit_seesaw.neopixel import NeoPixel as SeesawNeoPixel

# --- CONFIG ---
I2C_ADDRESS = 0x37           # Red encoder (A0 closed)
ENCODER_PIXEL_PIN = 6        # On the encoder board
ENCODER_BUTTON_PIN = 24
MAX_ENCODER_VALUE = 50
NEOPIXEL_PIN = board.D9      # External NeoPixel bar
NUM_PIXELS = 9               # 8 trail + 1 accent
DELAY_BETWEEN_PIXELS = 0.1   # Delay per step (seconds)

# --- Setup I2C + Encoder ---
i2c = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c, addr=I2C_ADDRESS)

encoder = rotaryio.IncrementalEncoder(ss)
ss.pin_mode(ENCODER_BUTTON_PIN, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, ENCODER_BUTTON_PIN)

encoder_pixel = SeesawNeoPixel(ss, ENCODER_PIXEL_PIN, 1)
encoder_pixel.brightness = 0.4

# --- Setup NeoPixel bar ---
strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=0.4, auto_write=False)

# --- Trail buffer ---
value_trail = [0] * 8  # last 8 encoder-derived values
last_shift_time = time.monotonic()
last_position = encoder.position

while True:
    raw_pos = -encoder.position  # Negate for CW = increase
    delta = abs(raw_pos - last_position)

    # Ignore glitchy jumps
    if delta > 10:
        raw_pos = last_position

    pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))
    red_val = int((pos / MAX_ENCODER_VALUE) * 255)

    # Update encoder pixel live
    encoder_pixel.fill((red_val, 0, 0))

    now = time.monotonic()
    if now - last_shift_time >= DELAY_BETWEEN_PIXELS:
        value_trail.insert(0, red_val)  # push new value
        value_trail.pop()               # keep buffer size at 8
        last_shift_time = now

        # Update strip
        strip.fill((0, 0, 0))
        for i in range(8):
            strip[i] = (value_trail[i], 0, 0)

        # Bright cursor on pixel 8
        strip[8] = (min(255, red_val + 40), 20, 20)
        strip.show()

    # Optional: flash everything on button press
    if not button.value:
        print("Button pressed!")
        encoder_pixel.fill((255, 255, 255))
        strip.fill((255, 255, 255))
        strip.show()
        time.sleep(0.2)
        encoder_pixel.fill((red_val, 0, 0))
        for i in range(8):
            strip[i] = (value_trail[i], 0, 0)
        strip[8] = (min(255, red_val + 40), 20, 20)
        strip.show()

    last_position = raw_pos
    time.sleep(0.01)
