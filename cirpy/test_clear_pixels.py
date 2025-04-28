import time
import board
import busio
import neopixel
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import rotaryio, digitalio
from adafruit_seesaw.neopixel import NeoPixel as SeesawNeoPixel

# ---- CONFIG ----
I2C_ADDRESS = 0x37         # Red encoder (A0 closed)
NEOPIXEL_PIN_PI = board.D18
NUM_STRIP_PIXELS = 9       # 8 for trail, 1 for cursor
ENCODER_NEOPIXEL_PIN = 6
BUTTON_PIN = 24
MAX_ENCODER_VALUE = 50
MAX_ENCODER_DELTA = 50
DELAY_BETWEEN_PIXELS = 0.1  # Seconds between value shifts in the LED trail

# ---- External NeoPixel strip (on Pi) ----
strip = neopixel.NeoPixel(
    NEOPIXEL_PIN_PI, NUM_STRIP_PIXELS, brightness=1.0, auto_write=False
)

# ---- I2C Setup ----
i2c = board.I2C()
ss = Seesaw(i2c, I2C_ADDRESS)

# ---- Encoder Setup ----
encoder = rotaryio.IncrementalEncoder(ss)
last_position = encoder.position

# ---- Button Setup ----
ss.pin_mode(BUTTON_PIN, ss.INPUT_PULLUP)
switch = digitalio.DigitalIO(ss, BUTTON_PIN)

# ---- Encoder NeoPixel Setup ----
encoder_pixel = SeesawNeoPixel(ss, ENCODER_NEOPIXEL_PIN, 1)
encoder_pixel.brightness = 0.5

# ---- Initialize Trail Buffer ----
value_trail = [0] * 8
last_shift_time = time.monotonic()

# ---- Main Loop ----
while True:
    # --- Get current encoder value ---
    raw_pos = -encoder.position
    delta = abs(raw_pos - last_position)

    # If the jump is too big, ignore it
    if delta > MAX_ENCODER_DELTA:
        print(f"Ignored glitch: Δ={delta}, raw={raw_pos}, last={last_position}")
        raw_pos = last_position

    pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))
    red_val = int((pos / MAX_ENCODER_VALUE) * 255)

    # --- Update encoder NeoPixel immediately ---
    encoder_pixel.fill((red_val, 0, 0))

    now = time.monotonic()
    if now - last_shift_time >= DELAY_BETWEEN_PIXELS:
        # Shift new value into the front, drop the oldest
        value_trail.insert(0, red_val)
        value_trail.pop()  # maintain buffer size
        last_shift_time = now

        # Update LED bar with delayed values
        strip.fill((0, 0, 0))
        for i in range(8):
            strip[i] = (value_trail[i], 0, 0)

        # Bright cursor
        strip[8] = (min(255, red_val + 40), 20, 20)
        strip.show()

    # --- Optional: Button Flash ---
    if not switch.value:
        print("Red button pressed!")
        encoder_pixel.fill((255, 255, 255))
        strip.fill((255, 255, 255))
        strip.show()
        time.sleep(0.2)
        encoder_pixel.fill((red_val, 0, 0))
        for i in range(8):
            strip[i] = (value_trail[i], 0, 0)
        strip[8] = (min(255, red_val + 40), 20, 20)
        strip.show()

    time.sleep(0.01)
