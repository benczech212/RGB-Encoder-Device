import pygame
import colorsys
import math

class Slider:
    def __init__(self, x, y, width, min_val, max_val, start_val, label):
        self.x = x
        self.y = y
        self.width = width
        self.min_val = min_val
        self.max_val = max_val
        self.val = start_val
        self.label = label
        self.handle_radius = 10
        self.dragging = False
        self.font = pygame.font.SysFont(None, 24)

    def draw(self, surface):
        # Draw main slider line
        pygame.draw.line(surface, (0, 0, 0), (self.x, self.y), (self.x + self.width, self.y), 4)

        # Draw ticks
        num_ticks = (self.max_val - self.min_val) + 1
        for i in range(num_ticks):
            tick_x = self.x + (i / (num_ticks - 1)) * self.width
            pygame.draw.line(surface, (0, 0, 0), (int(tick_x), self.y - 5), (int(tick_x), self.y + 5), 2)

        # Draw handle
        handle_x = self.x + (self.val - self.min_val) / (self.max_val - self.min_val) * self.width
        pygame.draw.circle(surface, (0, 0, 0), (int(handle_x), self.y), self.handle_radius)

        # Draw label and value
        label_surface = self.font.render(f"{self.label}: {self.get_value()}", True, (0, 0, 0))
        surface.blit(label_surface, (self.x, self.y - 40))

        # Draw min and max labels
        min_surface = self.font.render(str(self.min_val), True, (0, 0, 0))
        max_surface = self.font.render(str(self.max_val), True, (0, 0, 0))
        surface.blit(min_surface, (self.x - 10, self.y + 15))
        surface.blit(max_surface, (self.x + self.width - 10, self.y + 15))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if math.hypot(mx - self.get_handle_x(), my - self.y) <= self.handle_radius:
                self.dragging = True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx, _ = event.pos
            ratio = (mx - self.x) / self.width
            ratio = min(max(ratio, 0), 1)
            # Snap to nearest notch
            num_steps = (self.max_val - self.min_val)
            snapped_step = round(ratio * num_steps)
            self.val = self.min_val + snapped_step

    def get_handle_x(self):
        return self.x + (self.val - self.min_val) / (self.max_val - self.min_val) * self.width

    def get_value(self):
        return int(self.val)


# --- Settings ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

hue_count = 32
saturation_count = 4
value_count = 3
hue_voxel_res_factor = 2
hue_voxel_res = 1.0 / (hue_count * hue_voxel_res_factor)
sat_voxel_res = 1.0 / (saturation_count * hue_voxel_res_factor)
val_voxel_res = 1.0 / (value_count * hue_voxel_res_factor)

hsv_voxel_map = []

sat_steps = int(1.0 / sat_voxel_res) + 1

for si in range(sat_steps):
    sat = si * sat_voxel_res
    if sat > 1.0:
        sat = 1.0

    # Linearly reduce hue count toward center
    hue_count_at_s = max(1, round(hue_count * sat))
    hue_voxel_res_at_s = 1.0 / (hue_count_at_s * hue_voxel_res_factor)

    for hi in range(int(1.0 / hue_voxel_res_at_s)):
        hue = hi * hue_voxel_res_at_s

        for vi in range(int(1.0 / val_voxel_res) + 1):
            val = vi * val_voxel_res
            if val > 1.0:
                val = 1.0

            hsv_voxel_map.append({
                "hsv": (hue, sat, val),
                "rgb": colorsys.hsv_to_rgb(hue, sat, val),
                "claimed_by": None
            })

print(f"Adaptive HSV Voxel Map Length: {len(hsv_voxel_map)}")


print(f"HSV Voxel Map Length: {len(hsv_voxel_map)}")

def draw_hue_test(surface):
    center_x = 960
    center_y = 540
    radius_scale = 400  # Radius for full saturation
    wedge_overlap_angle = 0.5 * (hue_voxel_res * 2 * math.pi)  # slight overlap
    wedge_overlap_radius = 1.5  # slight radius fudge

    # Build a saturation map for how many hues at each ring
    sat_steps = int(1.0 / sat_voxel_res) + 1
    saturation_rings = []
    for si in range(sat_steps):
        sat = si * sat_voxel_res
        if sat > 1.0:
            sat = 1.0
        hue_count_at_s = max(1, round(hue_count * sat))
        saturation_rings.append((sat, hue_count_at_s))

    # --- Draw background wedges ---
    # Sort voxels to draw smaller radii first
    voxels_sorted = sorted(hsv_voxel_map, key=lambda v: v["hsv"][1])

    for voxel in voxels_sorted:
        h, s, v = voxel["hsv"]
        if s == 0:
            continue

        # Calculate hue count at this saturation
        hue_count_at_s = max(1, round(hue_count * s))
        hue_width = 1.0 / hue_count_at_s  # in hue space (0-1)

        # Calculate angles and radius
        theta_center = h * 2 * math.pi
        theta_start = (h - hue_width / 2) * 2 * math.pi - wedge_overlap_angle
        theta_end = (h + hue_width / 2) * 2 * math.pi + wedge_overlap_angle

        radius_inner = (s - sat_voxel_res / 2) * radius_scale - wedge_overlap_radius
        radius_outer = (s + sat_voxel_res / 2) * radius_scale + wedge_overlap_radius

        radius_inner = max(0, radius_inner)
        radius_outer = max(0, radius_outer)

        # Build wedge points
        points = []
        angle_step = math.radians(0.5)

        angle = theta_start
        while angle <= theta_end:
            x = int(center_x + radius_outer * math.cos(angle))
            y = int(center_y + radius_outer * math.sin(angle))
            points.append((x, y))
            angle += angle_step

        angle = theta_end
        while angle >= theta_start:
            x = int(center_x + radius_inner * math.cos(angle))
            y = int(center_y + radius_inner * math.sin(angle))
            points.append((x, y))
            angle -= angle_step

        # Convert color
        r, g, b = [int(c * 255) for c in voxel["rgb"]]

        # Draw filled polygon
        if len(points) >= 3:
            pygame.draw.polygon(surface, (r, g, b), points)
            pygame.draw.polygon(surface, (255, 255, 255), points, width=1)  # <-- stroke on top


    # --- Draw wireframe on top ---
    # # Draw saturation rings
    # for sat, _ in saturation_rings:
    #     radius = int(sat * radius_scale)
    #     if radius > 0:
    #         pygame.draw.circle(surface, (255, 255, 255), (center_x, center_y), radius, 1)

    # # Draw hue spokes
    # for sat, hue_count_at_s in saturation_rings:
    #     if hue_count_at_s == 0:
    #         continue
    #     radius = int(sat * radius_scale)
    #     if radius == 0:
    #         continue
    #     for hi in range(hue_count_at_s):
    #         hue = hi / hue_count_at_s
    #         theta = hue * 2 * math.pi
    #         x = int(center_x + radius * math.cos(theta))
    #         y = int(center_y + radius * math.sin(theta))
    #         pygame.draw.line(surface, (255, 255, 255), (center_x, center_y), (x, y), 1)



# --- Initialize ---
pygame.init()

# Create fullscreen window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("HSV Polar Plot")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 24)

# Create two sliders
hue_slider = Slider(100, 950, 800, 2, 64, hue_count, "Hue Count")
sat_slider = Slider(100, 1000, 800, 1, 16, saturation_count, "Saturation Count")

def regenerate_voxel_map():
    global hsv_voxel_map, hue_count, saturation_count
    hue_count = hue_slider.get_value()
    saturation_count = sat_slider.get_value()

    print(f"Regenerating: hue_count={hue_count}, sat_count={saturation_count}")

    hue_voxel_res = 1.0 / (hue_count * hue_voxel_res_factor)
    sat_voxel_res = 1.0 / (saturation_count * hue_voxel_res_factor)

    hsv_voxel_map = []
    sat_steps = int(1.0 / sat_voxel_res) + 1

    for si in range(sat_steps):
        sat = si * sat_voxel_res
        if sat > 1.0:
            sat = 1.0

        # Linearly reduce hue count toward center
        hue_count_at_s = max(1, round(hue_count * sat))
        hue_voxel_res_at_s = 1.0 / (hue_count_at_s * hue_voxel_res_factor)

        for hi in range(int(1.0 / hue_voxel_res_at_s)):
            hue = hi * hue_voxel_res_at_s

            for vi in range(int(1.0 / val_voxel_res) + 1):
                val = vi * val_voxel_res
                if val > 1.0:
                    val = 1.0

                hsv_voxel_map.append({
                    "hsv": (hue, sat, val),
                    "rgb": colorsys.hsv_to_rgb(hue, sat, val),
                    "claimed_by": None
                })

regenerate_voxel_map()

running = True
last_hue_val = hue_slider.get_value()
last_sat_val = sat_slider.get_value()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        hue_slider.handle_event(event)
        sat_slider.handle_event(event)

    if (hue_slider.get_value() != last_hue_val) or (sat_slider.get_value() != last_sat_val):
        last_hue_val = hue_slider.get_value()
        last_sat_val = sat_slider.get_value()
        regenerate_voxel_map()

    # --- Drawing ---
    screen.fill((255, 255, 255))  # Fill the screen with white

    draw_hue_test(screen)  # Pass the actual screen

    hue_slider.draw(screen)
    sat_slider.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
