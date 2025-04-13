import matplotlib.colors as mcolors
import json
def closest_named_color(rgb_tuple):
    min_dist = float("inf")
    closest_name = None
    for name, hex_val in mcolors.CSS4_COLORS.items():
        r, g, b = [int(255 * x) for x in mcolors.to_rgb(hex_val)]
        dist = sum((c1 - c2) ** 2 for c1, c2 in zip((r, g, b), rgb_tuple))
        if dist < min_dist:
            min_dist = dist
            closest_name = name
    return closest_name

# generate list of hsv values
h_count = 12
h_wrap = True

sat_values = 4
sat_wrap = False

val_values = 4
val_wrap = False

h_step = 1.0 / (h_count-1) if h_wrap else 1.0 / h_count
sat_step = 1.0 / (sat_values-1) if sat_wrap else 1.0 / sat_values
val_step = 1.0 / (val_values-1) if val_wrap else 1.0 / val_values

hue_values = [i * h_step for i in range(h_count)]
sat_values = [i * sat_step for i in range(sat_values)]
val_values = [i * val_step for i in range(val_values)]




# generate list of rgb values
hsv_values = [(h, s, v) for h in hue_values for s in sat_values for v in val_values]
rgb_values = [mcolors.hsv_to_rgb(hsv) for hsv in hsv_values]

# create list of objects with name, rgb, and hsv values
named_colors = []
for rgb_float, hsv in zip(rgb_values, hsv_values):
    rgb_int = tuple(int(x * 255) for x in rgb_float)
    name = closest_named_color(rgb_int)
    named_colors.append({
        "name": name,
        "rgb": rgb_int,
        "hsv": hsv
    })

# Save the named colors to a JSON file
with open("named_colors.json", "w") as f:
    json.dump(named_colors, f, indent=4)
