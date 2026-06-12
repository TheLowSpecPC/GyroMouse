import board
import busio
import time
import usb_hid
from analogio import AnalogIn
from adafruit_hid.mouse import Mouse

m = Mouse(usb_hid.devices)

x = AnalogIn(board.GP27)
y = AnalogIn(board.GP26)

while True:
    # Read the raw 16-bit value
    x_value = int(((x.value / 65535) * 255) - 128)
    y_value = int(((y.value / 65535) * 255) - 128)
    
    #print(f"X: {x_value}, Y: {y_value}")
    #time.sleep(0.1)
    
    m.move(x_value, y_value)