import usb_hid
from adafruit_hid.mouse import Mouse

m = Mouse(usb_hid.devices)

m.move(1000, 0)