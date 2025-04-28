# open named_colors.json
import json

with open("/home/benczech/dev/RGB-Encoder-Device/pre_processing/named_colors.json", "r") as f:
    named_colors = json.load(f)

# if color name is "black", drop
named_colors = [color for color in named_colors if color["name"] != "black"]
#  save to file
with open("named_colors_noblack.json", "w") as f:
    json.dump(named_colors, f, indent=4)