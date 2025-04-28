print("Hello World!")
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
from color_utils import *



MAX_ENCODER_DELTA = 50
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 172


NEOPIXEL_REGISTRY = {}


# Load global settings
with open('/settings.json', 'r') as f:
    SETTINGS = json.load(f)

class SimulatedEncoder:
    def __init__(self, initial_position=0):
        self.position = initial_position

class Channel:
    def __init__(self, config: dict, i2c, cursor_strip, color_index: int, saved_state: dict):
        """Initialize a single color channel linked to an encoder and NeoPixel bar."""
        self.color_index = color_index
        self.encoder_address = int(config["encoder_addr"], 16)
        self.button_pin = config["button_pin"]
        self.neopixel_pin = config["neopixel_pin"]
        self.cursor_pixel_id = config["cursor_pixel_id"]
        self.trail_pin = getattr(board, config["trail_pin"])
        self.cursor_strip = cursor_strip

        self.brightness = config.get("brightness", 0.4)
        self.channel_enabled = saved_state.get("enabled", True)
        self.value = saved_state.get("value", config.get("initial_value", 0))
        self.pending_value = self.value
        self.last_position = saved_state.get("encoder_position", 0)
        self.last_trail_update = time.monotonic_ns()
        self.button_pressed_at = time.monotonic_ns()

        # Trail LED setup
        if self.trail_pin not in NEOPIXEL_REGISTRY:
            trail_strip = neopixel.NeoPixel(
                self.trail_pin, 8,
                brightness=self.brightness,
                auto_write=False,
                pixel_order=config.get("trail_pixel_order", "RGB")
            )
            NEOPIXEL_REGISTRY[self.trail_pin] = trail_strip

        self.trail_strip = NEOPIXEL_REGISTRY[self.trail_pin]
        self.trail_buffer = [0] * len(self.trail_strip)

        # Try to initialize I2C encoder, else fall back to simulation
        try:
            self.encoder_ss = Seesaw(i2c, addr=self.encoder_address)
            self.encoder = rotaryio.IncrementalEncoder(self.encoder_ss)
            self.encoder.position = self.last_position

            self.encoder_ss.pin_mode(self.button_pin, self.encoder_ss.INPUT_PULLUP)
            self.button = digitalio.DigitalIO(self.encoder_ss, self.button_pin)

            self.encoder_pixel = SeesawNeoPixel(self.encoder_ss, self.neopixel_pin, 1)
            self.encoder_pixel.brightness = self.brightness
        except Exception as e:
            print(f"[Simulated] Encoder at {hex(self.encoder_address)} - {e}")
            self.encoder = SimulatedEncoder(self.last_position)
            self.button = None
            self.encoder_pixel = None

    def update_encoder(self, max_value: int = 255, sensitivity: int = 1):
        """Update the encoder value and button toggle."""
        now = time.monotonic_ns()

        # Handle button press for toggling enable
        if self.button and not self.button.value and (now - self.button_pressed_at) > 400_000_000:
            self.channel_enabled = not self.channel_enabled
            self.button_pressed_at = now
            print(f"Encoder {hex(self.encoder_address)} toggled to {'enabled' if self.channel_enabled else 'disabled'}")

        # Read and sanitize encoder position
        raw_pos = -self.encoder.position
        computed_pos = max(0, min(max_value, raw_pos * sensitivity))
        delta = abs(computed_pos - self.last_position)

        if delta > MAX_ENCODER_DELTA:
            computed_pos = self.last_position  # Ignore large jumps

        self.pending_value = computed_pos
        self.last_position = computed_pos
        self.encoder.position = -int(computed_pos / sensitivity)

        # Update encoder NeoPixel
        # if self.channel_enabled and self.encoder_pixel:
        #     color = [0, 0, 0]
        #     color[self.color_index] = self.pending_value
        #     self.encoder_pixel.fill(tuple(color))

    def update_trail(self, trail_delay: float):
        """Update the value trail for this channel."""
        now = time.monotonic_ns()
        if (now - self.last_trail_update) < int(trail_delay * 1_000_000):
            return  # Not enough time passed

        # Step 1: Update the trail buffer with current value or 0 if disabled
        val = self.pending_value if self.channel_enabled else 0
        self.trail_buffer.insert(0, val)
        self.trail_buffer.pop()

        # Step 2: Apply brightness floor logic to trail
        for i in range(len(self.trail_buffer)):
            value = self.trail_buffer[i]
            output = 0 if value == 0 else dim_curve(value)
            color = [0, 0, 0]
            color[self.color_index] = output
            self.trail_strip[i] = tuple(color)

        self.trail_strip.show()

        # Step 3: Update the cursor pixel (last trail value)
        last_val = self.trail_buffer[-1]
        cursor_color = [0, 0, 0]
        cursor_color[self.color_index] = 0 if last_val == 0 else dim_curve(last_val)
        self.cursor_strip[self.cursor_pixel_id] = tuple(cursor_color)
        self.cursor_strip.show()

        self.last_trail_update = now

class MenuEncoder:
    def __init__(self, config: dict, i2c, menu_count: int):
        self.encoder_address = int(config["encoder_addr"], 16)
        self.button_pin = config["button_pin"]
        self.neopixel_pin = config["neopixel_pin"]
        self.menu_count = menu_count

        self.accumulated_delta = 0
        self.step_threshold = 2  # Change this to 3 or more for even lower sensitivity
        self.position = 0
        self.last_position = 0
        self.selected_index = 0
        self.button_pressed_at = time.monotonic_ns()

        try:
            self.encoder_ss = Seesaw(i2c, addr=self.encoder_address)
            self.encoder = rotaryio.IncrementalEncoder(self.encoder_ss)
            self.encoder.position = 0
            self.encoder_ss.pin_mode(self.button_pin, self.encoder_ss.INPUT_PULLUP)
            self.button = digitalio.DigitalIO(self.encoder_ss, self.button_pin)
        except Exception as e:
            print(f"[Simulated Menu Encoder] {e}")
            self.encoder = SimulatedEncoder()
            self.button = None

    def update(self):
        raw_position = self.encoder.position
        delta = raw_position - self.last_position
        self.last_position = raw_position

        self.accumulated_delta += delta

        if abs(self.accumulated_delta) >= self.step_threshold:
            direction = int(self.accumulated_delta / abs(self.accumulated_delta))
            self.selected_index = (self.selected_index + direction) % self.menu_count
            self.accumulated_delta = 0
            self.encoder.position = 0  # Reset hardware encoder to avoid drift
            print(f"Menu switched to index {self.selected_index}")

        # Optional button press
        if self.button and not self.button.value and (time.monotonic_ns() - self.button_pressed_at) > 400_000_000:
            print("Menu encoder button pressed!")
            self.button_pressed_at = time.monotonic_ns()



class RGBMixMenu:
    def __init__(self, display_group, config, i2c, state):
        self.menu_name = "RGB Mix"
        self.menu_title_visible = True
        self.menu_display_time = 2
        self.first_draw = True
        self.knob_sensitivity = state.get("knob_sensitivity", 3)
        self.display_group = display_group
        cursor_pin = getattr(board, SETTINGS["cursor_strip_pin"])
        if cursor_pin not in NEOPIXEL_REGISTRY:
            strip = neopixel.NeoPixel(
                cursor_pin,
                SETTINGS["cursor_strip_count"],
                brightness=SETTINGS.get("cursor_pixel_brightness", 1.0),
                auto_write=False,
                pixel_order=SETTINGS.get("cursor_pixel_order", "RGB")
            )
            NEOPIXEL_REGISTRY[cursor_pin] = strip

        self.cursor_strip = NEOPIXEL_REGISTRY[cursor_pin]
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
                anchored_position=(int((i + 0.5) * self.bar_width), self.screen_height - self.bar_area_height - 34)
            )
            self.channel_labels.append(color_name_label)
            self.display_group.append(color_name_label)


   


    def update_screen_menu(self):
        if self.menu_title_visible and self.menu_title and (time.monotonic() - self.title_shown_at > self.menu_display_time):
            self.display_group.remove(self.menu_title)
            self.display_group.remove(self.menu_subtitle)
            self.display_group.remove(self.box_tile)
            self.menu_title = None
            self.menu_subtitle = None
            self.box_tile = None
            self.display_group.append(self.color_name_label)
            self.menu_title_visible = False

    def update_screen_color_name(self):
        rgb = [ channel.pending_value if channel.channel_enabled else 0 for channel in self.channels]
        name = closest_named_color(*rgb)
        self.color_name_label.text = name
        self.color_name_label.color = 0x000000 if is_light_color(*rgb) else 0xFFFFFF
        self.color_name_label.scale = 1 if len(name) > 26 else 2
        self.preview_palette[0] = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]



    def update_screen(self):
        if self.first_draw: self.first_draw = False
        self.update_screen_menu()
        self.update_screen_color_name()

        

        for i, channel in enumerate(self.channels):
            if channel.pending_value != channel.value:
                channel.value = channel.pending_value
                # Update the color of the cursor pixel
                # cursor_color = [0, 0, 0]
                # cursor_color[channel.color_index] = channel.pending_value
                # self.cursor_strip[channel.cursor_pixel_id] = tuple(cursor_color)
                # self.cursor_strip.show()

        for i, channel in enumerate(self.channels):
            val = channel.pending_value
            height = int((val / 255) * self.bar_area_height)
            bitmap = self.bar_bitmaps[i]
            old_height = self.last_heights[i]

            if height != old_height:
                if height > old_height:
                    # Add pixels
                    for x in range(self.bar_width):
                        for y in range(self.bar_area_height - height, self.bar_area_height - old_height):
                            bitmap[x, y] = 1
                else:
                    # Remove pixels
                    for x in range(self.bar_width):
                        for y in range(self.bar_area_height - old_height, self.bar_area_height - height):
                            bitmap[x, y] = 0
                self.last_heights[i] = height
            self.bar_tilegrids[i].pixel_shader = (self.bar_palettes_enabled[i] if channel.channel_enabled else self.bar_palettes_disabled[i] )

            label_text = f"{val:03}"
            if self.last_label_texts[i] != label_text:
                self.value_labels[i].text = label_text
                self.last_label_texts[i] = label_text



            


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

class ColorMixMenu:
    def __init__(self, display_group, config, i2c, state):
        self.menu_name = "Color Mix"
        self.menu_title_visible = True
        self.menu_display_time = 2
        self.first_draw = True
        self.knob_sensitivity = state.get("knob_sensitivity", 3)
        self.trail_delay = state.get("trail_delay", 0.01)
        self.display_group = display_group

        cursor_pin = getattr(board, SETTINGS["cursor_strip_pin"])
        if cursor_pin not in NEOPIXEL_REGISTRY:
            strip = neopixel.NeoPixel(
                cursor_pin,
                SETTINGS["cursor_strip_count"],
                brightness=SETTINGS.get("cursor_pixel_brightness", 1.0),
                auto_write=False,
                pixel_order=SETTINGS.get("cursor_pixel_order", "RGB")
            )
            NEOPIXEL_REGISTRY[cursor_pin] = strip

        self.cursor_strip = NEOPIXEL_REGISTRY[cursor_pin]

        self.channels = [
            Channel(chan_config, i2c, self.cursor_strip, idx, state.get(f"colormix_channel_{idx}", {}))
            for idx, chan_config in enumerate(SETTINGS["channels"])
        ]

        self.channel_names = ["Hue1", "Hue2", "Hue3"]

        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT

        # Named color label and preview
        self.preview_palette = displayio.Palette(1)
        self.preview_bitmap = displayio.Bitmap(self.screen_width, 24, 1)
        self.preview_tile = displayio.TileGrid(self.preview_bitmap, pixel_shader=self.preview_palette, x=0, y=0)
        self.display_group.append(self.preview_tile)

        self.color_name_label = label.Label(
            terminalio.FONT, text="???",
            color=0xFFFFFF, scale=2,
            anchor_point=(0.5, 0.5),
            anchored_position=(self.screen_width // 2, 12)
        )
        self.display_group.append(self.color_name_label)

    def update_screen_color_name(self):
        # Mix hues by averaging the 3 RGB values
        rgbs = []
        for chan in self.channels:
            h = (chan.pending_value / 255.0) * 360.0
            r, g, b = [int(c * 255) for c in hsv_to_rgb(h / 360.0, 1.0, 1.0)]
            rgbs.append((r, g, b))

        avg_rgb = tuple(sum(x[i] for x in rgbs) // len(rgbs) for i in range(3))
        name = closest_named_color(*avg_rgb)

        self.color_name_label.text = name
        self.color_name_label.color = 0x000000 if is_light_color(*avg_rgb) else 0xFFFFFF
        self.color_name_label.scale = 1 if len(name) > 26 else 2
        self.preview_palette[0] = (avg_rgb[0] << 16) | (avg_rgb[1] << 8) | avg_rgb[2]

    def update_trails(self):
        pass
        # for chan in self.channels:
        #     chan.update_trail(self.trail_delay)

    def update_encoders(self, enabled=True, sensitivity=1):
        if enabled:
            for chan in self.channels:
                chan.update_encoder(sensitivity=sensitivity)

    def update_screen(self):
        if self.first_draw:
            self.first_draw = False
        self.update_screen_color_name()

        # Push RGB colors directly to trail and cursor
        for chan in self.channels:
            h = (chan.pending_value / 255.0) * 360.0
            rgb_float = hsv_to_rgb(h / 360.0, 1.0, 1.0)
            r, g, b = [dim_curve(int(c * 255), gamma=0.8) for c in rgb_float]
            rgb_tuple = (r, g, b)

            # Update trail
            chan.trail_buffer.insert(0, rgb_tuple if chan.channel_enabled else (0, 0, 0))
            chan.trail_buffer.pop()
            for i in range(len(chan.trail_buffer)):
                chan.trail_strip[i] = chan.trail_buffer[i]
            chan.trail_strip.show()

            # Update cursor
            chan.cursor_strip[chan.cursor_pixel_id] = chan.trail_buffer[-1]
            chan.cursor_strip.show()

            #  Update encoder NeoPixel to full RGB color
            if chan.encoder_pixel and chan.channel_enabled:
                chan.encoder_pixel.fill(rgb_tuple)
            elif chan.encoder_pixel:
                chan.encoder_pixel.fill((0, 0, 0))  # Off if disabled

    def export_state(self):
        state = {"trail_delay": self.trail_delay, "knob_sensitivity": self.knob_sensitivity}
        for idx, chan in enumerate(self.channels):
            state[f"colormix_channel_{idx}"] = {
                "value": chan.value,
                "encoder_position": chan.last_position,
                "enabled": chan.channel_enabled
            }
        return state

class RGBScreen:
    def __init__(self, config):
        self.cs_pin = getattr(board, config["cs"])
        self.dc_pin = getattr(board, config["dc"])
        self.rst_pin = getattr(board, config["rst"])
        self.width = config["width"]
        self.height = config["height"]
        self.colstart = config["colstart"]
        self.rotation = config["rotation"]

        displayio.release_displays()
        spi = board.SPI()
        self.display_bus = FourWire(spi, command=self.dc_pin, chip_select=self.cs_pin, reset=self.rst_pin)
        self.display = ST7789(
            self.display_bus,
            width=self.width,
            height=self.height,
            colstart=self.colstart,
            rotation=self.rotation
        )

    def create_root_group(self):
        group = displayio.Group()
        self.display.root_group = group
        return group

i2c = board.I2C()


screen = RGBScreen(SETTINGS["screen"])
display = screen.display
main_group = screen.create_root_group()

# Initialize menu
state = {}
menus = [RGBMixMenu, ColorMixMenu]
menu_names = ["RGB Mix", "Color Mix"]
menu_index = 0
current_menu = menus[menu_index](main_group, SETTINGS, i2c, state)
menu_encoder = MenuEncoder(SETTINGS["menu_encoder"], i2c, len(menus))

# Main loop
tick_count = 0
while True:
    if hasattr(current_menu, "update_trails"):
        current_menu.update_trails()
    current_menu.update_encoders(enabled=True, sensitivity=current_menu.knob_sensitivity)
    current_menu.update_screen()
    menu_encoder.update()

    if menu_encoder.selected_index != menu_index:
        menu_index = menu_encoder.selected_index
        print(f"Switching to menu: {menu_names[menu_index]}")
        main_group = screen.create_root_group()
        current_menu = menus[menu_index](main_group, SETTINGS, i2c, state)

    tick_count += 1
