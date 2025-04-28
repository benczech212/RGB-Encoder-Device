


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