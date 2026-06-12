import time
import board
import analogio
import digitalio
import usb_hid
import json
import os
from ulab import numpy as np
from adafruit_hid.mouse import Mouse

# Initialize hardware
mouse = Mouse(usb_hid.devices)
joy_x = analogio.AnalogIn(board.A0)
joy_y = analogio.AnalogIn(board.A1)

# Onboard LED to communicate calibration status
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# --- CONFIGURATION ---
CALIBRATION_FILE = "/Calibration/JoyStickCalibration.json"

INVERT_X = False
INVERT_Y = False 
MAX_SPEED = 30  
DEADZONE = 0 

def load_calibration():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            return json.load(f)
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
        return calibration_data
    
def smoother(val,travel):
    val = np.interp(val, [0, travel], [0, 127])[0]
    val = -(np.log((127.3119-val)/128.3597)/0.04554843)
    val = np.interp(val, [0, 127], [0, travel])[0]
    return val

def get_mapped_speed(raw_value, center, min_val, max_val, invert):
    """Maps the raw value using calibrated bounds and handles the deadzone."""
    diff = raw_value - center
    
    # Apply Deadzone
    if abs(diff) < DEADZONE:
        return 0
        
    speed = 0
    if diff > 0:
        # Moving towards max
        active_travel = diff - DEADZONE
        max_travel = max_val - (center + DEADZONE)
        if max_travel > 0:
            active_travel = smoother(active_travel,max_travel)
            speed = (active_travel / max_travel) * MAX_SPEED
    else:
        # Moving towards min (diff is negative here)
        active_travel = abs(diff) - DEADZONE
        max_travel = (center - DEADZONE) - min_val
        if max_travel > 0:
            active_travel = smoother(active_travel,max_travel)
            speed = -(active_travel / max_travel) * MAX_SPEED
            
    # Apply Inversion
    if invert:
        speed = -speed
        
    # Clamp safety
    return int(speed)

# --- STARTUP ---
cal_data = load_calibration()

# --- MAIN LOOP ---
while True:
    x_move = get_mapped_speed(
        joy_x.value, 
        cal_data['center_x'], cal_data['min_x'], cal_data['max_x'], 
        INVERT_X
    )
    y_move = get_mapped_speed(
        joy_y.value, 
        cal_data['center_y'], cal_data['min_y'], cal_data['max_y'], 
        INVERT_Y
    )
    
    if x_move != 0 or y_move != 0:
        mouse.move(x=x_move, y=y_move)
        print((x_move, y_move))
        
    time.sleep(0.01)