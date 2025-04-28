# === Color Constants & Helpers ===
import json
# NAMED_COLORS = {
#     "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
#     "lime": (0, 255, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
#     "cyan": (0, 255, 255), "magenta": (255, 0, 255), "silver": (192, 192, 192),
#     "gray": (128, 128, 128), "maroon": (128, 0, 0), "olive": (128, 128, 0),
#     "green": (0, 128, 0), "purple": (128, 0, 128), "teal": (0, 128, 128),
#     "navy": (0, 0, 128), "orange": (255, 165, 0), "pink": (255, 192, 203),
#     "brown": (165, 42, 42), "gold": (255, 215, 0), "orchid": (218, 112, 214),
#     "salmon": (250, 128, 114), "khaki": (240, 230, 140), "indigo": (75, 0, 130),
#     "violet": (238, 130, 238), "turquoise": (64, 224, 208), "plum": (221, 160, 221),
#     "crimson": (220, 20, 60), "skyblue": (135, 206, 235), "chartreuse": (127, 255, 0),
#     "coral": (255, 127, 80), "beige": (245, 245, 220), "darkgray": (169, 169, 169),
#     "lightgray": (211, 211, 211), "lavender": (230, 230, 250), "darkred": (139, 0, 0),
#     "darkgreen": (0, 100, 0), "darkblue": (0, 0, 139), "darkcyan": (0, 139, 139),
#     "darkmagenta": (139, 0, 139), "darkyellow": (128, 128, 0)
# }
with open('named_colors.json') as f:
    named_colors_raw = json.load(f)


def is_light_color(r: int, g: int, b: int) -> bool:
    """Return True if the color is considered light based on luminance."""
    return (0.299 * r + 0.587 * g + 0.114 * b) > 128

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to a hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"

def closest_named_color(r: int, g: int, b: int, blend_threshold: float = 0.25, show_two_colors=False, show_hex = True) -> str:
    """Return the closest named color from named_colors_raw."""
    distances = sorted(
        (
            (r - color["rgb"][0])**2 +
            (g - color["rgb"][1])**2 +
            (b - color["rgb"][2])**2,
            color["name"]
        )
        for color in named_colors_raw
    )
    closest_dist, closest_name = distances[0]
    second_dist, second_name = distances[1]
    if r == 0 and g == 0 and b == 0:
        name = "black"
    # if v = 0
    elif not show_two_colors:
        name = closest_name
    elif closest_dist == 0:
        name = closest_name
    elif second_dist / closest_dist < (1 + blend_threshold):
        name = f"{closest_name} with {second_name}"
    if show_hex:
        hex_color = rgb_to_hex(r, g, b)
        name = f"{name} ({hex_color})"
    return name

def dim_curve(value: int, gamma: float = 0.5) -> int:
    """Apply a gamma dimming curve. Ceils output to 1 for non-zero values."""
    if value <= 0:
        return 0
    normalized = value / 255
    adjusted = pow(normalized, 1 / gamma)
    return max(1, int(adjusted * 255))

def hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    """Convert HSV (0–1 float inputs) to RGB (0–1 float outputs)."""
    if s == 0.0:
        return v, v, v

    i = int(h * 6.0)  # Assume h in [0,1)
    f = (h * 6.0) - i
    i = i % 6

    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))

    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q