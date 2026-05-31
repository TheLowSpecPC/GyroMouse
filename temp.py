# SPDX-FileCopyrightText: 2022 Neradoc
# SPDX-License-Identifier: Unlicense

import time
import usb_hid
from absolute_mouse import AbsMouse # Using your new class name

# --- NEW LOGIC: Grab the mouse by its order ---
# Find all devices that identify as a Mouse
all_mice = [dev for dev in usb_hid.devices if dev.usage_page == 0x1 and dev.usage == 0x02]

if len(all_mice) == 0:
    raise RuntimeError("No mice found at all! Check your USB cable and boot.py.")
elif len(all_mice) == 1:
    print("Warning: Only 1 mouse found. Using it as the Absolute Mouse.")
    abs_device = all_mice[0]
else:
    # Because absolute_mouse was placed AFTER the standard mouse in boot.py,
    # it will be the last mouse in this list.
    abs_device = all_mice[-1]
    std_device = all_mice[0] # You can pass this to a StandardMouse class if you want!

# Initialize using ONLY the absolute mouse device
# We wrap it in a list [abs_device] so the library's find_device function can read it
m = AbsMouse([abs_device])
# ----------------------------------------------

# mouse_abs accept value from 0 to 32767 for both X and Y
# Note: Values are NOT pixels! 32767 = 100% (to right or to bottom)

def transpose(x, y):
    return ((x * 32767) // 1920, (y * 32767) // 1080)

positions = [(10, 40), (800, 800), (1600, 200)]

while True:
    time.sleep(2)
    for position in positions:
        print("MOVE", position, transpose(*position))
        m.move(*transpose(*position), 0)
        time.sleep(2)
    break