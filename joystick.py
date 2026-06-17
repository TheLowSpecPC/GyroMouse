import time
import board
import analogio
import digitalio
import usb_hid
import json
import os
from ulab import numpy as np
from adafruit_hid.mouse import Mouse

class JoyStick:
    def __init__(self, sensitivity = 30, deadzone = 0, CalFile = "/Calibration/JoyStickCalibration.json"):
        # --- CONFIGURATION ---
        self.CALIBRATION_FILE = CalFile
 
        self.MAX_SPEED = sensitivity  
        self.DEADZONE = deadzone
        
        self.cal_data = {}
        self.load_calibration()

    def load_calibration(self):
        # Onboard LED to communicate calibration status
        led = digitalio.DigitalInOut(board.LED)
        led.direction = digitalio.Direction.OUTPUT
        
        try:
            with open(self.CALIBRATION_FILE, "r") as f:
                self.cal_data = json.load(f)
        except:
            # If the file is corrupted, recalibrate
            """Runs the calibration routine and saves to a JSON file."""
            calibration_data = {}
            
            # 1. Calibrate Center
            led.value = True # Solid LED: Do not touch the stick
            time.sleep(2) # Give user a moment to let go
            
            x_center_sum = 0
            y_center_sum = 0
            samples = 100
            
            for _ in range(samples):
                x_center_sum += joy_x.value
                y_center_sum += joy_y.value
                time.sleep(0.01)
                
            calibration_data['center_x'] = int(x_center_sum / samples)
            calibration_data['center_y'] = int(y_center_sum / samples)
            
            # 2. Calibrate Extremes (Min/Max)
            x_min, y_min = 65535, 65535
            x_max, y_max = 0, 0
            
            # Fast flashing LED: Swirl the joystick in extreme circles
            end_time = time.monotonic() + 7 # 7 seconds to swirl
            led_state = False
            
            while time.monotonic() < end_time:
                x_val = joy_x.value
                y_val = joy_y.value
                
                x_min, x_max = min(x_min, x_val), max(x_max, x_val)
                y_min, y_max = min(y_min, y_val), max(y_max, y_val)
                
                # Flash LED
                led_state = not led_state
                led.value = led_state
                time.sleep(0.05)
                
            calibration_data['min_x'], calibration_data['max_x'] = x_min, x_max
            calibration_data['min_y'], calibration_data['max_y'] = y_min, y_max
            
            # 3. Save to File
            try:
                with open(CALIBRATION_FILE, "w") as f:
                    json.dump(calibration_data, f)
            except Exception as e:
                print("Failed to save calibration:", e)
                
            led.value = False # LED Off: Calibration complete
            self.cal_data = calibration_data
    
    def smoother(self, val, travel):
        val = np.interp(val, [0, travel], [0, 127])[0]
        val = -(np.log((127.3119-val)/128.3597)/0.04554843)
        val = np.interp(val, [0, 127], [0, travel])[0]
        return val

    def get_mapped_speed(self, raw_value, center, min_val, max_val, invert):
        """Maps the raw value using calibrated bounds and handles the deadzone."""
        diff = raw_value - center
        
        # Apply Deadzone
        if abs(diff) < self.DEADZONE:
            return 0
            
        speed = 0
        if diff > 0:
            # Moving towards max
            active_travel = diff - self.DEADZONE
            max_travel = max_val - (center + self.DEADZONE)
            if max_travel > 0:
                active_travel = self.smoother(active_travel,max_travel)
                speed = (active_travel / max_travel) * self.MAX_SPEED
        else:
            # Moving towards min (diff is negative here)
            active_travel = abs(diff) - self.DEADZONE
            max_travel = (center - self.DEADZONE) - min_val
            if max_travel > 0:
                active_travel = self.smoother(active_travel,max_travel)
                speed = -(active_travel / max_travel) * self.MAX_SPEED
                
        # Apply Inversion
        if invert:
            speed = -speed
            
        # Clamp safety
        return int(speed)


# Initialize hardware
m = Mouse(usb_hid.devices)
joy_x = analogio.AnalogIn(board.A0)
joy_y = analogio.AnalogIn(board.A1)

INVERT_X = False
INVERT_Y = False

j = JoyStick()

# --- MAIN LOOP ---
while True:
    x_move = j.get_mapped_speed(
        joy_x.value, 
        j.cal_data['center_x'], j.cal_data['min_x'], j.cal_data['max_x'], 
        INVERT_X
    )
    y_move = j.get_mapped_speed(
        joy_y.value, 
        j.cal_data['center_y'], j.cal_data['min_y'], j.cal_data['max_y'], 
        INVERT_Y
    )
    
    if x_move != 0 or y_move != 0:
        m.move(x=x_move, y=y_move)
        print((x_move, y_move))
        
    time.sleep(0.01)
