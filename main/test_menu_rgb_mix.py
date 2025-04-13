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
    "skyblue": (135, 206, 235), "chartreuse": (127, 255, 0), "coral": (255, 127, 80), "beige": (245, 245, 220),
    "darkgray": (169, 169, 169), "lightgray": (211, 211, 211), "lavender": (230, 230, 250), 
    "darkred": (139, 0, 0), "darkgreen": (0, 100, 0), "darkblue": (0, 0, 139),
    "darkcyan": (0, 139, 139), "darkmagenta": (139, 0, 139), "darkyellow": (128, 128, 0),
}
def is_light_color(r, g, b):
    # Relative luminance formula (from W3C)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 128

def closest_named_color(r, g, b, blend_threshold=0.25):
    distances = []
    for name, (nr, ng, nb) in NAMED_COLORS.items():
        dist = (r - nr) ** 2 + (g - ng) ** 2 + (b - nb) ** 2
        distances.append((dist, name))

    distances.sort()
    closest_dist, closest_name = distances[0]
    second_dist, second_name = distances[1]

    if closest_dist == 0:
        return closest_name

    # Blend if second is within threshold % of the first
    if second_dist / closest_dist < (1 + blend_threshold):
        return f"{closest_name} with {second_name}"
    else:
        return closest_name

def dim_curve(value: int, gamma: float = 0.5) -> int:
    """Apply a gamma dimming curve with low-end exaggeration and ceil behavior."""
    if value <= 0:
        return 0
    normalized = value / 255
    adjusted = pow(normalized, 1 / gamma)
    result = int(adjusted * 255)
    return max(1, result)




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
        self.button_pressed_at = time.monotonic_ns()

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
                dimmed_value = dim_curve(self.trail_buffer[i])
                color[self.color_index] = dimmed_value
                self.trail_strip[i] = tuple(color)

            self.trail_strip.show()

            cursor_color = [0, 0, 0]
            dimmed_cursor_value = dim_curve(self.trail_buffer[-1])
            cursor_color[self.color_index] = dimmed_cursor_value
            self.cursor_strip[self.cursor_pixel_id] = tuple(cursor_color)
            self.cursor_strip.show()

            self.last_trail_update = now

    def update_encoder(self, max_value=255, sensitivity=1):
        if self.button and not self.button.value and time.monotonic_ns() - self.button_pressed_at > 400_000_000:
            self.channel_enabled = not self.channel_enabled
            self.button_pressed_at = time.monotonic_ns()
            print(f"Button pressed on encoder {self.encoder_addr}: {'Enabled' if self.channel_enabled else 'Disabled'}")
            # time.sleep(0.02)

        raw_pos = -self.encoder.position
        computed_pos = max(0, min(max_value, raw_pos * sensitivity))
        delta = abs(computed_pos - self.last_position)

        if delta > MAX_ENCODER_DELTA:
            computed_pos = self.last_position

        # Always track encoder motion, even if disabled
        self.pending_value = computed_pos
        self.last_position = computed_pos
        self.encoder.position = -int(computed_pos / sensitivity)

        # Only light the encoder LED if enabled
        if self.channel_enabled and self.encoder_pixel:
            encoder_color = [0, 0, 0]
            encoder_color[self.color_index] = self.pending_value
            self.encoder_pixel.fill(tuple(encoder_color))

class RGBMixMenu:
    def __init__(self, display_group, config, i2c, state):
        self.menu_name = "RGB Mix"
        self.menu_display_time = 2
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

        self.channel_names = ["Red", "Green", "Blue"]

        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        self.bar_width = self.screen_width // 3
        self.bar_area_height = int(self.screen_height * 0.60)
        self.bar_bitmaps = []
        self.bar_tilegrids = []
        self.last_heights = [0] * 3
        self.last_label_texts = ["000"] * 3


        # Color preview background (top bar)
        self.preview_palette = displayio.Palette(1)
        self.preview_palette[0] = 0x000000
        self.preview_bitmap = displayio.Bitmap(self.screen_width, 24, 1)
        self.preview_tile = displayio.TileGrid(self.preview_bitmap, pixel_shader=self.preview_palette, x=0, y=0)
        self.display_group.append(self.preview_tile)

        
        # Menu Title
        self.menu_subtitle = label.Label(
            terminalio.FONT, text="Menu",
            color=0xFFFFFF, scale=2,  # Smaller scale for the subtitle
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, self.screen_height // 2 - 30)  # Positioned above the title
        )
        self.menu_title = label.Label(
            terminalio.FONT, text=self.menu_name,
            color=0xFFFFFF, scale=4,  # Increased scale for a much bigger title
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, self.screen_height // 2)
        )
        # draw a black box around the menu, 50% width and height of the screen
        box_width = int(self.screen_width * 0.5)
        box_height = int(self.screen_height * 0.5)
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        box_bitmap = displayio.Bitmap(box_width, box_height, 1)
        box_palette = displayio.Palette(1)
        box_palette[0] = 0x505050
        self.box_tile = displayio.TileGrid(box_bitmap, pixel_shader=box_palette, x=box_x, y=box_y)
        self.display_group.append(self.box_tile)
        self.display_group.append(self.menu_title)
        self.display_group.append(self.menu_subtitle)
        self.title_shown_at = time.monotonic()


        # Named color label (centered)
        self.color_name_label = label.Label(
            terminalio.FONT, text="???",
            color=0xFFFFFF, scale=2,
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, 12)
        )
        enabled_colors = [0xFF0000, 0x00FF00, 0x0000FF]       # Red, Green, Blue
        disabled_colors = [0x400000, 0x004000, 0x000040]      # Dark Red, Dark Green, Dark Blue

        self.bar_bitmaps = []
        self.bar_tilegrids = []
        self.value_labels = []
        self.label_bg_tiles = []
        self.bar_palettes_enabled = []
        self.bar_palettes_disabled = []

        for i in range(3):
            # Bar bitmap and tilegrid
            bitmap = displayio.Bitmap(self.bar_width, self.bar_area_height, 2)
            enabled_palette = displayio.Palette(2)
            enabled_palette[0] = 0x000000
            enabled_palette[1] = enabled_colors[i]

            disabled_palette = displayio.Palette(2)
            disabled_palette[0] = 0x000000
            disabled_palette[1] = disabled_colors[i]

            self.bar_palettes_enabled.append(enabled_palette)
            self.bar_palettes_disabled.append(disabled_palette)

            tilegrid = displayio.TileGrid(
                bitmap, pixel_shader=enabled_palette,  # Start enabled
                x=i * self.bar_width,
                y=self.screen_height - self.bar_area_height - 24
            )
            self.bar_bitmaps.append(bitmap)
            self.bar_tilegrids.append(tilegrid)
            self.display_group.append(tilegrid)

            # Background box for label
            label_bg = displayio.Bitmap(self.bar_width, 20, 1)
            label_bg_palette = displayio.Palette(1)
            label_bg_palette[0] = 0x000000
            label_bg_tile = displayio.TileGrid(
                label_bg, pixel_shader=label_bg_palette,
                x=i * self.bar_width,
                y=self.screen_height - 22
            )
            self.label_bg_tiles.append(label_bg_tile)
            self.display_group.append(label_bg_tile)

            # Label showing the value
            value_label = label.Label(
                terminalio.FONT, text="000", color=0xFFFFFF, scale=2,
                anchor_point=(0.5, 0.5),
                anchored_position=(int((i + 0.5) * self.bar_width), self.screen_height - 12)
            )
            self.value_labels.append(value_label)
            self.display_group.append(value_label)

            

        self.outline_tilegrids = []


    
        
        self.channel_labels = []

        for i in range(3):
            color_name_label = label.Label(
                terminalio.FONT, text=self.channel_names[i],
                color=0xFFFFFF, scale=1,
                anchor_point=(0.5, 0.5),
                anchored_position=(int((i + 0.5) * self.bar_width), self.screen_height - self.bar_area_height - 36)
            )
            self.channel_labels.append(color_name_label)
            self.display_group.append(color_name_label)



    def update_screen_menu(self):
        if self.menu_title and (time.monotonic() - self.title_shown_at > self.menu_display_time):
            self.display_group.remove(self.menu_title)
            self.display_group.remove(self.menu_subtitle)
            self.display_group.remove(self.box_tile)
            self.menu_title = None
            self.menu_subtitle = None
            self.box_tile = None
            self.display_group.append(self.color_name_label)

    def update_screen_color_name(self):
        rgb = [ channel.pending_value if channel.channel_enabled else 0 for channel in self.channels]
        name = closest_named_color(*rgb)
        self.color_name_label.text = name
        self.color_name_label.color = 0x000000 if is_light_color(*rgb) else 0xFFFFFF
        self.color_name_label.scale = 1 if len(name) > 30 else 2
        self.preview_palette[0] = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]



    def update_screen(self):
        if self.first_draw: self.first_draw = False
        self.update_screen_menu()
        self.update_screen_color_name()

        

        # for i, channel in enumerate(self.channels):
        #     if channel.pending_value != channel.value:
        #         channel.value = channel.pending_value
                # Update the color of the cursor pixel
                # cursor_color = [0, 0, 0]
                # cursor_color[channel.color_index] = channel.pending_value
                # self.cursor_strip[channel.cursor_pixel_id] = tuple(cursor_color)
                # self.cursor_strip.show()

        # for i, channel in enumerate(self.channels):
        #     val = channel.pending_value
        #     height = int((val / 255) * self.bar_area_height)
        #     bitmap = self.bar_bitmaps[i]
        #     old_height = self.last_heights[i]

        #     if height != old_height:
        #         if height > old_height:
        #             # Add pixels
        #             for x in range(self.bar_width):
        #                 for y in range(self.bar_area_height - height, self.bar_area_height - old_height):
        #                     bitmap[x, y] = 1
        #         else:
        #             # Remove pixels
        #             for x in range(self.bar_width):
        #                 for y in range(self.bar_area_height - old_height, self.bar_area_height - height):
        #                     bitmap[x, y] = 0
        #         self.last_heights[i] = height
        #     self.bar_tilegrids[i].pixel_shader = (self.bar_palettes_enabled[i] if channel.channel_enabled else self.bar_palettes_disabled[i] )

            # label_text = f"{val:03}"
            # if self.last_label_texts[i] != label_text:
            #     self.value_labels[i].text = label_text
            #     self.last_label_texts[i] = label_text



            


    def update_trails(self):
        for channel in self.channels:
            channel.update_trail(self.trail_delay)

    def update_encoders(self, enabled=True, sensitivity=1):
        if enabled:
            for channel in self.channels:
                channel.update_encoder(sensitivity=sensitivity)
        

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
tick_count = 0
while True:
    
    current_menu.update_trails()
    current_menu.update_encoders(enabled=True,sensitivity=current_menu.knob_sensitivity)
    current_menu.update_screen()
    # time.sleep(0.05)
    tick_count +=1 
