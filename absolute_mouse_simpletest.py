# SPDX-FileCopyrightText: 2022 Neradoc
# SPDX-License-Identifier: Unlicense

import time
import usb_hid
from absolute_mouse import AbsMouse

# Find all devices that identify as a Mouse
all_mice = [dev for dev in usb_hid.devices if dev.usage_page == 0x1 and dev.usage == 0x02]

m = AbsMouse(all_mice[-1]) # There are only two mouse so the last one would be the AbsMouse

# mouse_abs accept value from 0 to 32767 for both X and Y
# Note: Values are NOT pixels! 32767 = 100% (to right or to bottom)


def transpose(x, y):
    return ((x * 32767) // 1920, (y * 32767) // 1080)


positions = [(1920, 1080), (960 ,540)]

while True:
    time.sleep(2)
    for position in positions:
        print("MOVE", position, transpose(*position))
        m.move(*transpose(*position), 0)
        time.sleep(2)
    # time.sleep(10)
    break
