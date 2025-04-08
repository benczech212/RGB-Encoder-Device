import time
import board
import displayio
import terminalio
import neopixel
import json
import os
from adafruit_display_text import label
from fourwire import FourWire
from adafruit_st7789 import ST7789

from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import rotaryio, digitalio
from adafruit_seesaw.neopixel import NeoPixel as SeesawNeoPixel

# --- Encoder Setup ---
ENCODER_I2C_ADDRESS = 0x37  # Red encoder
ENCODER_NEOPIXEL_PIN = 6
BUTTON_PIN = 24
MAX_ENCODER_VALUE = 50

# --- NeoPixel Strip Setup ---
# Main RGB pixel preview

# Cursor NeoPixel strip on A3
cursor_strip = neopixel.NeoPixel(board.A3, 3, brightness=1.0, auto_write=False, pixel_order=neopixel.RGBW)


# R Value Trail Strip (D10)
value_trail_pin_r = board.D10
value_trail_r = neopixel.NeoPixel(value_trail_pin_r, 8, brightness=0.4, auto_write=False)
trail_buffer_r = [0] * 8

# G Value Trail Strip (D12)
value_trail_pin_g = board.D12
value_trail_g = neopixel.NeoPixel(value_trail_pin_g, 8, brightness=0.4, auto_write=False)
trail_buffer_g = [0] * 8

# B Value Trail Strip (D11)
value_trail_pin_b = board.D11
value_trail_b = neopixel.NeoPixel(value_trail_pin_b, 8, brightness=0.4, auto_write=False)
trail_buffer_b = [0] * 8

last_trail_shift_time = time.monotonic()

def update_led_strip(r, g, b):
    if trail_buffer_r[-1] > 0 or trail_buffer_g[-1] > 0 or trail_buffer_b[-1] > 0:
        cursor_strip[0] = (trail_buffer_r[-1], 0, 0, 0)
        cursor_strip[1] = (0, trail_buffer_g[-1], 0, 0)
        cursor_strip[2] = (0, 0, trail_buffer_b[-1], 0)
        cursor_strip.show()

# --- Save/Load State ---
STATE_FILE = "/state.json"

def load_state():
    if STATE_FILE in os.listdir("/"):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Failed to load state:", e)
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print("Failed to save state:", e)

# --- I2C, Encoder, Display Setup ---
ENCODER_BUTTON_MASK = 1 << BUTTON_PIN
i2c = board.I2C()
ss = Seesaw(i2c, addr=ENCODER_I2C_ADDRESS)
encoder = rotaryio.IncrementalEncoder(ss)
ss.pin_mode(BUTTON_PIN, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, BUTTON_PIN)
encoder_pixel = SeesawNeoPixel(ss, ENCODER_NEOPIXEL_PIN, 1)
encoder_pixel.brightness = 0.4

state = load_state()
encoder_enabled = state.get("encoder_enabled", True)

# --- Display Setup ---
displayio.release_displays()
spi = board.SPI()
tft_cs = board.D5
tft_dc = board.D6
tft_rst = board.D9

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)
display = ST7789(display_bus, width=320, height=172, colstart=34, rotation=270)
screen_width = 320
screen_height = 172

class Menu:
    def __init__(self, display_group):
        self.group = display_group

    def update(self, encoder_enabled):
        pass

    def export_state(self):
        return {}

NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "lime": (0, 255, 0),
    "blue": (0, 0, 255), "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "silver": (192, 192, 192), "gray": (128, 128, 128), "maroon": (128, 0, 0), "olive": (128, 128, 0),
    "green": (0, 128, 0), "purple": (128, 0, 128), "teal": (0, 128, 128), "navy": (0, 0, 128),
    "orange": (255, 165, 0), "pink": (255, 192, 203), "brown": (165, 42, 42), "gold": (255, 215, 0),
    "orchid": (218, 112, 214), "salmon": (250, 128, 114), "khaki": (240, 230, 140), "indigo": (75, 0, 130),
    "violet": (238, 130, 238), "turquoise": (64, 224, 208), "plum": (221, 160, 221), "crimson": (220, 20, 60),
    "skyblue": (135, 206, 235), "chartreuse": (127, 255, 0), "coral": (255, 127, 80), "beige": (245, 245, 220)
}

def closest_named_color(r, g, b):
    min_dist = float("inf")
    closest = "unknown"
    for name, (nr, ng, nb) in NAMED_COLORS.items():
        dist = (r - nr) ** 2 + (g - ng) ** 2 + (b - nb) ** 2
        if dist < min_dist:
            min_dist = dist
            closest = name
    return closest


class RawRGBMenu(Menu):
    def __init__(self, display_group, r=0, g=127, b=255):
        super().__init__(display_group)
        self.last_r_pos = encoder.position
        self.r_value = r
        self.g_value = g
        self.b_value = b
        self.last_heights = [0, 0, 0]

        self.bar_width = screen_width // 3
        self.bar_area_height = int(screen_height * 0.75)

        self.palettes = []
        self.bar_bitmaps = []
        self.bar_tilegrids = []

        colors = [0xFF0000, 0x00FF00, 0x0000FF]
        for i in range(3):
            palette = displayio.Palette(2)
            palette[0] = 0x000000
            palette[1] = colors[i]
            self.palettes.append(palette)

            bitmap = displayio.Bitmap(self.bar_width, self.bar_area_height, 2)
            self.bar_bitmaps.append(bitmap)

            tilegrid = displayio.TileGrid(
                bitmap,
                pixel_shader=palette,
                x=i * self.bar_width,
                y=screen_height - self.bar_area_height
            )
            self.bar_tilegrids.append(tilegrid)
            self.group.append(tilegrid)

        self.preview_palette = displayio.Palette(1)
        self.preview_palette[0] = 0x000000
        self.preview_bitmap = displayio.Bitmap(screen_width, 20, 1)
        self.preview_tile = displayio.TileGrid(self.preview_bitmap, pixel_shader=self.preview_palette, x=0, y=0)
        self.group.append(self.preview_tile)

        # Named color label
        self.name_label = label.Label(
            terminalio.FONT,
            text="nearest: ???",
            color=0xFFFFFF,
            scale=2,
            x=10,
            y=24
        )
        self.group.append(self.name_label)

        self.labels = []
        for i, val in enumerate([self.r_value, self.g_value, self.b_value]):
            lbl_bg = displayio.Bitmap(self.bar_width, 20, 1)
            bg_palette = displayio.Palette(1)
            bg_palette[0] = 0x000000
            bg_tile = displayio.TileGrid(
                lbl_bg,
                pixel_shader=bg_palette,
                x=i * self.bar_width,
                y=screen_height - 22
            )
            self.group.append(bg_tile)

            lbl = label.Label(
                terminalio.FONT,
                text="000",
                color=0xFFFFFF,
                scale=2,
                anchor_point=(0.5, 0.5),
                anchored_position=(
                    int((i + 0.5) * self.bar_width),
                    screen_height - 12
                ),
            )
            self.labels.append(lbl)
            self.group.append(lbl)

        self.update_bars()

    def update_bars(self):
        now = time.monotonic()
        global last_trail_shift_time
        if now - last_trail_shift_time >= 0.1:
            # Update value trail for R
            trail_buffer_r.insert(0, self.r_value)
            trail_buffer_r.pop()
            for i in range(8):
                value_trail_r[i] = (trail_buffer_r[i], 0, 0)
            value_trail_r.show()

            # Update G
            trail_buffer_g.insert(0, self.g_value)
            trail_buffer_g.pop()
            for i in range(8):
                value_trail_g[i] = (0, trail_buffer_g[i], 0)
            value_trail_g.show()

            # Update B
            trail_buffer_b.insert(0, self.b_value)
            trail_buffer_b.pop()
            for i in range(8):
                value_trail_b[i] = (0, 0, trail_buffer_b[i])
            value_trail_b.show()

            last_trail_shift_time = now


        # Update named color label
        name = closest_named_color(self.r_value, self.g_value, self.b_value)
        self.name_label.text = f"nearest: {name}"

        values = [self.r_value, self.g_value, self.b_value]
        for i in range(3):
            height = int((values[i] / 255) * self.bar_area_height)
            bitmap = self.bar_bitmaps[i]
            old_height = self.last_heights[i]

            if height > old_height:
                for y in range(self.bar_area_height - height, self.bar_area_height - old_height):
                    for x in range(self.bar_width):
                        bitmap[x, y] = 1
            elif height < old_height:
                for y in range(self.bar_area_height - old_height, self.bar_area_height - height):
                    for x in range(self.bar_width):
                        bitmap[x, y] = 0

            self.last_heights[i] = height
            self.labels[i].text = f"{values[i]:03}"

        rgb = (self.r_value << 16) | (self.g_value << 8) | self.b_value
        self.preview_palette[0] = rgb
        update_led_strip(self.r_value, self.g_value, self.b_value)

    def update(self, encoder_enabled):
        # Always update value trail
        self.update_bars()
        if not encoder_enabled:
            return

        raw_pos = max(0, min(MAX_ENCODER_VALUE, -encoder.position))
        delta = abs(raw_pos - self.last_r_pos)

        if delta > 10:
            raw_pos = self.last_r_pos

        pos = max(0, min(MAX_ENCODER_VALUE, raw_pos))
        if pos != self.last_r_pos:
            self.r_value = int((pos / MAX_ENCODER_VALUE) * 255)
            encoder_pixel.fill((self.r_value, 0, 0))
            self.update_bars()
            self.last_r_pos = pos

    def export_state(self):
        return {
            "menu": "RawRGBMenu",
            "r": self.r_value,
            "g": self.g_value,
            "b": self.b_value
        }

main_group = displayio.Group()
display.root_group = main_group

menu_name = state.get("menu", "RawRGBMenu")
r = state.get("r", 0)
g = state.get("g", 127)
b = state.get("b", 255)
current_menu = RawRGBMenu(main_group, r, g, b)

while True:
    current_menu.update(encoder_enabled)

    # Detect encoder button press using interrupt flag
    if ss.get_GPIO_interrupt_flag() & ENCODER_BUTTON_MASK:
        encoder_enabled = not encoder_enabled
        print("Encoder toggled " + ("ON" if encoder_enabled else "OFF"))
        combined_state = current_menu.export_state()
        combined_state["encoder_enabled"] = encoder_enabled
        save_state(combined_state)
        # Clear the interrupt flag by reading the button state
        _ = button.value
    
    

    time.sleep(0.05)
