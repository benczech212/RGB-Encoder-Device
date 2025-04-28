import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import json
import os
import math
from matplotlib.widgets import Cursor
from matplotlib.patches import Wedge


NAMED_COLORS_FILENAME = "named_colors.json"
HUE_COUNT = 32
SATURATION_COUNT = 4
VALUE_COUNT = 3
HUE_VOXEL_RES_FACTOR = 2
SAT_VOXEL_RES_FACTOR = 1
VAL_VOXEL_RES_FACTOR = 1

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

def generate_hsv_colors(hue_count, saturation_count, value_count):
    h_step = 1.0 / (hue_count)
    s_step = 1.0 / (saturation_count - 1)
    v_step = 1.0 / (value_count - 1)

    hsv_values = [
        (h, s, v)
        for h in [i * h_step for i in range(hue_count)]
        for s in [i * s_step for i in range(saturation_count)]
        for v in [i * v_step for i in range(value_count)]
    ]
    return hsv_values

def generate_and_save_colors(hue_count=HUE_COUNT, saturation_count=SATURATION_COUNT, value_count=VALUE_COUNT):
    hsv_values = generate_hsv_colors(hue_count, saturation_count, value_count)
    named_colors = []
    for hsv in hsv_values:
        rgb_float = mcolors.hsv_to_rgb(hsv)
        rgb_int = tuple(int(x * 255) for x in rgb_float)
        name = closest_named_color(rgb_int)
        if name == "black":
            continue
        
        named_colors.append({
            "name": name,
            "rgb": rgb_int,
            "hsv": hsv
        })
    with open(NAMED_COLORS_FILENAME, "w") as f:
        json.dump(named_colors, f, indent=4)
    return named_colors

# Set interactive backend
matplotlib.use('TkAgg')

# Generate named colors
named_colors = generate_and_save_colors(
    hue_count=HUE_COUNT,
    saturation_count=SATURATION_COUNT,
    value_count=VALUE_COUNT
)

# Create HSV voxel map

hue_res = 1.0 / (HUE_COUNT * HUE_VOXEL_RES_FACTOR)
sat_res = 1.0 / (SATURATION_COUNT * HUE_VOXEL_RES_FACTOR)
val_res = 1.0 / (VALUE_COUNT * HUE_VOXEL_RES_FACTOR)

hsv_voxel_map = [
    {
        "hsv": (h, s, v),
        "claimed_by": None
    }
    for h in [i * hue_res for i in range(int(1.0 / hue_res))]
    for s in [i * sat_res for i in range(int(1.0 / sat_res)+1)]
    for v in [i * val_res for i in range(int(1.0 / val_res)+1)]
]

# 

# Create single polar plot
fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'polar': True})
ax.set_title("Named Colors and Voxel Map")
ax.set_rmax(1.0)
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
ax.grid(True)

# Shade the HSV voxel map using ax.bar (works correctly in polar plots)
for voxel in hsv_voxel_map:
    h, s, v = voxel["hsv"]
    if s == 0:
        continue

    rgb = mcolors.hsv_to_rgb((h, s, v))

    theta = (h - hue_res / 2) * 2 * math.pi
    width = hue_res * 2 * math.pi
    radius = s
    height = sat_res

    # 🔒 Clamp the bar height so it doesn't exceed r=1.0
    max_radius = 1.0
    if radius + height > max_radius:
        height = max_radius - radius
        if height <= 0:
            continue

    ax.bar(
        x=theta,
        height=height,
        width=width,
        bottom=radius,
        color=rgb,
        edgecolor=None,
        linewidth=0,
        align='edge',
        alpha=0.5
    )


# Plot named colors
named_color_points = []
for color in named_colors:
    rgb_float = tuple([v / 255 for v in color["rgb"]])
    hue_rad = color["hsv"][0] * 2 * math.pi
    sat = color["hsv"][1]
    point, = ax.plot(hue_rad, sat, 'o', color=rgb_float, markersize=8, picker=True)
    named_color_points.append((point, color["name"]))

# Adjust grid sizing
hue_ticks = HUE_COUNT * HUE_VOXEL_RES_FACTOR
tick_angles = [i * (2 * math.pi / hue_ticks) for i in range(hue_ticks)]
tick_labels = [f"{int(i * 360 / hue_ticks)}°" for i in range(hue_ticks)]

ax.set_xticks(tick_angles)
ax.set_xticklabels(tick_labels)

# Adjust radial ticks to match saturation voxel resolution
sat_ticks = int(SATURATION_COUNT * SAT_VOXEL_RES_FACTOR)
radial_tick_values = [i / (sat_ticks-1) for i in range(sat_ticks)]
radial_tick_labels = [f"{round(val, 2)}" for val in radial_tick_values]

ax.set_yticks(radial_tick_values)
ax.set_yticklabels(radial_tick_labels)


def on_pick(event):
    for point, name in named_color_points:
        if event.artist == point:
            ax.annotate(name, xy=(event.mouseevent.xdata, event.mouseevent.ydata),
                        xytext=(10, 10), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
            fig.canvas.draw_idle()

fig.canvas.mpl_connect('pick_event', on_pick)

plt.tight_layout()
plt.show()
# save to png
output_dir = "output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
output_file = os.path.join(output_dir, "hsv_voxel_map.png")
plt.savefig(output_file, dpi=300)
plt.close(fig)
print(f"HSV voxel map saved to {output_file}")