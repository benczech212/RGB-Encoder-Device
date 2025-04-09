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

MAX_ENCODER_DELTA = 50
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 172

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

# Load global settings
with open('/settings.json', 'r') as f:
    SETTINGS = json.load(f)

class SimulatedEncoder:
    def __init__(self, initial_position=0):
        self.position = initial_position

class Channel:
    def __init__(self, config, i2c, cursor_strip, color_index, channel_state):
        self.encoder_addr = int(config["encoder_addr"], 16)
        self.neopixel_pin = config["neopixel_pin"]
        self.cursor_pixel_id = config["cursor_pixel_id"]
        self.trail_pin = getattr(board, config["trail_pin"])
        self.trail_strip = neopixel.NeoPixel(
            self.trail_pin, 8, brightness=config.get("brightness", 0.4),
            auto_write=False, pixel_order=config.get("trail_pixel_order", "RGB")
        )
        self.trail_buffer = [0] * 8
        self.color_index = color_index
        self.cursor_strip = cursor_strip
        self.channel_enabled = channel_state.get("enabled", True)
        self.last_trail_update = time.monotonic_ns()
        self.value = channel_state.get("value", config.get("initial_value", 0))
        self.pending_value = self.value
        self.last_position = channel_state.get("encoder_position", 0)

        try:
            self.encoder_ss = Seesaw(i2c, addr=self.encoder_addr)
            self.encoder = rotaryio.IncrementalEncoder(self.encoder_ss)
            self.encoder.position = self.last_position
            self.encoder_ss.pin_mode(config["button_pin"], self.encoder_ss.INPUT_PULLUP)
            self.button = digitalio.DigitalIO(self.encoder_ss, config["button_pin"])
            self.encoder_pixel = SeesawNeoPixel(self.encoder_ss, self.neopixel_pin, 1)
            self.encoder_pixel.brightness = config.get("brightness", 0.4)
        except Exception as e:
            print(f"Simulating encoder at address {hex(self.encoder_addr)}: {e}")
            self.encoder = SimulatedEncoder(self.last_position)
            self.encoder_pixel = None
            self.button = None

    def update_trail(self, trail_delay):
        now = time.monotonic_ns()
        if (now - self.last_trail_update) >= int(trail_delay * 1_000_000):
            self.trail_buffer.insert(0, self.pending_value if self.channel_enabled else 0)
            self.trail_buffer.pop()
            for i in range(8):
                color = [0, 0, 0]
                color[self.color_index] = self.trail_buffer[i]
                self.trail_strip[i] = tuple(color)
            self.trail_strip.show()
            cursor_color = [0, 0, 0]
            cursor_color[self.color_index] = self.trail_buffer[-1]
            self.cursor_strip[self.cursor_pixel_id] = tuple(cursor_color)
            self.cursor_strip.show()
            self.last_trail_update = now

    def update_encoder(self, max_value=255, sensitivity=1):
        if self.button and not self.button.value:
            self.channel_enabled = not self.channel_enabled
            time.sleep(0.02)

        if self.channel_enabled:
            raw_pos = -self.encoder.position
            computed_pos = max(0, min(max_value, raw_pos * sensitivity))
            delta = abs(computed_pos - self.last_position)

            if delta > MAX_ENCODER_DELTA:
                computed_pos = self.last_position

            if computed_pos != self.last_position:
                self.pending_value = computed_pos
            if self.encoder_pixel:
                encoder_color = [0, 0, 0]
                encoder_color[self.color_index] = self.pending_value
                self.encoder_pixel.fill(tuple(encoder_color))
            self.last_position = computed_pos

            # Update the raw encoder position to match the computed position divided by sensitivity
            self.encoder.position = -int(computed_pos / sensitivity)

class RGBMixMenu:
    def __init__(self, display_group, config, i2c, state):
        self.menu_name = "RGB Mix"
        self.first_draw = True
        self.knob_sensitivity = state.get("knob_sensitivity", 3)
        self.display_group = display_group
        self.cursor_strip = neopixel.NeoPixel(
            getattr(board, SETTINGS["cursor_strip_pin"]),
            SETTINGS["cursor_strip_count"],
            brightness=SETTINGS.get("cursor_pixel_brightness", 1.0),
            auto_write=False,
            pixel_order=SETTINGS.get("cursor_pixel_order", "RGB")
        )
        self.trail_delay = state.get("trail_delay", 0.01)
        self.channels = [
            Channel(chan_config, i2c, self.cursor_strip, idx, state.get(f"channel_{idx}", {}))
            for idx, chan_config in enumerate(SETTINGS["channels"])
        ]

        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        self.bar_width = self.screen_width // 3
        self.bar_area_height = int(self.screen_height * 0.60)
        self.bar_bitmaps = []
        self.bar_tilegrids = []
        self.last_heights = [0, 0, 0]

        # Color preview background (top bar)
        self.preview_palette = displayio.Palette(1)
        self.preview_palette[0] = 0x000000
        self.preview_bitmap = displayio.Bitmap(self.screen_width, 24, 1)
        self.preview_tile = displayio.TileGrid(self.preview_bitmap, pixel_shader=self.preview_palette, x=0, y=0)
        self.display_group.append(self.preview_tile)

        # Named color label (centered)
        self.name_label = label.Label(
            terminalio.FONT, text="???",
            color=0xFFFFFF, scale=2,
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, 12)
        )
        
        self.menu_subtitle = label.Label(
            terminalio.FONT, text="Menu",
            color=0xFFFFFF, scale=2,  # Smaller scale for the subtitle
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, self.screen_height // 2 - 30)  # Positioned above the title
        )
        self.display_group.append(self.menu_subtitle)

        self.menu_title = label.Label(
            terminalio.FONT, text=self.menu_name,
            color=0xFFFFFF, scale=4,  # Increased scale for a much bigger title
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, self.screen_height // 2)
        )
        self.display_group.append(self.menu_title)
        self.title_shown_at = time.monotonic()
        time.sleep(2)
        self.display_group.append(self.name_label)
        # Bar bitmaps and palettes
        colors = [0xFF0000, 0x00FF00, 0x0000FF]
        self.bar_bitmaps = []
        self.bar_tilegrids = []
        self.bar_palettes = []

        for i in range(3):
            palette = displayio.Palette(2)
            palette[0] = 0x000000  # Background color (black)
            palette[1] = colors[i]  # Foreground color (R, G, B)
            self.bar_palettes.append(palette)
            print(f"Palette {i}: {palette[0]:#06x}, {palette[1]:#06x}")  # DEBUG: Check palette

            bitmap = displayio.Bitmap(self.bar_width, self.bar_area_height, 2)
            self.bar_bitmaps.append(bitmap)

            tilegrid = displayio.TileGrid(
                bitmap, pixel_shader=palette,
                x=i * self.bar_width,
                y=self.screen_height - self.bar_area_height - 24
            )
            self.bar_tilegrids.append(tilegrid)
            self.display_group.append(tilegrid)

        # Outline rectangles for disabled channels
        self.outline_rects = []
        for i in range(3):
            outline_bitmap = displayio.Bitmap(self.bar_width, self.bar_area_height, 1)
            outline_palette = displayio.Palette(1)
            outline_palette[0] = 0xFFFFFF
            for x in range(self.bar_width):
                outline_bitmap[x, 0] = 1
                outline_bitmap[x, self.bar_area_height - 1] = 1
            for y in range(self.bar_area_height):
                outline_bitmap[0, y] = 1
                outline_bitmap[self.bar_width - 1, y] = 1
            outline_tile = displayio.TileGrid(
                outline_bitmap,
                pixel_shader=outline_palette,
                x=i * self.bar_width,
                y=self.screen_height - self.bar_area_height - 24
            )
            self.outline_rects.append(outline_tile)
            self.display_group.append(outline_tile)

        # Value labels + backgrounds
        self.labels = []
        for i in range(3):
            lbl_bg = displayio.Bitmap(self.bar_width, 20, 1)
            bg_palette = displayio.Palette(1)
            bg_palette[0] = 0x000000
            bg_tile = displayio.TileGrid(
                lbl_bg, pixel_shader=bg_palette,
                x=i * self.bar_width,
                y=self.screen_height - 22
            )
            self.display_group.append(bg_tile)

            lbl = label.Label(
                terminalio.FONT, text="000", color=0xFFFFFF, scale=2,
                anchor_point=(0.5, 0.5),
                anchored_position=(int((i + 0.5) * self.bar_width), self.screen_height - 12)
            )
            self.labels.append(lbl)
            self.display_group.append(lbl)

    def update_screen(self):
        if self.menu_title and (time.monotonic() - self.title_shown_at > 2.0):
            self.display_group.remove(self.menu_title)
            self.menu_title = None

        values = [channel.pending_value for channel in self.channels]
        rgb = tuple(values)
        self.preview_palette[0] = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
        self.name_label.text = closest_named_color(*rgb)

        if self.first_draw:
            self.last_heights = [0, 0, 0]
            for i in range(3):
                self.labels[i].text = "..."
            self.first_draw = False

        for i, channel in enumerate(self.channels):
            val = channel.pending_value
            height = int((val / 255) * self.bar_area_height)
            bitmap = self.bar_bitmaps[i]
            old_height = self.last_heights[i]

            if height != old_height:
                if height > old_height:
                    for x in range(self.bar_width):
                        for y in range(self.bar_area_height - height, self.bar_area_height - old_height):
                            bitmap[x, y] = 1  # Set pixel to 1 (foreground color)
                            #print(f"Bitmap[{i}][{x},{y}] = 1") #DEBUG
                elif height < old_height:
                    for y in range(self.bar_area_height - old_height, self.bar_area_height - height):
                        for x in range(self.bar_width):
                            bitmap[x, y] = 0  # Set pixel to 0 (background color)
                            #print(f"Bitmap[{i}][{x},{y}] = 0") #DEBUG
                self.last_heights[i] = height
            #print(f"bar_bitmaps[{i}] = {bitmap}") #DEBUG

            # Channel enable/disable logic
            if channel.channel_enabled and self.bar_tilegrids[i].hidden:
                self.bar_tilegrids[i].hidden = False
                self.outline_rects[i].hidden = True
            elif not channel.channel_enabled and self.outline_rects[i].hidden == True:
                self.bar_tilegrids[i].hidden = True
                self.outline_rects[i].hidden = False

            # Only update label if value changed
            current_label = f"{val:03}"
            if self.labels[i].text != current_label:
                self.labels[i].text = current_label

    def update_trails(self):
        for channel in self.channels:
            channel.update_trail(self.trail_delay)

    def update_encoders(self, enabled=True, sensitivity=1):
        if enabled:
            for channel in self.channels:
                channel.update_encoder(sensitivity=sensitivity)
        self.update_screen()

    def export_state(self):
        state = {"trail_delay": self.trail_delay, "knob_sensitivity": self.knob_sensitivity}
        for idx, chan in enumerate(self.channels):
            state[f"channel_{idx}"] = {
                "value": chan.value,
                "encoder_position": chan.last_position,
                "enabled": chan.channel_enabled
            }
        return state




# --- Display and main setup ---
displayio.release_displays()
spi = board.SPI()
tft_cs = board.D5
tft_dc = board.D6
tft_rst = board.D9
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)
display = ST7789(display_bus, width=320, height=172, colstart=34, rotation=270)

main_group = displayio.Group()
display.root_group = main_group

i2c = board.I2C()
state = {}
current_menu = RGBMixMenu(main_group, SETTINGS, i2c, state)
current_menu.knob_sensitivity = 3
while True:
    current_menu.update_trails()
    current_menu.update_encoders(enabled=True,sensitivity=current_menu.knob_sensitivity)
    time.sleep(0.05)
