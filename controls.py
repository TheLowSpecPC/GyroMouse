import os
import time
import math
import json
import board
import usb_hid
import analogio
import digitalio
from ulab import numpy as np
from adafruit_hid.mouse import Mouse
from sensor import MPU6500, QMC5883L
from mahony import Mahony

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
    



class Gyro:
    def __init__(self, i2c_bus, mouse, CalFile = "/Calibration/GyroCalibration.json"):
        self.SAMPLE_RATE_HZ = 100
        self.UPDATE_INTERVAL_NS = int(1e9 / self.SAMPLE_RATE_HZ)  # Convert to nanoseconds
        self.CALIBRATION_FILE = CalFile

        # Increase frequency to 400kHz for faster sensor polling
        self.i2c = i2c_bus

        self.m = mouse

        self.mpu = MPU6500(self.i2c)
        self.mag = QMC5883L(self.i2c)

        # Initialize Mahony Filter
        self.ahrs = Mahony(sample_freq=self.SAMPLE_RATE_HZ, Kp=0.05, Ki=0.0)

        # State variable for non-blocking timer
        self.last_update_time = time.monotonic_ns()
        
        self.inrange = 180
        self.outrangey = 6000
        self.outrangex = self.outrangey+(1920/1080)
        self.xnot, self.ynot = 0, 0
        
        # Run calibration before starting AHRS
        self.gyro_off_x, self.gyro_off_y, self.gyro_off_z = 0,0,0
        self.calibrate_gyro(self.mpu)
        
        self.pitchoff, self.rolloff, self.yawoff = 0,0,0

    def calibrate_gyro(self, mpu):
        # Try to load existing calibration
        try:
            os.stat(self.CALIBRATION_FILE) # Check if file exists
            with open(self.CALIBRATION_FILE, "r") as f:
                offsets = json.load(f)
                print("Loaded saved gyro calibration!")
                return offsets["x"], offsets["y"], offsets["z"]
        except OSError:
            pass # File doesn't exist, proceed to calibrate

        # Run the calibration routine (from previous steps)
        print("No calibration found. Keep sensor perfectly still! Calibrating gyro...")
        x_off, y_off, z_off = 0.0, 0.0, 0.0
        samples = 200
        for _ in range(samples):
            gx, gy, gz = self.mpu.get_gyro()
            x_off += gx
            y_off += gy
            z_off += gz
            time.sleep(0.01)
            
        x_off /= samples
        y_off /= samples
        z_off /= samples
        
        # Try to save it for next time
        try:
            with open(self.CALIBRATION_FILE, "w") as f:
                json.dump({"x": x_off, "y": y_off, "z": z_off}, f)
            print("Calibration saved to flash!")
        except OSError:
            print("WARNING: Could not save to flash. Is boot.py set to readonly=False?")

        self.gyro_off_x, self.gyro_off_y, self.gyro_off_z = x_off, y_off, z_off

    def get_orientation(self):
        # 1. Read Raw Sensor Data
        ax, ay, az = self.mpu.get_acceleration()
        gx, gy, gz = self.mpu.get_gyro()
        raw_mx, raw_my, raw_mz = self.mag.get_mag()
        
        # Apply Calibration Offsets
        gx -= self.gyro_off_x
        gy -= self.gyro_off_y
        gz -= self.gyro_off_z
        
        # 2. Map Magnetometer Axes
        mx, my, mz = raw_my, raw_mx, -raw_mz
        
        # 3. Update the Mahony Filter
        # Note: Your MPU6500 class already scales gyro to degrees/sec, which Mahony requires.
        self.ahrs.update(gx, gy, gz, ax, ay, az, mx, my, mz)

        # 5. Retrieve and Convert Angles
        # invoke compute_angles() on demand and return radians.
        pitch_deg = math.degrees(self.ahrs.pitch)
        roll_deg = math.degrees(self.ahrs.roll)
        yaw_deg = math.degrees(self.ahrs.yaw)
        
        # Convert Pitch, Roll and Yaw to a continuous 0 to 180 degrees
        if abs(roll_deg) > 90:
            pitch_deg = -pitch_deg
        else:
            if pitch_deg >= 0:
                pitch_deg = pitch_deg - 180
            else:
                pitch_deg = pitch_deg + 180
        
        return pitch_deg, roll_deg, yaw_deg
    
    def center(self, delay):
        print("Finding Center")
        while True:
            #print((self.pitchoff, self.yawoff))
            self.pitchoff, self.rolloff, self.yawoff = self.get_orientation()
            if time.monotonic_ns() % delay*1000000 < 5_000_000:
                break
        print("Done")
        
    def absmove(self, pitch, yaw):
        xin = (yaw - self.yawoff + 180) % 360 - 180
        yin = (pitch - self.pitchoff + 180) % 360 - 180
        
        x = np.interp(xin, [-self.inrange, self.inrange], [-self.outrangex, self.outrangex])[0]
        y = np.interp(yin, [-self.inrange, self.inrange], [-self.outrangey, self.outrangey])[0]
            
        x_value = int(x - self.xnot)
        y_value = int(y - self.ynot)
        
        self.m.move(-x_value, y_value)
        
        self.xnot = x
        self.ynot = y
        
        #print((x, y))
        #print((xnot, ynot))
        return (xin, yin)