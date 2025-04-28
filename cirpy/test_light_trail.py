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

# LED pins and counts
R_PIXEL_PIN = board.D10
G_PIXEL_PIN = board.D12
B_PIXEL_PIN = board.D11
CURSOR_STRIP_PIN = board.A3

NUM_TRAIL_PIXELS = 8
CURSOR_PIXEL_COUNT = 1       # Single-pixel cursor for now
DELAY_BETWEEN_PIXELS = 0.1   # Delay per step (seconds)

# --- Setup I2C + Encoder ---
i2c = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c, addr=I2C_ADDRESS)

encoder = rotaryio.IncrementalEncoder(ss)
ss.pin_mode(ENCODER_BUTTON_PIN, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, ENCODER_BUTTON_PIN)

encoder_pixel = SeesawNeoPixel(ss, ENCODER_PIXEL_PIN, 1)
encoder_pixel.brightness = 0.4

# --- Setup RGB trail strips ---
r_strip = neopixel.NeoPixel(R_PIXEL_PIN, NUM_TRAIL_PIXELS, brightness=0.4, auto_write=False)
g_strip = neopixel.NeoPixel(G_PIXEL_PIN, NUM_TRAIL_PIXELS, brightness=0.4, auto_write=False)
b_strip = neopixel.NeoPixel(B_PIXEL_PIN, NUM_TRAIL_PIXELS, brightness=0.4, auto_write=False)

# --- Cursor strip ---
cursor_strip = neopixel.NeoPixel(CURSOR_STRIP_PIN, CURSOR_PIXEL_COUNT, brightness=0.4, auto_write=True)

# --- Trail buffer ---
value_trail = [0] * NUM_TRAIL_PIXELS
last_shift_time = time.monotonic()
last_position = encoder.position

while True:
    raw_pos = -encoder.position  # Negate for CW = increase
    delta = abs(raw_pos - last_position)

    if delta > 10:
        raw_pos = last_position  # Ignore glitchy jumps

    pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))
    red_val = int((pos / MAX_ENCODER_VALUE) * 255)

    encoder_pixel.fill((red_val, 0, 0))

    now = time.monotonic()
    if now - last_shift_time >= DELAY_BETWEEN_PIXELS:
        value_trail.insert(0, red_val)
        value_trail.pop()
        last_shift_time = now

        # Update strips
        for i in range(NUM_TRAIL_PIXELS):
            r_strip[i] = (value_trail[i], 0, 0)
            g_strip[i] = (0, value_trail[i], 0)
            b_strip[i] = (0, 0, value_trail[i])

        r_strip.show()
        g_strip.show()
        b_strip.show()

        # If the last LED in the trail is non-zero, send value to cursor
        if value_trail[-1] > 0:
            cursor_color = (value_trail[-1], 0, 0)
            cursor_strip.fill(cursor_color)

    # Flash on button press
    if not button.value:
        print("Button pressed!")
        encoder_pixel.fill((255, 255, 255))
        r_strip.fill((255, 255, 255))
        g_strip.fill((255, 255, 255))
        b_strip.fill((255, 255, 255))
        cursor_strip.fill((255, 255, 255))
        r_strip.show()
        g_strip.show()
        b_strip.show()
        time.sleep(0.2)
        encoder_pixel.fill((red_val, 0, 0))
        cursor_strip.fill((value_trail[-1], 0, 0))

    last_position = raw_pos
    time.sleep(0.01)
