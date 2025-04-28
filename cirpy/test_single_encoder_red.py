import time
import board
import busio
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import rotaryio, digitalio
from adafruit_seesaw.neopixel import NeoPixel as SeesawNeoPixel

# --- Configuration ---
ENCODER_I2C_ADDRESS = 0x37  # A0 closed = Red encoder
ENCODER_NEOPIXEL_PIN = 6
BUTTON_PIN = 24
MAX_ENCODER_VALUE = 50

# --- I2C setup ---
i2c = board.I2C()  # Feather RP2040 default I2C pins: SDA=D0, SCL=D1
ss = Seesaw(i2c, addr=ENCODER_I2C_ADDRESS)

# --- Rotary encoder and button ---
encoder = rotaryio.IncrementalEncoder(ss)
last_position = encoder.position
ss.pin_mode(BUTTON_PIN, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, BUTTON_PIN)

# --- Encoder's onboard NeoPixel ---
encoder_pixel = SeesawNeoPixel(ss, ENCODER_NEOPIXEL_PIN, 1)
encoder_pixel.brightness = 0.4

while True:
    raw_pos = -encoder.position  # Negate for CW = positive
    delta = abs(raw_pos - last_position)

    # Filter out crazy jumps (likely I2C glitch)
    if delta > 10:
        print(f"Ignored glitch: Δ={delta}")
        raw_pos = last_position

    pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))

    if pos != last_position:
        red = int((pos / MAX_ENCODER_VALUE) * 255)
        encoder_pixel.fill((red, 0, 0))
        print(f"Encoder pos: {pos} → red={red}")
        last_position = pos

    # Optional: check button press
    if not button.value:
        print("Encoder button pressed!")

    time.sleep(0.05)
